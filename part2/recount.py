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
  case9/  (added 2026-11-18) routing in second turns, third turns or later and under role system prompts: where the original keys break
          (development set: accuracy, key outputs, the vector added directly), and the evaluation of the rebuilt keys against the original keys,
          the system prompt and a linear probe (accuracy per conversation shape, paired tests, wrongly empty replies)
  case10/ (added 2026-11-18) the output after the acknowledgment marker: the three conditions that separate the causes, the evaluation of the
          switch that ends an acknowledgment after one sentence (degraded replies, accuracy, length, the three side effects), the blind
          evaluators' sorting, and the 40 English inputs
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

# ---- case9 and case10 (added 2026-11-18) ---------------------------------------------------------------------------
ACK_K = ["thanks", "praise", "report", "greet"]
REPLY_K = ["fact", "howto", "consult", "invite", "request"]


def route3(text, empty_is_wrong=False):
    """Empty = no reply (or wrong, for the form with "■"), ◇ = acknowledgment, ■ = no reply, anything else = answer."""
    t = (text or "").strip()
    if not t:
        return "empty" if empty_is_wrong else "none"
    return "ack" if t.startswith("◇") else ("none" if t.startswith("■") else "reply")


def strip_mk(text):
    t = (text or "").strip()
    while t[:1] in ("◇", "■"):
        t = t[1:].lstrip()
    return t


def n_sentences(text):
    return len([x for x in re.split(r"[。！？!?…]+|\n+", strip_mk(text)) if x.strip()])


degraded = lambda x: bool(((x["text"] or "").strip() and "◇" in (x["text"] or "").strip()[1:]) or x["loop"])


