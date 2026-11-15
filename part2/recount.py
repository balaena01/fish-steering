"""Recount the main numbers of part 2 of the FiSH article from the files in this repository.

    python part2/recount.py        prints the numbers and writes part2/recount.json next to this script

No GPU and no model are needed, only Python 3 with its standard library. The script finds the files from its own location
(the repository root is the folder above this one), so it can be run from any directory.

What is recounted:
  case4/  the new keys on Qwen3.5-4B: replies in tone (readers' labels), prompts where 0.2 or more was written (gne nw check),
          replies that start like the unedited model's, correct answers (the questions are case1/sets/set3.json)
  case5/  sorting remarks: accuracy in the first comparison and on the new remarks (empty replies count as wrong, and as before),
          paired tests, replies that start like the unedited model's, breakage after a marker; silence with the end-of-reply token
  case6/  answering only when called by name
"""
import json
import re
from math import comb, sqrt
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
jl = lambda p: json.loads((ROOT / p).read_text(encoding="utf-8"))
KINDS = ["fact", "howto", "consult", "thanks", "praise", "report", "invite", "greet", "request", "partial"]
ROUTE = jl("case5/sets/routes.json")["routes"]


def mcnemar(a, b):
    """Remarks only a got right, only b got right, and the exact two-sided binomial p."""
    x = sum(p and not q for p, q in zip(a, b)); y = sum(q and not p for p, q in zip(a, b)); n = x + y
    return [x, y, 1.0 if n == 0 else min(1.0, 2 * sum(comb(n, k) for k in range(min(x, y) + 1)) / 2 ** n)]


def wilson(k, n, z=1.96):
    p = k / n; d = 1 + z * z / n; c = p + z * z / (2 * n); h = z * sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return [round(100 * (c - h) / d, 1), round(100 * (c + h) / d, 1)]


def marker(text, empty_is_wrong=True):
    """■ = no response, ◇ = acknowledge, anything else = answer. An empty reply is wrong ("empty"), or an answer under the earlier rule."""
    t = (text or "").strip()
    if not t:
        return "empty" if empty_is_wrong else "reply"
    return "none" if t.startswith("■") else ("ack" if t.startswith("◇") else "reply")


def silence_label(text):
    """The end-of-reply form: empty = no response, ◇ = acknowledge, anything else = answer."""
    t = (text or "").strip()
    return "none" if not t else ("ack" if t.startswith("◇") else "reply")


same30 = lambda a, b: (a or "").strip()[:30] == (b or "").strip()[:30]
broken_after = lambda t: any(s in (t or "").strip()[1:] for s in "■◇")
OUT = {}

# ---- case4: the new keys (Qwen3.5-4B, tsundere) -------------------------------------------------------------------
L = jl("case4/labels/labels.json")
REM = ("report", "greet", "request", "partial")
c4 = {}
for c in ("published_keys", "new_keys"):
    c4[c] = {"remarks_in_tone": sum(L[f"remarks|{c}|greedy|{g}"].count("T") for g in REM),
             "thanks_in_tone_greedy": L[f"set3|{c}|greedy|target"].count("T"), "thanks_in_tone_sampled": L[f"set3|{c}|sampled_seed0|target"].count("T")}
    amt = jl(f"case4/recipe/amounts_eval.{c}.json")["groups"]
    c4[c]["remarks_written_0.2"] = sum(any(abs(s["total"]) >= 0.2 for s in q["segments"].values()) for g in REM for q in amt[f"dont_touch:{g}"]["questions"])
    R = jl(f"case4/replies/remarks/{c}.greedy.json")["groups"]; B = jl("case4/replies/remarks/no_edit.greedy.json")["groups"]
    c4[c]["remarks_same_start"] = sum(a["text"][:30] == b["text"][:30] for g in REM for a, b in zip(R[g], B[g]))
S3 = jl("case1/sets/set3.json")["groups"]
for c in ("no_edit", "published_keys", "new_keys"):
    R = jl(f"case4/replies/set3/{c}.greedy.json")["groups"]
    c4.setdefault(c, {})["correct_of_65"] = sum(bool(re.search(q["answer"], x["text"] or "")) for g in ("facts", "english") for q, x in zip(S3[g], R[g]) if "answer" in q)
OUT["case4"] = c4

