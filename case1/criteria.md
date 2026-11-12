# Case 1 (Qwen3.5-4B): the pass criteria fixed in advance, and how each came out

This file restates the pass criteria that were written down before each final test, the changes made to them (and when), and the result for every criterion, including the ones that failed. It is rewritten from the working plans and result notes of the evaluation; those notes themselves are not published. Every number below can be recounted from this folder with `python case1/scripts/fish_numbers.py` (the block "Behind criteria.md", saved as `criteria` in `scripts/numbers.json`). Condition names are the ones used in the file names.

| Final test | Condition tested | Criteria passed | Overall |
|---|---|---|---|
| Set 1 | `fish_first_form` (layers 11, 18, 23, strength 0.9) | 2 of 4 | failed |
| Set 2 | `fish_tuned` (layers 11 to 23, strength 1 / 1 / 0.8) | 4 of 5 | failed (repetition) |
| Set 3 | `fish_threshold_0.5-0.9` (the variant the selection rule picked) | 4 of 5 | failed (strength) |
| Set 3 | `fish_tuned`, run as the comparison | 5 of 5, with one part not measured (see below) | — |

## Rules common to the three tests

- Each evaluation set (100 scene prompts and 130 others) was used for one final test only. It was not used to build the edit, to choose layers or strengths, or to adjust the scoring. Each new set was checked by program to share no prompt with any earlier set or with the contrast set.
- Decoding: greedy, and sampling at temperature 0.7 (top-k 20, top-p 0.95) with the seeds named in the file names. Replies are capped at 120 tokens. The edit is the only difference between conditions; `system_prompt` adds the persona instruction of `sets/contrast.yaml` and no edit.
- "In tone" is class `T` given by a blind reader. "Fell into repetition" is the mechanical count: a reply that is empty, has three tokens or fewer, or has fewer than half of its four-token sequences distinct.
- Tests are exact McNemar tests on paired prompts, two-sided, with Holm correction over the tests named in a criterion. Intervals are Wilson intervals.
- A shuffled key is a key built by the same procedure with the scene labels of the prompts shuffled.

## The check of the scoring, before any evaluation reply was read

**Planned.** Qwen3.5-4B itself, with no edit, was to sort every reply into the five classes. To check it, 188 replies to prompts kept apart from the evaluation sets (20 scene prompts under seven conditions and 16 other prompts under three, greedy) were labelled first by a Claude instance with the condition hidden. The 188 were split at random into two halves. The wording of the scoring prompt could be adjusted on the first half only. Pass: on the second half, used once, precision and recall for "in tone" both 0.8 or higher. If it failed, the model's scoring was to be kept as a secondary count, and the pass criteria were to be decided from blind reading of a fixed, smaller range of replies.

**Result: failed.** On the second half, precision was 0.950 and recall 0.760. The scoring prompt was not changed afterwards.

**Change 1, made at this point, before any evaluation reply had been read.** The replies in the fixed range were read by separate Claude instances, each given only shuffled files with the condition hidden, the written definitions, and examples taken from the first half. The reader was accepted by the same bar: against the labels on all 188 replies, precision 0.981 and recall 0.944 for "in tone" (0.960 and 0.960 on the half not used for examples). The reference labels were themselves made by a Claude instance. No human labelled replies.

The fixed range for set 1 was: scene prompts with greedy decoding under `no_edit`, `system_prompt`, `fish_first_form`, `fish_first_form_shuffled_key` and `direct_add`; scene prompts with sampling (seed 0) under `fish_first_form` and `fish_first_form_shuffled_key`; and the 130 other prompts with greedy decoding under `fish_first_form`. That is 830 replies. With that range, criterion 1 became three tests in place of the eight first planned (against `no_edit` and three shuffled keys, each with greedy decoding and with sampling), and criterion 4 was decided on the 130 greedy replies that were read.

The 188 check replies and their labels are not in this repository. The model's own scores are kept in the reply files of sets 2 and 3 as `model_scores`; they were used for the search and for secondary counts only.

## Set 1: the first form

The layers and the strength were the defaults of gne v0.3.0 and were not tuned.

| Criterion, as fixed before the test | Result | Verdict |
|---|---|---|
| 1. Effect. More replies in tone than with no edit and than with a shuffled key, every test significant after Holm correction (p < 0.05) | Against `no_edit`, greedy: 27 prompts in tone only with the edit, 0 only without, corrected p = 4e-8. Against the shuffled key, greedy: 23 against 13, corrected p = 0.13. Against the shuffled key, sampled: 27 against 8, corrected p = 0.004 | **Failed** (the greedy comparison with the shuffled key is not significant) |
| 2. Repetition. In the scene, 5% or less fell into repetition, with greedy decoding and over the sampled runs together. In the other scenes, no more than 2 points above `no_edit` | Scene: 10 of 100 with greedy decoding, 12 of 300 over the three sampled runs. Other scenes: 0 of 130 with greedy decoding and 0 of 390 sampled, against 0 and 0 with no edit | **Failed** (greedy) |
| 3. Correct answers. On the 50 arithmetic and fact questions, a drop of no more than 2 points from `no_edit`, and not a significant drop | Greedy: 46 with no edit, 46 with the edit. Sampled, 150 replies: 139 and 139 | Passed |
| 4. Other scenes keep their tone. In each of the three other scenes, 5% or less of the replies in tone | 0 of the 130 greedy replies read blind | Passed |
| Level 1: all of 1 to 4 | | **Failed** |
| Level 2: level 1, and at least half as many replies in tone as with the system prompt (greedy) | 27 against 86: 0.31 | **Failed** |

