import ollama


def generate_reply(post_text):
    """
    Generates a response using the fine-tuned model.
    The prompt is formatted to include the original post and an empty 'Reply:'.
    """
    prompt = f"Post: {post_text}\nReply:"
    # Use the model name from your fine-tuning step (adjust if using DeepSeek)
    response = ollama.chat(
        model="fine-tuned-mistral", messages=[{"role": "user", "content": prompt}]
    )
    return response["message"]["content"]


# Example usage
if __name__ == "__main__":
    test_post = "What’s next for $TSLA? Tesla is consolidating around resistance. What’s your take?"
    reply = generate_reply(test_post)
    print("🤖 AI Reply:", reply)
