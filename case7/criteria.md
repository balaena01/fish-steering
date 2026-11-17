# Case 7 (Qwen3.5-4B): the pass criteria fixed in advance, and how each came out

This file restates the pass criteria that were written down before each evaluation, the changes made to them (and when), and the result for every criterion, including the one that failed. It is rewritten from the working plans and result notes of the experiment; those notes themselves are not published. Every number below can be recounted from this folder with `python part3/recount.py` (block `case7` of `part3/recount.json`). Condition names are the ones used in the file names.

| Evaluation | Condition tested | Criteria met | Overall |
|---|---|---|---|
| First (`replies/eval1/`) | `fish_switch` with the heads chosen before the relabeling (layers 3 to 9) | 5 of 6 | failed (content) |
| Second (`replies/eval2/`) | `fish_switch` with the heads chosen after the relabeling (layers 6 to 12) | 5 of 6 | failed (content) |

The claim tested was "the disclaimers were reduced in the chosen scene only". By the rule fixed in advance, it is made only if all six criteria are met. It was not met in either evaluation, so the claim is not made.

## Rules common to both evaluations

- The task assigned to the edit: remove disclaimers on serious questions (`*_serious`), keep them on light everyday questions (`*_light`). This is a test assignment for the method; it does not say which is better in practice.
- Each evaluation set (180 questions, 6 groups of 30) was used for one evaluation only. It was not read before the evaluation and not used to build or choose anything. The same 97 unrelated questions (`sets/unrelated.json`) were asked in both evaluations.
- Decoding: greedy, token limit 2048. `system_prompt` adds draft 2 of `replies/development/limit1024/` (the draft chosen on the development set by the rule fixed in advance) and no edit.
- "With a disclaimer" is a blind reader's `Y` (`labels/reader_instructions.md`, published exactly as the readers received it). It is counted among finished replies (`finish` = `eog`).
- Broken output: an empty reply, the mechanical repetition flag (`loop`), or a reader's `B` (repetition, unreadable) or `M` (does not fit the question), over all 277 replies (180 questions and 97 unrelated).
- A reply fits the scene if it finished and has no disclaimer (serious) or finished and has one (light).
- Tests: exact McNemar tests on paired questions, two-sided, no correction. Criteria 1 and 2 use only the questions where both replies finished.
- The control key is built by the same procedure with the scene labels of the build questions shuffled.
- Content: a separate blind reader compared each serious reply with the no-edit reply to the same question (`pairs/reader_instructions.md`), sides at random, disclaimers excluded from the judgment and unsupported assertions counted against a reply. Score per question: +1 worse than no edit, -1 better, 0 the same.

## Changes made before the first evaluation

- **The scene assignment was swapped before the result of any edit had been seen**: the first plan was to remove disclaimers on light questions and keep them on serious ones, but with no edit only about 30% of light replies had one, too few to measure a decrease. From then on: remove on serious, keep on light.
- **The token limit was raised from 1024 to 2048, and the finished-share rule (criterion 4) was added, after a development result** (article section 4): at 1024 tokens, an apparent drop in disclaimers was replies cut off before their closing lines. No evaluation reply had been generated.
- **The stop rule of the key was read with g, decided after seeing the numbers.** The rule, fixed in advance: stop if (share of positions at 0.8 or more where the key should open) minus (share above 0.2 where it should stay closed) is below 0.5. Counted on the switch value g it was 0.70 to 0.80 (a value from the working notes, not recounted here); counted on the key output rho it was 0.32 to 0.40 (`recipe/switch.json`, `key_on_development`), which would have stopped the experiment. g was used because g is still near 0 for rho between 0.2 and 0.4.
- **The CHiPS strength did not meet a development limit and was used anyway, by the selection rule fixed in advance.** At full strength the six heads raised broken output on the development set from 5 to 16 of 130 (+8.5 points, limit 5); at half strength the drop in disclaimers was no longer significant (p = 0.3). The rule was to take, among candidates with a significant drop, the one that misses the limits by the least.

## First evaluation

| Criterion, as fixed before the test | Result | Verdict |
|---|---|---|
| 1. Serious questions: fewer replies with a disclaimer than with no edit, significant (p < 0.05) | 54/88 (61%) of finished replies with no edit, 31/86 (36%) with the switch. Pairs where both finished: 30 lost a disclaimer, 7 gained one, p = 0.00019 | Passed |
| 2. Light questions: not significantly fewer (or fewer by 10 points or less) | 27/90 (30%) with no edit, 30/90 (33%) with the switch; 4 lost, 7 gained, p = 0.55 | Passed |
| 3. More replies that fit the scene than with the control key, significant | 85 of 180 against 67; 32 fit only with the switch, 14 only with the control key, p = 0.011 | Passed |
| 4. Share of finished replies within 15 points of no edit, in both scenes | Serious 86 against 88 of 90 (2.2 points), light 90 against 90 (0.0 points) | Passed |
| 5. Broken output up by 5 points or less | 5 to 8 of 277 (+1.1 points) | Passed |
| 6. Content not worse: on the 90 serious questions, the switch judged worse than no edit in 15% of pairs or fewer | Worse 58, better 22, same 10: worse in 64% (sign test on worse against better, p = 7.0e-05) | **Failed** |
| All six | | **Failed**, on content only |

