# Case 8: removing a system-prompt tone on questions only (Qwen3.5-4B)

Part 3 of the FiSH article, section 3 (the first subject, stopped early), and figure 2: https://balaena01.github.io/fish-steering/part3/

The model was given the tsundere system prompt of case 1 (in every reply file as `system`). The edit was to remove that tone in replies to questions (`remove`: arithmetic, facts, how-to) and keep it in replies to thanks and compliments (`keep`), by removing the component along a tone direction in layers 11 to 23, switched by a key. The switch worked, but the removed tone mostly turned into a shy tone or broken output rather than plain replies; a system prompt stays in the context and can be read again by every layer, so this subject was dropped.

## What is here

| Path | Contents |
|---|---|
| `sets/build.json`, `sets/development.json` | The remarks: `remove` (questions) and `keep` (thanks and compliments), with `kind` and, for arithmetic and fact questions, the regular expression of a correct answer. The evaluation set of this case was never used and is not published |
| `replies/` | Every development reply (40 + 40, greedy, 120 tokens): `system_prompt_only` (no edit), `no_system_prompt`, `remove_everywhere.*` (in every scene, reply tokens only or every position), `key_*` (switched by the key) and `control_key_*` (a key built from shuffled scene labels) |
| `labels/` | The blind reader's tone classes (`T` tsundere, `S` shy but plain, `N` plain, `B` repetition or unreadable, `M` does not fit): the instructions as given, the two rounds (batches, labels, key) and `labels.json` |
| `mechanics.json` | The numbers of figure 2 (the switch value g, the removed fraction against the formula, the component after layer 23, for the three forms and the control keys), tau per layer, and the teacher-forcing log probabilities behind the remaining share of section 3 |

The table of section 3 (development set, 40 questions and 40 thanks and compliments), recounted by `part3/recount.py`:

| Condition | Questions: tsundere | shy | plain | broken (B + M) | Thanks and compliments: tsundere | p (questions, against no edit) |
|---|---|---|---|---|---|---|
| `system_prompt_only` | 31 | 0 | 0 | 9 | 35 | — |
| `remove_everywhere.layers11-23.reply_tokens` | 14 | 7 | 1 | 18 | 3 | 0.00022 |
| `key_proportional_removal` | 15 | 3 | 1 | 21 | 33 | 0.00086 |
| `key_removal_above_baseline` | 4 | 4 | 10 | 22 | 34 | 1.5e-08 |
| `key_constant_subtraction` | 26 | 3 | 1 | 10 | 36 | 0.3 |
| `control_key_proportional_removal` | 11 | 4 | 4 | 21 | 2 | 1.1e-05 |

Remaining share of the tone by teacher forcing (1 = with the system prompt, 0 = without): 0.84 with layer 11 only, 0.79 with layers 11 to 23.

## Notes

- The first round's batches also contain 40 replies of part 2's `case4/` mixed in to check the reader against that earlier blind reading (`agreement_check` in `labels/rounds/first/key.json`, with the case4 blind id and its earlier label). 32 of 40 got the same class. They are not counted anywhere in this case.
- A text was read once; the label applies to every identical reply to the same remark. Empty replies count as `B`. `no_system_prompt` was not read.
- The mechanism numbers are copied from the measurement (they need the model to recompute). The keys, directions and neurons of this case are not included.
