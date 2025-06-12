from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    Trainer,
    TrainingArguments,
    DataCollatorForLanguageModeling,
)
from datasets import load_dataset
from peft import LoraConfig, get_peft_model
import torch
import multiprocessing
import os

# ✅ Enable multi-threading for CPU efficiency
torch.set_num_threads(os.cpu_count())

# ✅ Model Selection (Switch to a Lighter Model if Needed)
model_name = "mistralai/Mistral-7B-v0.1"

# ✅ Load tokenizer & model
tokenizer = AutoTokenizer.from_pretrained(model_name)

# 🚀 **Fix: Add missing special tokens & set padding token**
special_tokens = {"pad_token": "[PAD]", "bos_token": "[START]", "eos_token": "[END]"}
tokenizer.add_special_tokens(special_tokens)

# ✅ Load model optimized for CPU
model = AutoModelForCausalLM.from_pretrained(
    model_name,
    torch_dtype=torch.float16,  # ✅ FP16 reduces memory load
    device_map="cpu",
    offload_folder="./offload_weights",  # ✅ Prevents meta tensor issues
    use_flash_attention_2=False,  # ✅ Not needed on CPU
)

# ✅ **Optimize for Large Vocabulary**
model.tie_weights()
model.resize_token_embeddings(len(tokenizer))

print("✅ Model & tokenizer loaded.")

# ✅ Load dataset & split for evaluation
dataset = load_dataset(
    "json", data_files="../data/raw/ollama_training_data.jsonl", split="train"
)
split_dataset = dataset.train_test_split(test_size=0.1)  # ✅ 10% for evaluation
train_dataset, eval_dataset = split_dataset["train"], split_dataset["test"]


# ✅ **Extract & Format Messages**
def tokenize_function(batch):
    prompts, responses = [], []

    for entry in batch["messages"]:
        if isinstance(entry, list):
            user_prompt = " ".join(
                [
                    f"[USR] {msg['content'].strip()}"
                    for msg in entry
                    if msg["role"] == "user"
                ]
            )
            assistant_response = " ".join(
                [
                    f"[AI] {msg['content'].strip()}"
                    for msg in entry
                    if msg["role"] == "assistant"
                ]
            )

            formatted_prompt = f"[SYS] Write a response that matches Victor Dixon's style.\n{user_prompt}\n"
            formatted_response = f"{assistant_response} [END]"

            prompts.append(formatted_prompt)
            responses.append(formatted_response)
        else:
            prompts.append("")
            responses.append("")

    return tokenizer(
        prompts, text_pair=responses, truncation=True, padding="longest", max_length=512
    )


# ✅ Apply tokenization
train_dataset = train_dataset.map(
    tokenize_function, batched=True, remove_columns=["messages"]
)
eval_dataset = eval_dataset.map(
    tokenize_function, batched=True, remove_columns=["messages"]
)
print("✅ Dataset tokenized.")

# ✅ Apply LoRA (Memory Efficient)
peft_config = LoraConfig(
    r=4,  # ✅ Reduce rank for lower memory use
    lora_alpha=8,  # ✅ Adjust scaling factor
    target_modules=["q_proj", "v_proj"],
    lora_dropout=0.1,
    bias="none",
)

model = get_peft_model(model, peft_config)
print("✅ LoRA applied. Ready for fine-tuning.")

# ✅ Training Configuration (Optimized for CPU Stability)
training_args = TrainingArguments(
    output_dir="./fine-tuned-mistral",
    per_device_train_batch_size=1,  # ✅ Prevent memory overload
    per_device_eval_batch_size=1,
    num_train_epochs=1,  # ✅ Start with 1 epoch (we can increase later)
    save_strategy="epoch",
    evaluation_strategy="epoch",  # ✅ Evaluate at end of each epoch
    logging_dir="./logs",
    fp16=False,  # ❌ Disable FP16 (better for GPU, not CPU)
    bf16=False,  # ❌ Disable BFloat16 (only useful on some CPUs)
    report_to="none",
    save_total_limit=1,
    gradient_checkpointing=True,  # ✅ Saves memory
    dataloader_num_workers=0,  # ✅ Fix Windows multiprocessing issue (set to 0)
    gradient_accumulation_steps=4,  # ✅ Reduce memory pressure by updating less frequently
)


if __name__ == "__main__":
    multiprocessing.freeze_support()  # ✅ Fixes Windows multiprocessing issue
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=eval_dataset,
        data_collator=DataCollatorForLanguageModeling(tokenizer, mlm=False),
    )

    # ✅ Start fine-tuning
    trainer.train()

    # ✅ Save model
    model.save_pretrained("fine_tuned_mistral")
    tokenizer.save_pretrained("fine_tuned_mistral")

    print("🚀 Fine-tuning complete. Model saved as 'fine_tuned_mistral'")
