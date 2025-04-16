import os
import sys
from collections import defaultdict
from datetime import datetime, timezone

# Add project root to sys.path (adjust if needed)
script_dir = os.path.dirname(__file__) # social/tools
project_root = os.path.abspath(os.path.join(script_dir, '..', '..')) # Adjust based on actual structure
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# --- Dependencies (Potentially needed later) ---
try:
    from dreamforge.core.governance_memory_engine import log_event
except ImportError:
    # Fallback logger if the main logger isn't available
    def log_event(event_type, source, details):
        print(f"[Dummy Logger - EngagementDashboard] Event: {event_type}, Source: {source}, Details: {details}")
        return False
# ------------------------------------------------

_SOURCE = "EngagementDashboard"

class EngagementDashboard:
    """
A simple class to aggregate and display social engagement metrics.
    Now includes a basic weighted unified engagement score calculation.
    """

    # --- Configuration for Unified Score ---
    # Define weights for different metrics. These are illustrative and should be tuned.
    # Higher weights mean the metric contributes more to the overall score.
    # Weights might differ per platform, but using common names for simplicity here.
    DEFAULT_METRIC_WEIGHTS = {
        # Twitter
        'likes': 1.0,
        'retweets': 2.5,
        'replies': 2.0,
        'impressions': 0.01, # Often large numbers, so lower weight
        # Reddit
        'upvotes': 1.0,
        'comments': 2.5,
        'awards': 3.0,
        # LinkedIn
        'reactions': 1.0,
        'comments': 2.5, # Shared name, same weight for now
        'views': 0.01,
        # Add other platforms/metrics as needed
    }
    # ---------------------------------------

    def __init__(self, metric_weights: dict | None = None):
        """Initializes the dashboard, optionally accepting custom metric weights."""
        self.metrics = defaultdict(lambda: defaultdict(int))
        self.last_updated = None
        # Use provided weights or defaults
        self.metric_weights = metric_weights if metric_weights is not None else self.DEFAULT_METRIC_WEIGHTS
        log_event("DASHBOARD_INIT", _SOURCE, {"status": "initialized", "weights_used": self.metric_weights})

    def update_metrics(self, platform: str, data: dict):
        """
        Updates the metrics for a given platform.

        Args:
            platform: The name of the social platform (e.g., 'twitter', 'reddit').
            data: A dictionary containing the metrics to update (e.g., {'likes': 5, 'comments': 1}).
                  Assumes these are incremental updates or latest counts.
        """
        log_event("DASHBOARD_UPDATE_START", _SOURCE, {"platform": platform, "incoming_data": data})
        platform = platform.lower()
        
        if not isinstance(data, dict):
             log_event("DASHBOARD_UPDATE_WARN", _SOURCE, {"warning": "Invalid data format received", "platform": platform, "data_type": type(data).__name__})
             return

        for key, value in data.items():
            if isinstance(value, (int, float)):
                # Simple aggregation: overwrite or add based on need.
                # For simplicity, let's assume incoming data is the latest total count.
                self.metrics[platform][key] = value
            else:
                log_event("DASHBOARD_UPDATE_WARN", _SOURCE, {"warning": f"Skipping non-numeric metric value for key '{key}'", "platform": platform, "value_type": type(value).__name__})
        
        self.last_updated = datetime.now(timezone.utc)
        log_event("DASHBOARD_UPDATE_SUCCESS", _SOURCE, {"platform": platform, "updated_metrics": dict(self.metrics[platform])})

    def get_aggregated_metrics(self) -> dict:
        """Returns the current aggregated metrics across all platforms."""
        # Convert defaultdict back to regular dict for cleaner output
        return {platform: dict(metrics) for platform, metrics in self.metrics.items()}

    # --- New Method for Unified Score ---
    def calculate_unified_score(self) -> float:
        """
        Calculates a simple, weighted unified engagement score across all platforms.
        
        Design Notes (Inline Documentation):
        - Formula: Sum(metric_value * metric_weight) for all metrics across all platforms.
        - Rationale: Provides a single number representing overall engagement trend.
                     Higher score indicates higher weighted engagement.
        - Weights: Defined in self.metric_weights. These are crucial and likely need
                   adjustment based on platform specifics and business goals.
                   For example, a comment might be valued more than a like.
        - Limitations: Very basic. Doesn't account for sentiment, reach vs. interaction,
                       platform nuances, or normalization. Different metrics (e.g., 
                       impressions vs. likes) have vastly different scales.
        - Future Improvements: Consider normalization, platform-specific weights,
                            separate scores for reach vs. interaction, sentiment weighting.
        
        Returns:
            A float representing the calculated unified score.
        """
        total_score = 0.0
        log_event("UNIFIED_SCORE_CALC_START", _SOURCE, {"current_metrics": self.get_aggregated_metrics()})

        for platform, platform_metrics in self.metrics.items():
            platform_score = 0.0
            for metric_name, metric_value in platform_metrics.items():
                # Get weight, default to 0 if metric is unknown
                weight = self.metric_weights.get(metric_name.lower(), 0)
                if weight > 0:
                    contribution = metric_value * weight
                    platform_score += contribution
                    # log_event("UNIFIED_SCORE_CALC_DETAIL", _SOURCE, {"platform": platform, "metric": metric_name, "value": metric_value, "weight": weight, "contribution": contribution}) # Potentially too verbose
            
            log_event("UNIFIED_SCORE_CALC_PLATFORM", _SOURCE, {"platform": platform, "platform_score": platform_score})
            total_score += platform_score
            
        log_event("UNIFIED_SCORE_CALC_FINISH", _SOURCE, {"total_unified_score": total_score})
        return total_score
    # --- End New Method ---

    def display_dashboard(self) -> str:
        """
        Generates a simple text-based representation of the dashboard.
        Now includes the calculated unified score.
        """
        output = ["--- Engagement Dashboard ---"]
        if self.last_updated:
            output.append(f"Last Updated: {self.last_updated.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        else:
            output.append("Last Updated: Never")
        output.append("--------------------------")

        if not self.metrics:
            output.append("No metrics data available yet.")
        else:
            for platform, metrics in self.metrics.items():
                output.append(f"\n Platform: {platform.capitalize()}")
                if not metrics:
                    output.append("  - No metrics found.")
                else:
                    for key, value in sorted(metrics.items()):
                        output.append(f"  - {key.capitalize()}: {value}")
        
        # Add unified score
        output.append("\n--------------------------")
        try:
            unified_score = self.calculate_unified_score()
            output.append(f"Unified Engagement Score: {unified_score:.2f}")
        except Exception as score_e:
            output.append(f"Unified Engagement Score: Error calculating ({score_e})")
            log_event("DASHBOARD_DISPLAY_ERROR", _SOURCE, {"error": "Failed to calculate unified score for display", "details": str(score_e)})
            
        output.append("--------------------------")
        return "\n".join(output)

# --- Example Usage --- 
if __name__ == "__main__":
    print("Testing Engagement Dashboard...")
    dashboard = EngagementDashboard()
    
    print("Initial Dashboard:")
    print(dashboard.display_dashboard())
    
    # Simulate updates
    print("\nSimulating updates...")
    dashboard.update_metrics('twitter', {'likes': 15, 'retweets': 3, 'impressions': 1050})
    dashboard.update_metrics('reddit', {'upvotes': 42, 'comments': 8})
    dashboard.update_metrics('linkedin', {'reactions': 12, 'views': 250})
    dashboard.update_metrics('twitter', {'likes': 18, 'replies': 2}) # Update twitter likes, add replies
    dashboard.update_metrics('reddit', {'awards': 1})
    dashboard.update_metrics('instagram', {}) # Platform with no metrics yet
    dashboard.update_metrics('facebook', {'shares': 'many'}) # Test invalid data

    print("\nDashboard After Updates:")
    print(dashboard.display_dashboard())
    
    print("\nGetting Aggregated Metrics (as dict):")
    aggregated = dashboard.get_aggregated_metrics()
    import json
    print(json.dumps(aggregated, indent=2))

    # Test unified score
    print("\nCalculating Unified Score...")
    score = dashboard.calculate_unified_score()
    print(f"Calculated Score: {score}")

    print("\nFinal Dashboard Display (with score):")
    print(dashboard.display_dashboard())

    # Test with custom weights
    print("\nTesting with custom weights (boosting comments)...")
    custom_weights = dashboard.DEFAULT_METRIC_WEIGHTS.copy()
    custom_weights['comments'] = 10.0 # Make comments much more valuable
    custom_weights['replies'] = 8.0 # Make replies much more valuable
    
    dashboard_custom = EngagementDashboard(metric_weights=custom_weights)
    dashboard_custom.update_metrics('twitter', {'likes': 18, 'retweets': 3, 'replies': 2})
    dashboard_custom.update_metrics('reddit', {'upvotes': 42, 'comments': 8, 'awards': 1})
    
    print(dashboard_custom.display_dashboard())

    print("\nDashboard test finished.") 