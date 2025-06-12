import json


def format_for_ollama():
    with open("linkedin_posts.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    with open("ollama_training_data.jsonl", "w", encoding="utf-8") as f:
        for post in data:
            json.dump(
                {
                    "messages": [
                        {"role": "user", "content": f"Post: {post['text']}"},
                        {"role": "assistant", "content": "Reply: (Your response here)"},
                    ]
                },
                f,
            )
            f.write("\n")

    print("✅ Training data saved as 'ollama_training_data.jsonl'")


if __name__ == "__main__":
    format_for_ollama()
