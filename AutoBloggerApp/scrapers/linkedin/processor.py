import json
import re

# Load LinkedIn posts
with open("linkedin_posts.json", "r", encoding="utf-8") as f:
    posts = json.load(f)


# Preprocessing function
def clean_text(text):
    """Cleans text by removing unnecessary spaces, symbols, and formatting."""
    text = re.sub(r"\s+", " ", text)  # Remove extra spaces
    text = text.strip()  # Trim whitespace
    return text


# Extract structured data
processed_data = []
for post in posts:
    if "text" in post:
        clean_post = clean_text(post["text"])
        processed_data.append(
            {
                "original": clean_post,
                "generated_reply": "",  # Placeholder for AI-generated replies
            }
        )

# Save processed dataset
with open("linkedin_processed.json", "w", encoding="utf-8") as f:
    json.dump(processed_data, f, indent=4)

print(f"✅ Processed {len(processed_data)} posts. Ready for AI training.")