def median(v):
    v = sorted(v); n = len(v)
    return None if n == 0 else (v[n // 2] if n % 2 else (v[n // 2 - 1] + v[n // 2]) / 2)


def mc_counts(x, y):
    n = x + y
    return [x, y, 1.0 if n == 0 else min(1.0, 2 * sum(comb(n, k) for k in range(min(x, y) + 1)) / 2 ** n)]


c9 = {}
dev = jl("case9/replies/development/original_keys.json")["rows"]
kout = {x["id"]: x for x in jl("case9/replies/development/original_keys.key_outputs.json")["rows"]}
forced = {(x["id"], x["vector"]): x for x in jl("case9/replies/development/vector_added_directly.json")["rows"]}
d9 = {}
for sh in ("first_turn", "second_turn", "third_turn_or_later", "system_prompt_seen_role", "system_prompt_unseen_role"):
    rows = [x for x in dev if x["shape"] == sh]
    ok = [route3(x["text"]) == ROUTE[x["kind"]] for x in rows]
    rho = sorted(kout[x["id"]]["end_of_turn_key_output"] for x in rows if x["kind"] == "partial")
    fail = [kout[x["id"]]["end_of_turn_key_output"] for x, o in zip(rows, ok) if x["kind"] == "partial" and not o]
    fe = [forced[(x["id"], "end_of_turn")] for x in rows if x["kind"] == "partial"]
    d9[sh] = {"correct": sum(ok), "of": len(rows), "no_reply_correct": [sum(o for x, o in zip(rows, ok) if x["kind"] == "partial"), sum(1 for x in rows if x["kind"] == "partial")],
              "end_of_turn_key_output_median": round(median(rho), 3), "failed_no_reply": len(fail), "failed_with_key_output_below_0.8": sum(r < 0.8 for r in fail),
              "vector_added_directly_empty": [sum(1 for z in fe if not (z["text"] or "").strip()), len(fe)]}
c9["development_original_keys"] = d9
E9 = {c: jl(f"case9/replies/eval/{c}.json")["rows"] for c in ("original_keys", "rebuilt_keys", "system_prompt", "no_edit")}
ids9 = [x["id"] for x in E9["original_keys"]]
assert all([x["id"] for x in v] == ids9 for v in E9.values())
OK9 = {c: [int(route3(x["text"]) == ROUTE[x["kind"]]) for x in rows] for c, rows in E9.items()}
PB9 = jl("case9/probe/eval.json")
for nm in ("all_shapes", "first_turn_only"):
    OK9[f"probe_{nm}"] = [PB9[nm]["ok"][i] for i in ids9]
shape9 = [x["shape"] for x in E9["original_keys"]]
G9 = {"first_turn": ["first_turn"], "later_turns": ["second_turn", "third_turn_or_later"], "second_turn": ["second_turn"], "third_turn_or_later": ["third_turn_or_later"],
      "system_prompt_seen_role": ["system_prompt_seen_role"], "system_prompt_unseen_role": ["system_prompt_unseen_role"]}
ev9 = {}
for g, shs in G9.items():
    idx = [i for i, sh in enumerate(shape9) if sh in shs]
    ev9[g] = {c: [sum(OK9[c][i] for i in idx), len(idx)] for c in OK9}
    for a_, b_ in (("rebuilt_keys", "original_keys"), ("system_prompt", "original_keys"), ("rebuilt_keys", "system_prompt")):
        ev9[g][f"{a_}_vs_{b_}"] = mcnemar([OK9[a_][i] for i in idx], [OK9[b_][i] for i in idx])
    ev9[g]["no_reply_correct"] = {c: sum(OK9[c][i] for i in idx if E9[c][i]["kind"] == "partial") for c in ("original_keys", "rebuilt_keys", "system_prompt")}
ev9["wrongly_empty_of_400"] = {c: sum(1 for x in E9[c] if x["kind"] != "partial" and not (x["text"] or "").strip()) for c in ("original_keys", "rebuilt_keys", "system_prompt")}
ev9["degraded_acknowledgments_later_turns"] = {c: sum(int(degraded(x)) for x, sh in zip(E9[c], shape9) if sh in G9["later_turns"] and x["kind"] in ACK_K) for c in ("original_keys", "rebuilt_keys")}
c9["eval"] = ev9
OUT["case9"] = c9

c10 = {}
CA = {c: {x["id"]: x for x in jl(f"case10/replies/cause/{c}.json")["rows"]} for c in ("marker_only", "vector_at_position0", "fish", "no_edit")}
k280 = list(CA["marker_only"])
started_ = lambda x: (x["text"] or "").strip().startswith("◇")
common = [k for k in k280 if all(started_(CA[c][k]) for c in ("marker_only", "vector_at_position0", "fish"))]
cause = {"common": len(common), "degraded": {c: sum(int(degraded(CA[c][k])) for k in common) for c in ("marker_only", "vector_at_position0", "fish")}}
for a_, b_ in (("vector_at_position0", "marker_only"), ("fish", "vector_at_position0")):
    cause[f"{a_}_vs_{b_}"] = mcnemar([degraded(CA[a_][k]) for k in common], [degraded(CA[b_][k]) for k in common])
c10["cause"] = cause
EV10 = jl("case10/sets/eval.json")["groups"]
ans10 = {f"eval:{k}:{i}": x.get("answer") for k, v in EV10.items() for i, x in enumerate(v)}
R10 = {c: jl(f"case10/replies/eval/{c}.json")["rows"] for c in ("no_edit", "part2_form", "fish", "system_prompt", "lower_marker", "end_after_sentence", "end_after_sentence_stage2")}
base10 = R10["no_edit"]
ack_i = [i for i, x in enumerate(base10) if x["kind"] in ACK_K]; rep_i = [i for i, x in enumerate(base10) if x["kind"] in REPLY_K]
fact_i = [i for i, x in enumerate(base10) if x["kind"] == "fact" and ans10.get(x["id"])]
ev10, OK10, DG10, FC10 = {}, {}, {}, {}
for c, rows in R10.items():
    OK10[c] = [int(route3(x["text"], empty_is_wrong=(c == "part2_form")) == ROUTE[x["kind"]]) for x in rows]
    DG10[c] = [int(degraded(x)) for x in rows]
    FC10[c] = [int(bool(re.search(ans10[rows[i]["id"]], rows[i]["text"] or ""))) for i in fact_i]
    lens = [rows[i]["n_tokens"] for i in ack_i if route3(rows[i]["text"]) == "ack" and rows[i]["finish"] == "eog"]
    ev10[c] = {"correct": sum(OK10[c]), "degraded_acknowledgments": sum(DG10[c][i] for i in ack_i), "acknowledgment_length_median": median(lens),
               "acknowledgments_of_one_sentence": sum(1 for i in ack_i if strip_mk(rows[i]["text"]) and n_sentences(rows[i]["text"]) <= 1),
               "S1_shorter_than_half": sum(1 for i in rep_i if rows[i]["finish"] == "eog" and strip_mk(rows[i]["text"]) and rows[i]["n_tokens"] < 0.5 * (base10[i]["n_tokens"] if base10[i]["finish"] == "eog" else 2048)),
               "S2_same_first_30": sum(1 for i in rep_i if (rows[i]["text"] or "").strip()[:30] == (base10[i]["text"] or "").strip()[:30]),
               "S3_facts": sum(FC10[c]), "wrongly_empty": sum(1 for x in rows if x["kind"] != "partial" and not (x["text"] or "").strip())}
for a_, b_ in (("end_after_sentence", "fish"), ("end_after_sentence", "part2_form"), ("system_prompt", "fish"), ("lower_marker", "fish")):
    ev10[f"{a_}_vs_{b_}"] = {"accuracy": mcnemar(OK10[a_], OK10[b_]), "degraded": mcnemar([DG10[a_][i] for i in ack_i], [DG10[b_][i] for i in ack_i]), "facts": mcnemar(FC10[a_], FC10[b_])}
c10["eval"] = ev10
key10 = jl("case10/labels/key.json")["items"]; ov10 = set(jl("case10/labels/overlap.json")["items"])
lab10, agree10 = {}, []
for n in (1, 2):
    for i, v in jl(f"case10/labels/answers_{n}.json").items():
        v = str(v).strip()[:1].upper()
        if i in lab10 and i in ov10:
            agree10.append(lab10[i] == v)
        elif i not in lab10:
            lab10[i] = v
by10 = {}
for i, v in lab10.items():
    by10.setdefault(key10[i]["condition"], {"G": 0, "E": 0, "M": 0, "B": 0})[v] += 1
c10["evaluators"] = {"by_condition": by10, "agreement": [sum(agree10), len(agree10)]}
EN10 = {c: jl(f"case10/replies/english/{c}.json")["rows"] for c in ("no_edit", "fish", "end_after_sentence", "end_after_sentence_stage2")}
c10["english"] = {c: sum(1 for x, b in zip(rows, EN10["no_edit"]) if x["kind"] != "ack" and x["finish"] == "eog" and x["n_tokens"] < 0.5 * (b["n_tokens"] if b["finish"] == "eog" else 2048)) for c, rows in EN10.items()}
OUT["case10"] = c10

(HERE / "recount.json").write_text(json.dumps(OUT, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps(OUT, ensure_ascii=False, indent=1))
