# case9: routing in conversations beyond the first turn (part 2, added 2026-11-18)

Qwen3.5-4B (Q8_0), greedy decoding, one run. The end-of-turn form of part 2 (no reply = an empty reply through the end-of-turn token; acknowledgment = a reply that starts with "◇"; answer = anything else), measured on second turns, third turns or later, and first turns under a short role system prompt: first with the original keys (built on first turns only), then with keys rebuilt from conversations of all these shapes.

| Path | Contents |
|---|---|
| `sets/build.json` | The 600 conversations added to the build set of the rebuilt keys (second turns, third turns or later, 6 roles). The 1,000 first turns are `case5/sets/build.json` |
| `sets/development.json` | The development conversations. The 300 first turns are `case5/sets/search.json` |
| `sets/eval.json` | The 600 evaluation conversations (used once) |
| `sets/roles.json` | The role system prompts |
| `replies/development/` | Where the original keys break: the replies (48 tokens), the key outputs at position 0, and the replies with the vector added directly at position 0 |
| `replies/eval/` | Replies of the original keys, the rebuilt keys and the system prompt chosen in part 2 (up to 2,048 tokens), and of the model without any edit (48 tokens) |
| `probe/eval.json` | Which evaluation inputs a linear probe on the hidden state at position 0 routed correctly |
| `recipe/keys.json` | How the rebuilt keys were built, and `gne eval` |

Each conversation has `earlier_inputs` (the user's earlier inputs), `earlier_replies` (the assistant's earlier replies, written by the model without any edit, greedy, up to 768 tokens; cut off where `earlier_replies_finished` is false) and `q` (the last input); `route` is its correct group. The inputs were written by instances of Claude; no human checked them. `python part2/recount.py` recounts the numbers of the addition (block `case9` of `part2/recount.json`).

Not included: the keys, the direction files and the LoRA (written by experimental scripts), the replies of the candidates that were not chosen, and the hidden states.
