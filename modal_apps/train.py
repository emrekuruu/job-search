from __future__ import annotations

import modal

BASE_MODEL = "Qwen/Qwen3.5-9B"
TASKS = ("query_gen", "fit_eval")

image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install(
        "torch==2.6.0",
        "transformers==4.49.0",
        "trl==0.15.2",
        "peft==0.14.0",
        "accelerate==1.4.0",
        "bitsandbytes==0.45.3",
        "datasets==3.3.2",
    )
    .add_local_dir("data/sft", "/root/sft")
)

app = modal.App("job-search-distill")
adapters_vol = modal.Volume.from_name("job-search-adapters", create_if_missing=True)
hf_cache_vol = modal.Volume.from_name("job-search-hf-cache", create_if_missing=True)


@app.function(
    image=image,
    gpu="A100-40GB",
    timeout=4 * 60 * 60,
    volumes={"/adapters": adapters_vol, "/root/.cache/huggingface": hf_cache_vol},
    secrets=[modal.Secret.from_name("huggingface")],
)
def train(task: str) -> None:
    import torch
    from datasets import load_dataset
    from peft import LoraConfig, prepare_model_for_kbit_training
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
    from trl import SFTConfig, SFTTrainer

    if task not in TASKS:
        raise ValueError(f"unknown task {task!r}; expected one of {TASKS}")

    dataset = load_dataset("json", data_files=f"/root/sft/{task}.jsonl", split="train")

    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    bnb = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16,
        bnb_4bit_use_double_quant=True,
    )
    model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL, quantization_config=bnb, torch_dtype=torch.bfloat16, device_map="auto"
    )
    model = prepare_model_for_kbit_training(model)

    peft_config = LoraConfig(
        r=16,
        lora_alpha=32,
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM",
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
    )

    out_dir = f"/adapters/{task}"
    sft_config = SFTConfig(
        output_dir=out_dir,
        num_train_epochs=3,
        per_device_train_batch_size=1,
        gradient_accumulation_steps=8,
        learning_rate=2e-4,
        lr_scheduler_type="cosine",
        warmup_ratio=0.03,
        logging_steps=5,
        bf16=True,
        max_length=8192,
        packing=False,
        # Loss only on assistant turns; Qwen's chat template marks generation spans.
        assistant_only_loss=True,
    )

    trainer = SFTTrainer(
        model=model,
        args=sft_config,
        train_dataset=dataset,
        peft_config=peft_config,
        processing_class=tokenizer,
    )
    trainer.train()
    trainer.save_model(out_dir)
    tokenizer.save_pretrained(out_dir)
    adapters_vol.commit()
    print(f"saved adapter -> {out_dir}")


@app.local_entrypoint()
def main(task: str = "query_gen") -> None:
    train.remote(task)