## Set 2: the tuned form

**How the form was chosen.** Candidates were compared on prompts used only for searching (`sets/search_a.json`), by adding the vectors directly to the layer outputs, with the model's own scoring. In the search, "repeating" is a looser count than the mechanical one (it also counts any six characters that occur four times or more). The rules were fixed before the search: for the layers, among the candidates with 10% or less repeating, take the one with the most replies in tone and not repeating, and prefer fewer layers when two are within 5 points; for the strength, the same with a limit of 5%. Candidates added during the search, and the reason for each, were written down before they were run. The rules gave layers 11 to 23 and strength 1 / 1 / 0.8. Every candidate and its counts are in `search/README.md`.

Set 1 was not used again. The five criteria below were fixed before the search, for the tuned form.

| Criterion, as fixed before the test | Result | Verdict |
|---|---|---|
| 1. Effect. More replies in tone than with no edit and than with a shuffled key, every test significant after Holm correction (p < 0.05) | Against `no_edit`, greedy: 53 against 0. Against `fish_tuned_shuffled_key`: 51 against 1 with greedy decoding, 54 against 0 sampled. The largest corrected p is 2e-14 | Passed |
| 2. Repetition. In the scene, 5% or less, with greedy decoding and with sampling. In the other scenes, no more than 2 points above `no_edit` | Scene: 8 of 100 with greedy decoding, 1 of 100 sampled. Other scenes: 0 and 0 of 130, against 0 and 1 with no edit | **Failed** (greedy: 8% against a limit of 5%) |
| 3. Correct answers. A drop of no more than 2 points on the 50 arithmetic and fact questions, and not a significant drop | Greedy: 46 with no edit, 47 with the edit. Sampled: 47 and 49 | Passed |
| 4. Other scenes keep their tone. 5% or less in tone in each of the three other scenes | 0 of the 130 greedy replies read blind. By the model's own scoring, 1 of 130 sampled replies | Passed |
| 5. Strength. At least half as many replies in tone as with the system prompt (greedy) | 53 against 78: 0.68 | Passed |
| All five | | **Failed**, on repetition only |

The plan named four tests for criterion 1. The sampled replies with no edit were not in the range that was read, so three were run.

## Set 3: a variant chosen to bring repetition down, with the tuned form as the comparison

**How the variant was chosen.** The aim was 5% or less repetition with greedy decoding. Candidates were compared on a second set of search prompts (`sets/search_b.json`), again with the model's own scoring. The rule, fixed before the search: a candidate qualifies if 5 or fewer of 100 greedy replies and 10 or fewer of 200 greedy and sampled replies are repeating; among those, take the one with the most replies in tone and not repeating. Before the final test, the chosen candidate's replies to the search prompts were also to be read blind, and it was to be replaced by the runner-up if more than 5% of its greedy replies had fallen into repetition. Twenty-four variations were tried. Among the edits written into neurons, only one qualified: the tuned form with the thresholds of its switches raised from 0.4 and 0.8 to 0.5 and 0.9 (`fish_threshold_0.5-0.9`). It passed the reading check and went to the final test. The tuned form was run next to it as the comparison.

The generation for the final test was started before the result of that reading check was in; the replies were not looked at until it was.

The five criteria were fixed for the selected variant. The right-hand column gives the same counts for the tuned form.

| Criterion, as fixed before the test | `fish_threshold_0.5-0.9` (selected) | `fish_tuned` (comparison) |
|---|---|---|
| 1. Effect. More replies in tone than with no edit and than with a shuffled key, every test significant after Holm correction | **Passed.** Against `no_edit`: 34 against 0. Against its shuffled key: 34 against 5 with greedy decoding, 51 against 4 sampled. The largest corrected p is 2e-6 | Against `no_edit`: 53 against 0. No shuffled key was run for the tuned form on this set, so that part was not measured here (on set 2 it passed) |
| 2. Repetition. In the scene, 5% or less, with greedy decoding and for each sampled seed. In the other scenes, no more than 2 points above `no_edit` | **Passed.** Scene: 5, 4 and 3 of 100. Other scenes: 0, 0 and 0 of 130 | Met. Scene: 1, 3 and 2 of 100. Other scenes: 0, 0 and 0 of 130 |
| 3. Correct answers. A drop of no more than 2 points on the 50 arithmetic and fact questions, and not a significant drop | **Passed.** 46, 47 and 45, against 46, 46 and 46 with no edit | Met. 46, 47 and 45, against the same 46, 46 and 46 |
| 4. Other scenes keep their tone. 5% or less in tone in each of the three other scenes | **Passed.** 0 of the 130 greedy replies read blind | Met by the model's own scoring only: 1 of 390 replies over the three runs. These replies were not read |
| 5. Strength. At least half as many replies in tone as with the system prompt (greedy) | **Failed.** 34 against 87: 0.39 | Met. 53 against 87: 0.61 |
| All five | **Failed**, on strength | All five met on this set, as far as they were measured |

The variant did not reduce repetition either: 5 of 100 with greedy decoding against 1 for the tuned form, which had 8 on set 2 and 7 on the search prompts. Over those three sets the tuned form fell into repetition in 16 of 300 greedy replies.
