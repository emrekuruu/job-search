# Job Searcher

Job hunting as a new grad is a full-time job by itself. You sift through hundreds of postings every week to find a handful worth applying to. You click "Easy Apply" until your eyes hurt. You write the same cover letter forty times. By month two of a search, you're applying to roles you wouldn't take, in industries you don't care about, because at that point the cost of *thinking* about each listing is higher than the cost of submitting to one.

> **Watch the short tour:** drop a resume, watch the queries stream, read the per-job reasoning.

<video controls width="100%" src="assets/demo.mp4"></video>

## How it works

A run has three steps.

1. **Queries.** The student reads the resume and the preferences you set (job type, work modality, location, free-form notes) and drafts a small set of LinkedIn-shaped search queries, reasoning out loud as it goes.
2. **Search.** Those queries hit LinkedIn through [JobSpy](https://github.com/Bunsly/JobSpy), one at a time.
3. **Scoring.** For each posting, the model reads the `(resume, job)` pair and writes a five-dimension fit score:
   - **skills match**
   - **experience relevance**
   - **education and certifications**
   - **industry / domain fit**
   - **seniority alignment**

![Inference pipeline](../assets/figures/pipeline.svg)

*Figure 1. End-to-end steps of the framework.*

> What you get back isn't a list of fifty roles. It's a small shortlist with defensible reasoning. You can read why the model thinks the second-ranked job beats the third.

## Technical Details

### Dataset Curation - The teacher and the student

The teacher is **DeepSeek V4 Pro**. Strong at structured reasoning, willing to follow a strict output schema, cheap enough to run once over a large corpus offline. It is used as a label generator, not as an inference-time dependency.

The student is **Qwen3-8B**. Small enough to fit on a single ZeroGPU slice once quantized to Q4_K_M, large enough to absorb the teacher's structured judgement.

The corpus came from a closed loop, resume-aware end-to-end:

- **Resumes.** 2,500, built on [Divyaamith/Kaggle-Resume](https://huggingface.co/datasets/Divyaamith/Kaggle-Resume).
- **Queries.** The teacher first drafted LinkedIn-shaped search queries from each resume.
- **Jobs.** JobSpy then scraped LinkedIn for what those queries actually returned. About 10,000 postings, every one of them surfaced by a query the teacher itself wrote for that specific resume.
- **Labels.** The teacher then scored every resulting `(resume, job)` pair across the same five dimensions used at inference, with one sentence of reasoning per dimension.

Everything ships in four foreign-key-clean configs at [`emrekuruu/job-search-distill`](https://huggingface.co/datasets/emrekuruu/job-search-distill).

### Training (Modal)

Two LoRA SFT runs on a single A100 via [Modal](https://modal.com), one per task:

- **Adapter.** Rank 16, alpha 16, dropout off, attention plus MLP projections.
- **Schedule.** One epoch per task. Mid-epoch checkpoints every 200 steps so a partial run could be sanity-checked before the full one finished.
- **Output.** Safetensors at [`emrekuruu/job-searcher-qwen3-8B`](https://huggingface.co/emrekuruu/job-searcher-qwen3-8B), and a Q4_K_M base plus LoRA-GGUF sidecars at [`emrekuruu/job-searcher-qwen3-8B-gguf`](https://huggingface.co/emrekuruu/job-searcher-qwen3-8B-gguf) for the llama.cpp serving path.

```python
LoraConfig(
    r=16,
    lora_alpha=16,
    task_type="CAUSAL_LM",
    target_modules=[
        "q_proj", "k_proj", "v_proj", "o_proj",
        "gate_proj", "up_proj", "down_proj",
    ],
)
```

### The Space - Inference (llama.cpp)

The Space runs `llama-cpp-python` with the pre-built CUDA wheel on a HuggingFace ZeroGPU Space. Two design choices that matter:

- **`Llama` inside `@spaces.GPU`.** ZeroGPU recycles the CUDA context per call, so a module-level instance would hold a dead context on the second use.
- **One GPU call per submission, not per job.** All fit evaluations for one submission run inside a single `@spaces.GPU` call. The model loads once and yields events for every job, instead of paying a fresh cold start and a fresh proxy-token request per posting.

Streaming uses the OpenAI-shaped `create_chat_completion(stream=True)` so the reasoning lands in the UI token by token. The live demo is at [`emrekuruu/job-search-assistant`](https://huggingface.co/spaces/emrekuruu/job-search-assistant).

### The traces

The entire Claude Code session that built this Space is published as an HuggingFace agent-traces dataset at [`emrekuruu/job-search-assistant-agent-trace`](https://huggingface.co/datasets/emrekuruu/job-search-assistant-agent-trace). Raw JSONL events, native HuggingFace trace viewer, every dead end and recovery on the record. Useful if you want to see how this thing actually came together rather than read the cleaned-up version of it.

## Try it

Drop your resume at [huggingface.co/spaces/emrekuruu/job-search-assistant](https://huggingface.co/spaces/emrekuruu/job-search-assistant). Stop sifting.

## What I learned

**Two adapters beat one.** I tried folding query generation and fit evaluation into a single LoRA. The model leaked formatting both ways, JSON on the query task and prose on the eval. Splitting them into two heads on the same base, hot-swapped per call, killed the whole class of bugs.

**The teacher's prompt mattered more than the student's size.** Rewriting the teacher's labelling prompt to score against specific resume details ("four years of Rust; the role asks for five" instead of "strong technical match") propagated through distillation. The student picked up the same habit.