# ---- case5: sorting remarks ---------------------------------------------------------------------------------------
c5 = {}
for m in ("4b", "27b"):
    F = {c: jl(f"case5/replies_first/{m}/{c}.json")["groups"] for c in ("no_edit", "instruction_original", "fish")}
    okF = {c: [int(marker(x["text"]) == ROUTE[k]) for k in KINDS for x in F[c][k]] for c in F}
    G = {c: jl(f"case5/replies_new/{m}/{c}.json")["groups"] for c in ("no_edit", "instruction_original", "instruction_chosen", "fish")}
    r = {"first_comparison": {c: sum(v) for c, v in okF.items()}, "first_fish_vs_instruction": mcnemar(okF["fish"], okF["instruction_original"])}
    for rule, empty_is_wrong in (("empty_is_wrong", True), ("empty_is_answer", False)):
        ok = {c: [int(marker(x["text"], empty_is_wrong) == ROUTE[k]) for k in KINDS for x in G[c][k]] for c in G}
        r[rule] = {c: [sum(v), wilson(sum(v), 400)] for c, v in ok.items()}
        r[rule]["chosen_vs_fish"] = mcnemar(ok["instruction_chosen"], ok["fish"])
        r[rule]["chosen_vs_original"] = mcnemar(ok["instruction_chosen"], ok["instruction_original"])
    RK = [k for k in KINDS if ROUTE[k] == "reply"]
    for c in ("fish", "instruction_chosen"):
        rows = [x for k in KINDS for x in G[c][k] if marker(x["text"]) in ("none", "ack")]
        r[c] = {"answers_same_start_of_200": sum(same30(a["text"], b["text"]) for k in RK for a, b in zip(G[c][k], G["no_edit"][k])),
                "marker_replies": len(rows), "marker_again_or_loop": sum(int(bool(x["loop"]) or broken_after(x["text"])) for x in rows)}
    # silence with the end-of-reply token (the same 400 remarks, rows of [kind, remark])
    A = jl(f"case5/replies_silence/{m}/fish_end_of_reply.json")["rows"]
    okA = [int(silence_label(x["text"]) == ROUTE[x["key"][0]]) for x in A]
    okP = [int(marker(x["text"]) == ROUTE[k]) for k in KINDS for x in G["fish"][k]]
    assert [x["key"][1] for x in A] == [x["q"] for k in KINDS for x in G["fish"][k]]
    prev_none = [x for k in KINDS for x in G["fish"][k] if marker(x["text"]) == "none"]
    r["silence"] = {"correct": sum(okA), "ci": wilson(sum(okA), 400), "marker_form_vs_end_form": mcnemar(okP, okA),
                    "wrongly_silent_of_360": sum(int(not (x["text"] or "").strip()) for x in A if x["key"][0] != "partial"),
                    "marker_form_no_response_broke": [sum(int(bool(x["loop"]) or broken_after(x["text"])) for x in prev_none), len(prev_none)],
                    "end_form_empty_replies": sum(int(not (x["text"] or "").strip()) for x in A if x["key"][0] == "partial")}
    c5[m] = r
OUT["case5"] = c5

# ---- case6: answering only when called by name --------------------------------------------------------------------
T = jl("case6/sets/answer_types.json")
answer = set(T["answer"])
c6 = {}
for c in ("no_edit", "instruction_chosen", "fish_called_by_name"):
    rows = jl(f"case6/replies/{c}.json")["rows"]
    ok = [int(bool((x["text"] or "").strip()) == (x["key"][0] in answer)) for x in rows]
    c6[c] = {"correct": sum(ok), "of": len(ok), "called_but_silent": sum(int(not (x["text"] or "").strip()) for x in rows if x["key"][0] in answer),
             "silent_where_it_should": sum(int(not (x["text"] or "").strip()) for x in rows if x["key"][0] not in answer)}
    c6[c]["_ok"] = ok
c6["fish_vs_instruction"] = mcnemar(c6["fish_called_by_name"]["_ok"], c6["instruction_chosen"]["_ok"])
for c in ("no_edit", "instruction_chosen", "fish_called_by_name"):
    del c6[c]["_ok"]
OUT["case6"] = c6

(HERE / "recount.json").write_text(json.dumps(OUT, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps(OUT, ensure_ascii=False, indent=1))
