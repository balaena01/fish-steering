# Case 3 (second persona on the 27B model): the pass criteria fixed in advance, and how each came out

This file restates the pass criteria that were written down before the test of the second persona (a cheerful, casual tone in replies to worries and requests for advice), the changes made (and when), and the result for every criterion, including the one that failed. It is rewritten from the working plan and result notes of the evaluation; those notes themselves are not published. Every number below can be recounted from this folder with `python case3/scripts/fish_numbers.py`. Condition names are the ones used in the file names.

**Five of the six criteria passed. The one that failed was strength, so the test as a whole failed.**

## When the plan was written

Before anything was run for this persona, and after the results of case 2 were known. The comparison with the shuffled key (criterion 2) was defined anew at that point; the reason is given below.

## Rules

- Nothing was tuned for this persona. The layers, the strengths and the form were taken unchanged from case 2 (every other layer from 22 to 46, strength 1.2 / 1.2 / 0.96, the capped pair). The instruction text is the one in gne's `always_persona` template.
- All prompts were new, written for this test, and split at random into the contrast set, the prompts for checking the reader, and the evaluation set (100 scene prompts and 80 others), which was used once.
- Conditions: `no_edit`, `system_prompt`, `fish`, `fish_shuffled_key`. Decoding: greedy for everything; sampling (temperature 0.7, seed 0) for `fish` and `fish_shuffled_key` on the scene prompts. Replies are capped at 120 tokens.
- Read blind: the scene prompts with greedy decoding under all four conditions, the sampled replies, and the 80 other prompts under `fish`. 680 replies.
- Classes: `E` cheerful and casual, `C` somewhat casual, `N` plain, `B` repetition or unreadable, `M` does not fit the prompt. The criteria use `E` only.
- Tests are exact McNemar tests on paired prompts, two-sided.

## The check of the reader, before the final replies were read

**Planned.** 108 replies to prompts kept apart from the evaluation set (20 scene prompts and 16 others under `no_edit`, `system_prompt` and `fish`, greedy) are labelled twice, independently, with the condition hidden: once by the Claude instance running the evaluation (judging from the first 75 characters of each reply) and once by a reader given only the instructions. The reader is accepted if precision and recall for `E` against the first labels are both 0.8 or higher. If not, the instructions are revised once and checked again.

**Result: passed.** 108 of 108 labels agreed. Only 7 of them were `C`, so the boundary of "somewhat casual" was hardly tested by this check. The replies and both sets of labels are in `reader_check/`.

The generation for the final test was started before the result of this check was in; the replies were not looked at until it was.

## The six criteria and the results

| Criterion, as fixed before the test | Result | Verdict |
|---|---|---|
| 1. Effect. In the scene, more replies in class `E` than with no edit, significant (greedy, p < 0.05) | 36 against 0 of 100 (p = 3e-11) | Passed |
| 2. The shuffled key, defined anew. Both of: (a) of the 80 replies to other prompts (greedy), significantly more begin with the same 30 characters as the unedited model's with the real key than with the shuffled key; (b) in the scene (greedy), the real key gives no more replies in classes `B` and `M` than the shuffled key | (a) 61 against 37 of 80; 29 prompts only with the real key, 5 only with the shuffled key, p = 0.00004. (b) 6 against 16 of 100 (sampled: 4 against 24) | Passed |
| 3. Repetition (mechanical count). In the scene, 5% or less, with greedy decoding and with sampling. In the other scenes, no more than 2 points above `no_edit` | Scene: 0 and 0 of 100. Other scenes: 0 of 80, against 0 | Passed |
| 4. Correct answers. On the 40 questions with an answer (30 arithmetic and fact questions, 10 fact questions in English), at most one fewer than with no edit, and not a significant drop | 36 with no edit, 37 with the edit | Passed |
| 5. Other scenes keep their tone. 5% or less in class `E` in each of the three other scenes (greedy) | 0 of 80 read blind; all 80 were plain | Passed |
| 6. Strength. At least half as many replies in class `E` as with the system prompt (greedy) | 36 against 97: 0.37 | **Failed** |
| All six | | **Failed** (5 of 6) |

## Why criterion 2 was changed, and what the old form would have shown

In cases 1 and 2 the criterion was "more replies in tone than with a shuffled key". Case 2 failed it: on the 27B model a shuffled key gave more replies in tone than the real key, and what set the two apart was how many replies went wrong and how many replies to other prompts were left as they were. Before this test was run, the comparison was therefore fixed as (a) and (b) above, and the count of replies in tone was kept as a reference only. Criterion 4 was also written as "at most one fewer" because, with 40 questions, 2 points is less than one question.

The reference count came out in the same direction as in case 2: the shuffled key gave 49 replies in class `E` against 36 for the real key with greedy decoding (p = 0.08), and 45 against 39 sampled (p = 0.41). Under the old form of the criterion this test would have failed it too.
