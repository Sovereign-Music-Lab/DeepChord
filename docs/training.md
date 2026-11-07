# Private MLX LoRA workflow

Use a local MLX-compatible model with `config.json`, tokenizer files and `.safetensors` weights. Ollama's storage layout and model tags are not training inputs. Obtain the model separately under its terms; no model download is triggered by the training command. The tested backend is `mlx-lm[train]==0.32.2` on Apple Silicon.

## Review and group your examples

Each line in a private JSONL input must be an object with:

- `reviewed: true`: the data owner has reviewed the symbolic composition and its use for training.
- `group_id`: all revisions/transpositions/variants of one original composition share this ID, to keep them in one split.
- `messages`: exactly one nonempty user request and one assistant response. The response content is a JSON string matching the composition schema (`title`, `tempo`, `bars`, `chords`, `tracks`). See the `demo` output for an editable example.

Do not copy book passages or unreviewed model replies into this dataset. A positive feedback rating alone is not an approval to train. The tool validates note events and its limited chord vocabulary before preparing data. This does not replace human musical or data-use review.

`train prepare` requires at least three original groups; it deterministically assigns groups to train/validation/test using seed 42. Duplicate target compositions cannot cross splits. For useful evaluation, use substantially more independent compositions and hold out entire pieces/styles as appropriate. Output directories must be new. Split files are hashed at preparation; training refuses data changed afterward.

## Train

`train run` uses batch size 1, two LoRA layers, prompt masking, gradient checkpointing, a 2,048-token limit and an explicit iteration count. Examples exceeding 2,048 tokens are rejected before training, rather than silently truncated. Review memory consumption before scaling up. It writes a private run manifest, logs and adapters, then evaluates loss on the held-out test split. All backend loading is offline; remote code execution and external reporting services are not enabled.

`train generate` reloads the exact local base path with the adapter. `compose --adapter` also uses this path and applies the same JSON/MIDI validation as the Ollama route. Adapter output is not guaranteed to satisfy the schema; invalid output is rejected. Do not assume an adapter trained on one model can be applied to another model or used in Ollama without a compatible conversion process.

## Pipeline smoke test

```sh
deepchord train smoke-data --out /path/to/private/smoke/reviewed.jsonl
deepchord train prepare /path/to/private/smoke/reviewed.jsonl --out /path/to/private/smoke/data
deepchord train run --model /path/to/small/local-mlx-model --data /path/to/private/smoke/data --out /path/to/private/smoke/adapter --iters 3
```

The smoke generator creates synthetic chord exercises from code. The examples are closely related and are **only an infrastructure test**, not a legitimate benchmark of generalization or musical improvement. Never mix them into a production evaluation set. Three iterations are not a useful completed musical training program.

The development test used `mlx-community/Qwen2.5-0.5B-Instruct-4bit` at revision `a5339a4131f135d0fdc6a5c8b5bbed2753bbe0f3`; neither it nor its adapter is distributed here. No Gemma LoRA training or compatibility is claimed.

Sources: [MLX LoRA documentation](https://github.com/ml-explore/mlx-lm/blob/main/mlx_lm/LORA.md), [smoke-test model card](https://huggingface.co/mlx-community/Qwen2.5-0.5B-Instruct-4bit).
