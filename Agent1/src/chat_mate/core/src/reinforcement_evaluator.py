import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import json
import os
from trinity.core.config.config_manager import ConfigManager

class ReinforcementEvaluator:
    """
    Evaluates responses and provides reinforcement feedback.
    Manages memory data and generates insights for prompt tuning.
    """

    def __init__(self, config_manager: ConfigManager):
        """
        Initialize the reinforcement evaluator.
        
        :param config_manager: The configuration manager instance
        """
        self.logger = logging.getLogger(__name__)
        self.config_manager = config_manager
        self.memory_file = self.config_manager.get('MEMORY_FILE', 'memory_data.json')
        self.memory_data = self._load_memory_data()
        self.min_score_threshold = self.config_manager.get('MIN_SCORE_THRESHOLD', 0.6)

    def _load_memory_data(self) -> Dict[str, Any]:
        """Load memory data from file or create default structure."""
        try:
            if os.path.exists(self.memory_file):
                with open(self.memory_file, 'r') as f:
                    return json.load(f)
            else:
                return self._create_default_memory()
        except Exception as e:
            self.logger.error(f"Error loading memory data: {e}")
            return self._create_default_memory()

    def _create_default_memory(self) -> Dict[str, Any]:
        """Create and return default memory data structure."""
        default_memory = {
            'responses': [],
            'feedback': [],
            'scores': [],
            'last_updated': datetime.now().isoformat(),
            'prompt_performance': {},
            'rate_limit_adjustments': []
        }
        self._save_memory_data(default_memory)
        return default_memory

    def _save_memory_data(self, data: Dict[str, Any]) -> None:
        """Save memory data to file."""
        try:
            with open(self.memory_file, 'w') as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            self.logger.error(f"Error saving memory data: {e}")

    def evaluate_response(self, response_text: str, prompt_text: str) -> float:
        """
        Evaluate a response using multiple metrics.
        
        Args:
            response_text: The response to evaluate
            prompt_text: The prompt that generated the response
            
        Returns:
            Score between 0 and 1
        """
        try:
            # Initialize scores
            scores = {
                'length': self._evaluate_length(response_text),
                'relevance': self._evaluate_relevance(response_text, prompt_text),
                'coherence': self._evaluate_coherence(response_text),
                'completeness': self._evaluate_completeness(response_text, prompt_text)
            }
            
            # Calculate weighted average
            weights = {
                'length': 0.2,
                'relevance': 0.3,
                'coherence': 0.25,
                'completeness': 0.25
            }
            
            final_score = sum(scores[metric] * weights[metric] for metric in scores)
            return min(max(final_score, 0.0), 1.0)  # Ensure score is between 0 and 1
            
        except Exception as e:
            self.logger.error(f"Error evaluating response: {str(e)}")
            return 0.0

    def _evaluate_length(self, text: str) -> float:
        """Evaluate response length."""
        min_length = 50
        max_length = 1000
        length = len(text)
        
        if length < min_length:
            return 0.2
        elif length > max_length:
            return 0.8
        else:
            return 0.2 + 0.6 * (length - min_length) / (max_length - min_length)
            
    def _evaluate_relevance(self, response: str, prompt: str) -> float:
        """Evaluate response relevance to prompt."""
        # Simple keyword matching for now
        prompt_keywords = set(prompt.lower().split())
        response_keywords = set(response.lower().split())
        
        if not prompt_keywords:
            return 0.5
            
        matching_keywords = prompt_keywords.intersection(response_keywords)
        return len(matching_keywords) / len(prompt_keywords)
        
    def _evaluate_coherence(self, text: str) -> float:
        """Evaluate response coherence."""
        # Simple coherence check based on sentence structure
        sentences = text.split('.')
        if len(sentences) < 2:
            return 0.3
            
        # Check for basic sentence structure
        valid_sentences = sum(1 for s in sentences if len(s.split()) > 3)
        return valid_sentences / len(sentences)
        
    def _evaluate_completeness(self, response: str, prompt: str) -> float:
        """Evaluate response completeness."""
        # Check if response addresses key aspects of the prompt
        question_words = {'what', 'why', 'how', 'when', 'where', 'who'}
        prompt_words = set(prompt.lower().split())
        
        if not question_words.intersection(prompt_words):
            return 0.5
            
        # Check if response contains complete sentences
        sentences = response.split('.')
        complete_sentences = sum(1 for s in sentences if len(s.split()) > 5)
        return min(complete_sentences / 3, 1.0)  # Cap at 1.0

    def _generate_feedback(self, score: float, response: str) -> List[str]:
        """
        Generate feedback based on score and response.
        
        :param score: The calculated score
        :param response: The response to provide feedback for
        :return: List of feedback messages
        """
        feedback = []
        
        if score < self.min_score_threshold:
            feedback.append("Response quality below threshold")
            if len(response.split()) < 50:
                feedback.append("Response is too short")
            elif len(response.split()) > 1000:
                feedback.append("Response is too long")
        else:
            feedback.append("Response meets quality standards")
            
        return feedback

    def _update_prompt_performance(self, prompt_text: str, score: float) -> None:
        """
        Update performance metrics for a prompt.
        
        :param prompt_text: The prompt text
        :param score: The score for the response
        """
        if prompt_text not in self.memory_data['prompt_performance']:
            self.memory_data['prompt_performance'][prompt_text] = {
                'scores': [],
                'average_score': 0.0,
                'total_responses': 0
            }
            
        performance = self.memory_data['prompt_performance'][prompt_text]
        performance['scores'].append(score)
        performance['total_responses'] += 1
        performance['average_score'] = sum(performance['scores']) / performance['total_responses']

    def get_prompt_insights(self, prompt_text: str) -> Dict[str, Any]:
        """
        Get insights for a specific prompt.
        
        :param prompt_text: The prompt to get insights for
        :return: Dictionary containing prompt insights
        """
        if prompt_text not in self.memory_data['prompt_performance']:
            return {
                'error': 'No performance data available for this prompt',
                'prompt': prompt_text
            }
            
        performance = self.memory_data['prompt_performance'][prompt_text]
        return {
            'prompt': prompt_text,
            'total_responses': performance['total_responses'],
            'average_score': performance['average_score'],
            'score_trend': self._calculate_score_trend(performance['scores'])
        }

    def _calculate_score_trend(self, scores: List[float]) -> str:
        """
        Calculate the trend of scores.
        
        :param scores: List of scores
        :return: Trend description
        """
        if len(scores) < 2:
            return "Insufficient data"

        recent_scores = scores[-5:] if len(scores) > 5 else scores
        avg_recent = sum(recent_scores) / len(recent_scores)
        
        # If all scores are recent, compare first half to second half
        if len(scores) <= len(recent_scores):
            mid = len(scores) // 2
            first_half = scores[:mid]
            second_half = scores[mid:]
            avg_first = sum(first_half) / len(first_half)
            avg_second = sum(second_half) / len(second_half)
            
            if avg_second > avg_first:
                return "Improving"
            elif avg_second < avg_first:
                return "Declining"
            return "Stable"
        
        # Compare recent scores to older scores
        older_scores = scores[:-len(recent_scores)]
        avg_older = sum(older_scores) / len(older_scores)
        
        if avg_recent > avg_older:
            return "Improving"
        elif avg_recent < avg_older:
            return "Declining"
        return "Stable"

    def get_memory_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the memory data.
        
        :return: Dictionary containing memory summary
        """
        return {
            'total_responses': len(self.memory_data['responses']),
            'average_score': sum(self.memory_data['scores']) / len(self.memory_data['scores']) if self.memory_data['scores'] else 0,
            'last_updated': self.memory_data['last_updated'],
            'prompt_count': len(self.memory_data['prompt_performance'])
        }

    def clear_memory(self) -> None:
        """Clear all memory data and reset to defaults."""
        self.memory_data = self._create_default_memory()
        self._save_memory_data(self.memory_data)
        self.logger.info("Memory data cleared and reset to defaults") 
