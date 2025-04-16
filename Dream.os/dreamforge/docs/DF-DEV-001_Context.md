# Task Context: DF-DEV-001 - Implement Sentiment Analysis for SocialAgent

**Related Social Task:** `social-new-003`

## 1. Goal

Integrate sentiment analysis capabilities into the social media monitoring process. Specifically, analyze the sentiment of scraped mentions (initially from Twitter/X, potentially Reddit later) to gauge community feedback and reaction.

## 2. Core Requirements

1.  **Library Integration:** Use a standard Python library for sentiment analysis. NLTK with the VADER lexicon (`nltk.sentiment.vader.SentimentIntensityAnalyzer`) is recommended due to its suitability for social media text and relative ease of use. Add `nltk` to the main `requirements.txt` file.
2.  **Code Modification:** Determine the best place to integrate the analysis. Options:
    *   Within the relevant strategy's scraping methods (e.g., `twitter_strategy.py`, `reddit_strategy.py`) immediately after parsing mention text.
    *   Within the `SocialMediaAgent`'s `process_incoming_message` method when handling the results of a `scrape_mentions` command.
    *   (Consider modularity - perhaps a dedicated utility function called by the agent/strategy).
3.  **Data Enrichment:** Modify the data structure returned by scraping methods (e.g., the list of mention dictionaries) to include sentiment information. Suggested fields:
    *   `sentiment_score` (e.g., VADER's compound score ranging from -1 to 1).
    *   `sentiment_label` (e.g., 'positive', 'neutral', 'negative' based on score thresholds).
4.  **Logging:** Log the sentiment analysis outcome for each analyzed mention using `governance_memory_engine.log_event`. Define a suitable `event_type` (e.g., `MENTION_SENTIMENT_ANALYZED`) and include relevant details (mention ID/URL, text snippet, score, label).

## 3. Relevant Files

*   **Primary Target(s):**
    *   `social/social_media_agent.py`
    *   `social/strategies/twitter_strategy.py`
    *   `social/strategies/reddit_strategy.py` (If extending)
*   **Dependencies/Related:**
    *   `governance_memory_engine.py` (for logging)
    *   `requirements.txt` (for adding nltk)
    *   `social/task_list.json` (Original task source: `social-new-003`)

## 4. Implementation Notes

*   Ensure the NLTK VADER lexicon is downloaded if required (`nltk.download('vader_lexicon')`). Handle this appropriately (e.g., documentation, setup script, or within the code with checks).
*   Define clear thresholds for classifying the sentiment score into labels (positive/neutral/negative).
*   Handle potential errors during sentiment analysis gracefully (e.g., empty text).
*   Add unit tests for the sentiment analysis logic.

## 5. Acceptance Criteria

*   `nltk` is added to `requirements.txt`.
*   Sentiment analysis is performed on scraped mentions.
*   Mention data includes `sentiment_score` and `sentiment_label`.
*   Sentiment results are logged via `log_event`.
*   Code is reasonably modular and includes error handling.
*   Relevant unit tests are added. 