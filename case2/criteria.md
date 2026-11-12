# Case 2 (Swift-1.5-Qwen3.8-27B, IQ2_XS): the pass criteria fixed in advance, and how each came out

This file restates the pass criteria that were written down before the final test on the 27B model, the changes made to the plan (and when), and the result for every criterion, including the ones that failed. It is rewritten from the working plan and result notes of the evaluation; those notes themselves are not published. Every number below can be recounted from this folder with `python case2/scripts/fish_numbers.py`. Condition names are the ones used in the file names.

**Three of the five criteria passed, so the test as a whole failed.**

## When the plan was written

After a small check that the edit works on this model (three layers, ten prompts, and the formula check), and before the layer comparison and the final test. The persona, the contrast set, the readers' instructions and the five criteria are those of case 1.

## Rules

- The evaluation set (100 scene prompts and 80 others) was new, was checked by program to share no prompt with any earlier set, and was used once.
- Conditions: `no_edit`, `system_prompt`, `fish`, `fish_shuffled_key`. Decoding: greedy for everything; sampling (temperature 0.7, seed 0) for `fish` and `fish_shuffled_key` on the scene prompts. Replies are capped at 120 tokens.
- Read blind, by the same kind of reader and with the same instructions as in case 1: the scene prompts with greedy decoding under all four conditions, the sampled replies, and the 80 other prompts under `fish`. 680 replies.
- "In tone" is class `T` given by a blind reader. "Fell into repetition" is the mechanical count: empty, three tokens or fewer, or fewer than half of the four-token sequences distinct.
- Tests are exact McNemar tests on paired prompts, two-sided.

## How the layers and the strength were chosen

Six sets of layers and the selection rule were fixed before any of them was run. The candidates were compared by adding the vectors directly to the layer outputs, on 40 search prompts (`sets/search.json`), with greedy decoding and the 27B model's own scoring, which was not checked against a reader on this model. Rule: among the candidates with 4 or fewer of 40 replies repeating (the looser count that also catches any six characters occurring four times or more), take the one with the most replies in tone and not repeating; when two are within 2 replies, take the one with fewer layers. The strength was chosen by the same rule among three values.

| Candidate (`search/direct_add.<name>.greedy.json`) | Layers | Strength | In tone and not repeating, of 40 | Repeating |
|---|---|---|---|---|
| `F` | 3: 22, 34, 46 | 1 / 1 / 0.8 | 26 | 2 |
| `N` | 13: every other layer from 22 to 46 | 1 / 1 / 0.8 | 35 | 2 |
| `P` | 25: 22 to 46 | 1 / 1 / 0.8 | 35 | 3 |
| `E` | 25: 16 to 40 | 1 / 1 / 0.8 | 36 | 1 |
| `L` | 25: 28 to 52 | 1 / 1 / 0.8 | 37 | 2 |
| `W` | 45: 12 to 56 | 1 / 1 / 0.8 | 37 | 2 |
| `N08` | as `N` | 0.8 / 0.8 / 0.64 | 24 | 0 |
| `N12` | as `N` | 1.2 / 1.2 / 0.96 | 38 | 1 |

The rule gave the 13 layers of `N` (within 2 of the best, with the fewest layers) and then strength 1.2 / 1.2 / 0.96.

## Changes to the plan, each made before the final test

- The layer comparison took about four GPU hours against an estimate of 70 minutes. To fit the remaining time, the strength comparison was run with greedy decoding only (the plan had sampling as well for the top two), the edit was built from the direction already made for `N`, sampling in the final test was limited to `fish` and `fish_shuffled_key` on the scene prompts, and the second persona was put off (it was run later; see `case3/`).
- The formula check flagged one of the 13 layers (7.4% against a threshold of 5%). The edit was used as it was.
- On the search prompts the edit itself gave fewer than 5 repeating replies of 40, so, as the plan said for that case, no weaker version was built.

## The five criteria and the results

| Criterion, as fixed before the test | Result | Verdict |
|---|---|---|
| 1. Effect. More replies in tone than with no edit and than with a shuffled key: three tests (against `no_edit` greedy, against `fish_shuffled_key` greedy and sampled), all significant after Holm correction (p < 0.05) | Against `no_edit`: 55 prompts in tone only with the edit, 0 only without (p = 6e-17). Against the shuffled key, greedy: 14 prompts in tone only with the real key, 29 only with the shuffled key (p = 0.03 before correction): the shuffled key gave more, 70 against 55 of 100. Sampled: 19 against 26 (p = 0.37) | **Failed** |
| 2. Repetition. In the scene, 5% or less, with greedy decoding and with sampling. In the other scenes, no more than 2 points above `no_edit` | Scene: 3 of 100 with greedy decoding, 1 of 100 sampled. Other scenes: 0 of 80, against 0 with no edit | Passed |
| 3. Correct answers. A drop of no more than 2 points on the arithmetic and fact questions, and not a significant drop | 29 of 30 with no edit, 28 with the edit. One question of 30 is 3.3 points. The drop is not significant (p = 1.00) | **Failed on paper** |
| 4. Other scenes keep their tone. 5% or less in tone in each of the three other scenes | 0 of 80 read blind; all 80 were plain | Passed |
| 5. Strength. At least half as many replies in tone as with the system prompt (greedy) | 55 against 93: 0.59 | Passed |
| All five | | **Failed** (3 of 5) |

## Notes on the two failures

**Criterion 3.** The one question that differed was "What is the deepest lake in Japan?". Reading the two replies, both models answered wrongly; the reply without the edit was counted correct because the right name appears further down in its list. The count by the answer patterns (29 and 28) and the failed criterion are reported as they stand. With 30 questions, a 2-point criterion cannot be met by any drop at all.

**Criterion 1.** The criterion assumed that a shuffled key would give fewer replies in tone, as it did on the 4B model. On this model it gave more. What the shuffled key lost was precision: in the scene, 30 of 100 greedy replies were repetition, unreadable or did not fit the prompt, against 10 with the real key; and of the 80 replies to other prompts, 29 began with the same 30 characters as the unedited model's, against 70 with the real key. These two counts were made after the result was known. They were not criteria of this test. They were written into the criteria of the next test (`case3/criteria.md`) before that test was run.
