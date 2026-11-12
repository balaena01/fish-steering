# FiSH: Formula-instantiated Scene-gated Hidden units

Article: https://balaena01.github.io/fish-steering/ (Japanese: https://balaena01.github.io/fish-steering/#ja)

FiSH takes a few MLP neurons that do very little, replaces their weights with values computed from data, and turns them into switches: when the model is replying in one kind of scene they write a tone into the reply, and otherwise they write nothing. There is no training and no system prompt. The result is a LoRA for stock llama.cpp.

The tool is [gguf-neuron-explorer](https://github.com/balaena01/gguf-neuron-explorer) (`gne`), v0.3.2 or later.

## What is here

| Path | Contents |
|---|---|
| `index.html` | The article, English with a Japanese switch |
| `case1/` | Qwen3.5-4B (Q8_0), a tsundere tone in replies to thanks and compliments |
| `case1/sets/` | The contrast set (`contrast.yaml`), three evaluation sets (`set1` to `set3`: 100 scene prompts and 130 others each) and the prompts used only for searching |
| `case1/replies/set*/` | Every reply, by condition and decoding, with token counts and the mechanical repetition flag (`loop`). `model_scores` is the model's own scoring of its replies |
| `case1/labels/set*/` | The blind readers' classes (`labels.json`), the instructions they were given, the shuffled files they read (`blind/`) and the key back to conditions |
| `case1/search/` | The search over layers and strengths (vectors added directly), with a table of every candidate |
| `case1/recipe/` | The units of the tuned form and the first form, the neurons used, the amounts written per reply position, and the LoRA of the tuned form |
| `case2/` | The same test on [Swift-1.5-Qwen3.8-27B](https://huggingface.co/ukisai/Swift-1.5-Qwen3.8-27B-GSQ-RCO-GGUF), IQ2_XS file. Same layout, one evaluation set (100 scene prompts and 80 others) |
| `case3/` | A second persona on the same 27B file: a cheerful, casual tone in replies to worries and requests for advice. Same layout as `case2/`, one evaluation set (100 scene prompts and 80 others) |
| `case3/reader_check/` | The 108 replies (to `case3/sets/reader_check.json`) on which the reader's definitions were checked before the final test, the shuffled file that was read, and the two independent sets of labels |
| `case3/recipe/` | The units, the neurons used, the LoRA, and the amounts written per reply position (`amounts_contrast.json`, measured on the prompts of the contrast set, not on the evaluation set) |
| `case*/criteria.md` | The pass criteria fixed before each final test, the changes made to them, and how each one came out, including the ones that failed |
| `case*/scripts/fish_numbers.py` | Recounts the numbers in the article's tables for that case from the files here. `numbers.json` next to it is its saved output |
| `case1/scripts/make_figures.py` | Draws the article's figures (SVG) from those numbers |

Case 3 has no `search/`: its layers and strengths were taken unchanged from case 2. Its replies carry no `model_scores`.

Reader classes: `T` in the target tone, `S` shy but plain, `N` plain, `B` repetition or unreadable, `M` does not fit the prompt. Case 3 uses `E` cheerful and casual and `C` somewhat casual in place of `T` and `S`. The readers were instances of Claude, working from `reader_instructions.md`, which is published exactly as they received it.

Conditions: `no_edit`, `system_prompt`, `fish_tuned` (13 layers, strength 1 / 1 / 0.8), `fish_first_form` (3 layers, strength 0.9), `fish` (cases 2 and 3: 13 layers, strength 1.2 / 1.2 / 0.96), `*_shuffled_key` (the same edit with a key built from shuffled scene labels), `direct_add` (the same vectors added to the layer outputs, no neurons), `fish_threshold_0.5-0.9` (a variant that did not help). Decoding: `greedy`, or `sampled_seedN` at temperature 0.7.

Prompt groups: `target` (the scene), and the unrelated groups `facts`, `ordinary` and `english` (in case 3: `facts`, `howto` and `english`).

## The models

- Case 1: Qwen3.5-4B, Q8_0 GGUF.
- Case 2: the IQ2_XS file from https://huggingface.co/ukisai/Swift-1.5-Qwen3.8-27B-GSQ-RCO-GGUF. The case 2 LoRA only works together with that file.
- Case 3: the same file as case 2. The case 3 LoRA only works together with that file.

LoRA files, written from the recipes with `gne nw export` and applied with llama.cpp's `--lora` at scale 1. Each was checked by generating, with the file applied, the replies to the first 16 prompts of every group of the evaluation set (set 2 for case 1) with greedy decoding and comparing them with the replies saved in `replies/`:

- `case1/recipe/fish_tuned.lora.gguf` (11.0 MB, sha256 `f4654023d1277baf5f931d1cc11bd2af2e26481628e66ec677c35f98ce5e8c9f`), for Qwen3.5-4B, Q8_0. Check: 64 of 64 replies identical to the saved ones, 64 of 64 with the same first 30 characters.
- `case2/recipe/fish.lora.gguf` (21.1 MB, sha256 `3a315020bed1839800951914ac038d03e6581ded356096b7e57d74ad9c1ea525`), for the IQ2_XS file from https://huggingface.co/ukisai/Swift-1.5-Qwen3.8-27B-GSQ-RCO-GGUF. Check: 64 of 64 replies identical to the saved ones, 64 of 64 with the same first 30 characters.
- `case3/recipe/fish.lora.gguf` (21.1 MB, sha256 `272bdfabd9236a0c5ce56ba77cf19f1cfd9e322541d91c61c70869db4f2b87a1`), for the IQ2_XS file from https://huggingface.co/ukisai/Swift-1.5-Qwen3.8-27B-GSQ-RCO-GGUF. Check: 64 of 64 replies identical to the saved ones, 64 of 64 with the same first 30 characters.

## Checking the numbers

Every number in the article's tables can be recounted from `replies/`, `labels/` and the answer patterns in `sets/`. No GPU and no model are needed, only Python 3 with its standard library:

```bash
python case1/scripts/fish_numbers.py     # Qwen3.5-4B: sets 1 to 3, the search, the amounts written
python case2/scripts/fish_numbers.py     # the 27B model
python case3/scripts/fish_numbers.py     # the second persona
python case1/scripts/make_figures.py     # the figures, written to case1/scripts/figures/
```

Each `fish_numbers.py` prints its numbers and writes them to `numbers.json` next to itself. The scripts find the files from their own location, so they can be run from any directory. The pass criteria and their results are in each `criteria.md`, with the numbers taken from the same recount.

These are the scripts behind the tables and figures. The scripts that generated the replies are not included: they are tied to the layout and the condition names of the working folder. How the replies were generated (conditions, decoding, token limit, what was read blind) is described in each `criteria.md`, the commands that build an edit are in the article under "Reproduce", and the LoRA files here give the measured edits directly.

## Credits and license

By Kujirachan / くじら ([@balaena01](https://x.com/balaena01)), with Claude (Anthropic). Scripts are MIT licensed (see `LICENSE`). The prompts were written for this project.
