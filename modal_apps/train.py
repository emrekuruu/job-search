from __future__ import annotations

import modal

BASE_MODEL = "Qwen/Qwen3-8B"
TASKS = ("query_gen", "fit_eval")
MAX_SEQ_LEN = 16384  # long resume + job + reasoning trace must fit without truncation
SEED = 42            # matches settings.random_seed in src/job_search/config.py

# Image deps live in pyproject.toml's `[dependency-groups].train`; Modal calls
# `uv sync --frozen --group train` against the auto-attached pyproject.toml + uv.lock from the
# build context. Qwen3-8B is a pure transformer (GQA) — no CUDA kernels to compile, so plain
# `debian_slim` is sufficient (no CUDA devel image needed). SFT data ships with the image so the
# GPU container reads JSONL from `/root/sft/<task>.{train,val,test}.jsonl`.
image = (
    modal.Image.debian_slim(python_version="3.12")
    .uv_sync(uv_project_dir="./", groups=["train"], gpu="A100")
    .add_local_dir("data/sft", "/root/sft")
)

app = modal.App("job-search-distill")
adapters_vol = modal.Volume.from_name("job-search-adapters", create_if_missing=True)
hf_cache_vol = modal.Volume.from_name("job-search-hf-cache", create_if_missing=True)


@app.function(
    image=image,
    gpu="A100-40GB",
    timeout=6 * 60 * 60,
    volumes={"/adapters": adapters_vol, "/root/.cache/huggingface": hf_cache_vol},
    secrets=[modal.Secret.from_name("huggingface")],
)
def train(task: str) -> None:
    import torch
    from datasets import load_dataset
    from peft import LoraConfig
    from transformers import AutoModelForCausalLM, AutoTokenizer, EarlyStoppingCallback
    from trl import SFTConfig, SFTTrainer

    if task not in TASKS:
        raise ValueError(f"unknown task {task!r}; expected one of {TASKS}")

    # 1) Tokenizer.
    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    # 2) Load the pre-split train / val / test datasets.
    #    Drop-guard each — never truncate; losing the JSON answer at the end of an assistant label
    #    corrupts the training signal. Splits are produced by `sft_format.py` with a seeded shuffle,
    #    so the train file is already randomized; HF Trainer further shuffles via RandomSampler.
    def _load_and_filter(suffix: str):
        path = f"/root/sft/{task}.{suffix}.jsonl"
        ds = load_dataset("json", data_files=path, split="train")
        n_before = len(ds)
        ds = ds.filter(
            lambda ex: len(tokenizer.apply_chat_template(ex["messages"], tokenize=True))
            <= MAX_SEQ_LEN
        )
        print(f"{suffix}: kept {len(ds)}/{n_before} examples within {MAX_SEQ_LEN} tokens")
        return ds

    train_ds = _load_and_filter("train")
    val_ds = _load_and_filter("val")
    test_ds = _load_and_filter("test")

    # 3) Model in bf16 with SDPA. `AutoModelForCausalLM` resolves to `Qwen3ForCausalLM` cleanly
    #    (Qwen3 isn't multimodal). `dtype=` not `torch_dtype=` (latter is deprecated).
    model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL,
        dtype=torch.bfloat16,
        device_map="auto",
        attn_implementation="sdpa",
    )

    # 4) LoRA. Standard Qwen targets. PEFT initializes lora_B = 0, so at init the adapter is a
    #    mathematical no-op — `trainer.evaluate(test_ds)` before `trainer.train()` gives a true
    #    base-model baseline.
    peft_config = LoraConfig(
        r=16,
        lora_alpha=16,
        lora_dropout=0,
        bias="none",
        task_type="CAUSAL_LM",
        target_modules=[
            "q_proj", "k_proj", "v_proj", "o_proj",
            "gate_proj", "up_proj", "down_proj",
        ],
    )

    # 5) SFTConfig.
    #    - assistant_only_loss=True: trl v1 masks loss to the assistant span.
    #    - eval/save_strategy="epoch" + load_best_model_at_end + EarlyStoppingCallback: eval val
    #      every epoch, save per-epoch checkpoints, stop if val_loss hasn't improved for 2 evals,
    #      load best adapter before final save.
    #    - seed + data_seed: full reproducibility (model init, dataloader sampling).
    #    - weight_decay: standard LoRA regularization.
    #    - bf16_full_eval: keep eval precision identical to train (eval_loss defaults to fp32).
    #    - report_to="none": silence wandb/tensorboard noise in Modal logs.
    out_dir = f"/adapters/{task}"
    sft_config = SFTConfig(
        output_dir=out_dir,
        num_train_epochs=3,
        per_device_train_batch_size=1,
        per_device_eval_batch_size=1,
        gradient_accumulation_steps=8,
        learning_rate=2e-4,
        lr_scheduler_type="cosine",
        warmup_steps=20,
        weight_decay=0.01,
        bf16=True,
        bf16_full_eval=True,
        optim="adamw_torch",
        max_length=MAX_SEQ_LEN,
        packing=False,
        gradient_checkpointing=True,
        gradient_checkpointing_kwargs={"use_reentrant": False},
        assistant_only_loss=True,
        logging_steps=5,
        eval_strategy="epoch",
        save_strategy="epoch",
        save_total_limit=2,
        load_best_model_at_end=True,
        # With a dict `eval_dataset` the metric name is prefixed by the key
        # (eval_val_loss, eval_test_loss). We only ever use VAL for selection
        # and early stopping — test is observational.
        metric_for_best_model="eval_val_loss",
        greater_is_better=False,
        seed=SEED,
        data_seed=SEED,
        report_to="none",
    )

    # `eval_dataset` as a dict so BOTH val and test go through SFTTrainer's `_prepare_dataset`
    # (chat-template + tokenize + assistant-mask). The tokenized versions are then accessible
    # as `trainer.eval_dataset["val"]` and `trainer.eval_dataset["test"]`.
    # NOTE: this means test_loss is also computed at every epoch — purely observational
    # (selection + early stopping use eval_val_loss only).
    trainer = SFTTrainer(
        model=model,
        args=sft_config,
        train_dataset=train_ds,
        eval_dataset={"val": val_ds, "test": test_ds},
        peft_config=peft_config,
        processing_class=tokenizer,
        callbacks=[EarlyStoppingCallback(early_stopping_patience=2)],
    )

    # Tokenized test set for explicit pre/post-training evals.
    test_tokenized = trainer.eval_dataset["test"]

    # 6) Baseline: evaluate the BASE model on the held-out test set BEFORE training.
    #    PEFT's lora_B=0 init makes the wrapped model mathematically identical to the base, so
    #    this is a clean baseline. `metric_key_prefix="base_test"` produces base_test_loss.
    print(f"\n=== BASE MODEL test-set eval ({len(test_tokenized)} examples) ===")
    base_metrics = trainer.evaluate(eval_dataset=test_tokenized, metric_key_prefix="base_test")
    print(base_metrics)

    # 7) Train.
    trainer.train()

    # 8) Trained adapter on the held-out test set. `load_best_model_at_end=True` means the
    #    adapter we evaluate here is the best-eval_val_loss epoch, not necessarily the last.
    print(f"\n=== TRAINED ADAPTER test-set eval ({len(test_tokenized)} examples) ===")
    trained_metrics = trainer.evaluate(eval_dataset=test_tokenized, metric_key_prefix="final_test")
    print(trained_metrics)

    base_loss = base_metrics.get("base_test_loss")
    trained_loss = trained_metrics.get("final_test_loss")
    if base_loss is not None and trained_loss is not None:
        delta = trained_loss - base_loss
        pct = (delta / base_loss * 100) if base_loss else 0.0
        print(
            f"\n=== Δ test loss: {base_loss:.4f} -> {trained_loss:.4f} "
            f"({delta:+.4f}, {pct:+.1f}%) ==="
        )

    # 9) Save LoRA adapter + tokenizer to the shared Volume; serve.py mounts the same Volume.
    trainer.save_model(out_dir)
    tokenizer.save_pretrained(out_dir)
    adapters_vol.commit()
    print(f"saved adapter -> {out_dir}")


@app.local_entrypoint()
def main(task: str = "query_gen") -> None:
    train.remote(task)