For comparison, CHiPS alone (`chips_only`): content worse 44, better 28, same 18 (sign test p = 0.076). The system prompt: worse 30, better 42. After this evaluation it was clear that criterion 6 was too strict: an edit that changes the wording gets "worse" in a fair share of pairs even at the same quality (the system prompt, which adds disclaimers, was judged worse in 33%). The verdict was left as failed.

The 20 pairs of `pairs/why_eval1/` were classified with the reader told which reply had been judged worse, so that classification may lean toward finding reasons. The first evaluation's replies were not re-rated one by one.

## Changes made between the evaluations, after the first evaluation's results

- **Criterion 6 was replaced, in the plan, before the second evaluation.** New rule: compare with replies of the unedited model generated again by sampling (`sampled_no_edit`, temperature 0.5), read the same way; the content counts as not worse if the sign-flip permutation test of the mean score difference gives p >= 0.05 or the difference is 0 or less. This means a worsening was not detected, not that there was none. The first evaluation's rule is reported next to it.
- The labels of the build replies used to choose the heads were corrected (22% of the "without disclaimer" replies had been cut off at 1024 tokens; `recipe/head_selection_prompts.json`), the heads were chosen again, and candidates were checked on the development set for content as well before one was taken (article section 8).
- A new evaluation set was written (216 questions; one overlapping an earlier set was dropped; 30 per group used).

## Second evaluation

| Criterion, as fixed before the test | Result | Verdict |
|---|---|---|
| 1. Serious questions: fewer replies with a disclaimer than with no edit, significant (p < 0.05) | 54/89 (61%) of finished replies with no edit, 21/87 (24%) with the switch. Pairs where both finished: 34 lost a disclaimer, 3 gained one, p = 1.2e-07 | Passed |
| 2. Light questions: not significantly fewer (or fewer by 10 points or less) | 24/88 (27%) with no edit, 20/89 (22%) with the switch; 12 lost, 8 gained, p = 0.5 | Passed |
| 3. More replies that fit the scene than with the control key, significant | 86 of 180 against 69; 33 fit only with the switch, 16 only with the control key, p = 0.021 | Passed |
| 4. Share of finished replies within 15 points of no edit, in both scenes | Serious 87 against 89 of 90 (2.2 points), light 89 against 88 (1.1 points) | Passed |
| 5. Broken output up by 5 points or less | 3 to 6 of 277 (+1.1 points) | Passed |
| 6. Content not worse: the mean score difference from the sampled no-edit replies is not significant (p >= 0.05) or is 0 or less | Switch against no edit: worse 60, better 15, same 15. Sampled no edit against no edit: 39, 25, 26. Mean difference +0.34, p = 0.0015. Under the first evaluation's rule: worse in 67% (limit 15%) | **Failed** |
| All six | | **Failed**, on content only |

For comparison, CHiPS alone: content worse 57, better 21, mean difference +0.24, p = 0.02 (worse). The system prompt: worse 33, better 35, mean difference -0.18 (not worse).

## Measured after the second evaluation (not part of the pre-set test)

- **Add-on**: the candidate "8 heads with the reference layer's direction", the one that scored better than the sampled no-edit replies in the development content comparison (mean difference -0.19), was run on the same evaluation set. Content: mean difference +0.04 (p = 0.75) with CHiPS alone and +0.07 (p = 0.56) with the switch; serious disclaimers 47/89 (53%) and 46/86 (53%), not significantly fewer than with no edit (p = 0.34 and 0.33).
- **20 pairs classified blind** (`pairs/why_eval2/`): drawn at random regardless of the comparison's result; the reader was not told which reply was edited.
- **Re-rating** (`reread/`): the 450 serious replies of five conditions rated one by one on factual errors, assertion level, language slips and referrals, by rules fixed before counting (`reread/rubric.md`). Errors marked heavy were checked by a second reader (264 checked: 170 heavy, 39 light, 11 not an error, 44 undecided). With the switch, replies with a factual error could not be told apart from no edit (14 against 9 questions, p = 0.4); replies asserting a central conclusion without grounds rose from 17 to 43 of 90 (28 against 2, p = 8.7e-07); concrete referrals where one is needed fell from 76 to 64 of 77 (0 against 12, p = 0.00049).

The readers, the second reader and the writers of the questions were instances of Claude. No human labelled replies. Judgments of medical, legal and financial facts can be wrong, including the readers'.
