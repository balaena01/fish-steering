# case10: the output after the acknowledgment marker "◇" (part 2, added 2026-11-18)

Qwen3.5-4B (Q8_0), greedy decoding, one run, replies generated until they finished (up to 2,048 tokens). A reply is degraded if "◇" appears again after its first character, or if `loop` (mechanical repetition, gne's `loop_like`) is true.

| Path | Contents |
|---|---|
| `replies/cause/` | The 280 acknowledgment inputs of the development set under four conditions: `marker_only` (no edit, first token fixed to "◇"), `vector_at_position0` (the acknowledgment switch's vector added at position 0 only), `fish` (the end-of-turn form) and `no_edit`. The inputs are `case5/sets/search.json` (`development:<kind>:<i>`) and `case5/sets/eval_first.json` (`first_evaluation:<kind>:<i>`) |
| `sets/eval.json` | The 400 evaluation inputs (used once), with the answer patterns of the factual questions |
| `replies/eval/` | Replies to them: `no_edit`, `part2_form` ("■" + "◇"), `fish`, `system_prompt` (the one chosen in part 2), `end_after_sentence` (the switch that ends an acknowledgment after one sentence), `end_after_sentence_stage2` (its second-stage key) and `lower_marker` (the switch that lowers "◇") |
| `sets/english.json`, `replies/english/` | 40 English inputs and their replies (a check added after seeing the results) |
| `labels/` | The blind evaluators' sorting of the acknowledgment replies (G fits / E repeats or mixes up / M does not fit / B broken): the instructions as they received them (only the folder of the file paths removed), the two batches, their answers, which condition each item was (`key.json`) and the 40 items both read |
| `recipe/switch.json` | How the switches were built, the key outputs after position 0, and `gne eval` |

The inputs were written by instances of Claude; no human checked them. `python part2/recount.py` recounts the numbers of the addition (block `case10` of `part2/recount.json`). The key outputs after position 0 and `gne eval` need the model and are copied from the measurement.

Not included: the keys, the direction files and the LoRA (written by experimental scripts), the development replies of the candidates, and the hidden states.
