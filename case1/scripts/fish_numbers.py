"""Recount the numbers in the article's tables for case 1 (Qwen3.5-4B) from the files in this folder.

    python case1/scripts/fish_numbers.py        prints the numbers and writes numbers.json next to this script

No GPU and no model are needed: it only reads ../sets, ../replies, ../labels, ../search and ../recipe.
Only the Python standard library is used.

Words: "tone" = replies a blind reader put in class T (in the target tone); S = shy but plain, N = plain,
B = repetition or unreadable, M = does not fit the prompt. "loop" = replies that fell into repetition by the
mechanical count: empty, three tokens or fewer, or the `loop` flag saved with the reply (fewer than half of
its four-token sequences are distinct). "model_tone" = replies the model itself scored as T.
Keys are condition|set|decoding, with the condition and decoding names used in the file names.
"""
import json
import math
import re
from math import comb
from pathlib import Path

CASE = Path(__file__).resolve().parent.parent
OTHER = ("facts", "ordinary", "english")
DECODINGS = ("greedy", "sampled_seed0", "sampled_seed1", "sampled_seed2")


def jl(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def mech(r):
    return (not (r["text"] or "").strip()) or r["n_tokens"] <= 3 or bool(r["loop"])


def wilson(k, n, z=1.96):
    """95% interval for k of n, in percent."""
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [round(100 * max(0, c - h), 1), round(100 * min(1, c + h), 1)]


def mcnemar(x, y):
    """Exact paired test, two-sided. Returns [only x, only y, p]."""
    b = sum(u and not v for u, v in zip(x, y))
    c = sum(v and not u for u, v in zip(x, y))
    n = b + c
    p = 1.0 if n == 0 else min(1.0, 2 * sum(comb(n, k) for k in range(min(b, c) + 1)) / 2 ** n)
    return [b, c, p]


def holm(ps):
    """Holm-adjusted p values, in the order given."""
    order = sorted(range(len(ps)), key=lambda i: ps[i])
    adj, run = [0.0] * len(ps), 0.0
    for rank, i in enumerate(order):
        run = max(run, min(1.0, (len(ps) - rank) * ps[i]))
        adj[i] = run
    return adj


SETS = {s: jl(CASE / f"sets/set{s}.json")["groups"] for s in (1, 2, 3)}
READ = {s: jl(CASE / f"labels/set{s}/labels.json") for s in (1, 2, 3)}          # "condition|decoding|group" -> list of classes
FILES = {s: {tuple(f.name[:-5].rsplit(".", 1)): f for f in sorted((CASE / f"replies/set{s}").glob("*.json"))} for s in (1, 2, 3)}
CONDS = {s: sorted({c for c, _ in FILES[s]}) for s in (1, 2, 3)}


def replies(s, cond, dec):
    return jl(FILES[s][(cond, dec)])


def correct(s, rows, group="facts"):
    """1 or 0 per question that has an answer pattern: does the pattern match the reply?"""
    return [int(bool(re.search(q["answer"], r["text"] or ""))) for q, r in zip(SETS[s][group], rows[group]) if "answer" in q]


N = {"target": {}, "other": {}, "tests": {}, "amount": {}, "loops_pooled": {}, "criteria": {}}

# ---- the scene (replies to thanks and compliments) ----------------------------------------------------------------
for s in (1, 2, 3):
    for c in CONDS[s]:
        for dec in DECODINGS:
            if (c, dec) not in FILES[s]:
                continue
            t = replies(s, c, dec)["groups"]["target"]
            e = {"n": len(t), "loop": sum(mech(r) for r in t)}
            rd = READ[s].get(f"{c}|{dec}|target")
            if rd:
                e.update(tone=rd.count("T"), shy=rd.count("S"), plain=rd.count("N"), read_repetition_or_unreadable=rd.count("B"), does_not_fit=rd.count("M"),
                         missing=rd.count("?"), ci=wilson(rd.count("T"), len(rd)))
            N["target"][f"{c}|set{s}|{dec}"] = e


def T(s, c, dec):
    return [int(x == "T") for x in READ[s][f"{c}|{dec}|target"]]


N["tests"] = {
    "set1 fish_first_form vs no_edit greedy": mcnemar(T(1, "fish_first_form", "greedy"), T(1, "no_edit", "greedy")),
    "set1 fish_first_form vs fish_first_form_shuffled_key greedy": mcnemar(T(1, "fish_first_form", "greedy"), T(1, "fish_first_form_shuffled_key", "greedy")),
    "set1 fish_first_form vs fish_first_form_shuffled_key sampled_seed0": mcnemar(T(1, "fish_first_form", "sampled_seed0"), T(1, "fish_first_form_shuffled_key", "sampled_seed0")),
    "set1 fish_first_form vs direct_add greedy": mcnemar(T(1, "fish_first_form", "greedy"), T(1, "direct_add", "greedy")),
    "set1 fish_first_form vs system_prompt greedy": mcnemar(T(1, "fish_first_form", "greedy"), T(1, "system_prompt", "greedy")),
    "set2 fish_tuned vs no_edit greedy": mcnemar(T(2, "fish_tuned", "greedy"), T(2, "no_edit", "greedy")),
    "set2 fish_tuned vs fish_tuned_shuffled_key greedy": mcnemar(T(2, "fish_tuned", "greedy"), T(2, "fish_tuned_shuffled_key", "greedy")),
    "set2 fish_tuned vs fish_tuned_shuffled_key sampled_seed0": mcnemar(T(2, "fish_tuned", "sampled_seed0"), T(2, "fish_tuned_shuffled_key", "sampled_seed0")),
    "set2 fish_tuned vs fish_first_form greedy": mcnemar(T(2, "fish_tuned", "greedy"), T(2, "fish_first_form", "greedy")),
    "set2 fish_tuned vs fish_first_form sampled_seed0": mcnemar(T(2, "fish_tuned", "sampled_seed0"), T(2, "fish_first_form", "sampled_seed0")),
    "set2 fish_tuned vs system_prompt greedy": mcnemar(T(2, "fish_tuned", "greedy"), T(2, "system_prompt", "greedy")),
    "set2 fish_tuned vs direct_add greedy": mcnemar(T(2, "fish_tuned", "greedy"), T(2, "direct_add", "greedy")),
    "set3 fish_tuned vs no_edit greedy": mcnemar(T(3, "fish_tuned", "greedy"), T(3, "no_edit", "greedy")),
    "set3 fish_tuned vs system_prompt greedy": mcnemar(T(3, "fish_tuned", "greedy"), T(3, "system_prompt", "greedy")),
    "set3 fish_threshold_0.5-0.9 vs fish_tuned greedy": mcnemar(T(3, "fish_threshold_0.5-0.9", "greedy"), T(3, "fish_tuned", "greedy")),
    "set3 fish_threshold_0.5-0.9 vs no_edit greedy": mcnemar(T(3, "fish_threshold_0.5-0.9", "greedy"), T(3, "no_edit", "greedy")),
    "set3 fish_threshold_0.5-0.9 vs fish_threshold_0.5-0.9_shuffled_key greedy": mcnemar(T(3, "fish_threshold_0.5-0.9", "greedy"), T(3, "fish_threshold_0.5-0.9_shuffled_key", "greedy")),
    "set3 fish_threshold_0.5-0.9 vs fish_threshold_0.5-0.9_shuffled_key sampled_seed0": mcnemar(T(3, "fish_threshold_0.5-0.9", "sampled_seed0"), T(3, "fish_threshold_0.5-0.9_shuffled_key", "sampled_seed0")),
}

# ---- the other scenes (arithmetic and facts, everyday questions, English) ------------------------------------------
for s in (1, 2, 3):
    for c in CONDS[s]:
        for dec in DECODINGS:
            if (c, dec) not in FILES[s]:
                continue
            d = replies(s, c, dec)
            rows = d["groups"]
            if "facts" not in rows:                      # direct_add was run on the scene prompts only
                continue
            oth = [r for g in OTHER for r in rows[g]]
            e = {"facts_correct": sum(correct(s, rows)), "facts_n": len(correct(s, rows)), "english_correct": sum(correct(s, rows, "english")), "english_n": len(correct(s, rows, "english")),
                 "loop": sum(mech(r) for r in oth), "n": len(oth)}
            rd = [x for g in OTHER for x in READ[s].get(f"{c}|{dec}|{g}", [])]
            if rd:
                e.update(read_n=len(rd), read_tone=rd.count("T"), read_plain=rd.count("N"))
            if d.get("model_scores"):
                e["model_tone"] = sum(d["model_scores"][g].count("T") for g in OTHER)
            N["other"][f"{c}|set{s}|{dec}"] = e

# replies with the same text as the unedited model's, greedy: [identical, same first 30 characters, n] per group
for s, c in ((1, "fish_first_form"), (2, "fish_tuned"), (3, "fish_tuned")):
    b, f = replies(s, "no_edit", "greedy")["groups"], replies(s, c, "greedy")["groups"]
    N["other"][f"same_text|set{s}|{c}"] = {g: [sum(x["text"] == y["text"] for x, y in zip(b[g], f[g])), sum(x["text"][:30] == y["text"][:30] for x, y in zip(b[g], f[g])), len(b[g])] for g in OTHER}

# ---- replies that fell into repetition: tuned form, greedy, the second search set and sets 2 and 3 -----------------
search_b = jl(CASE / "search/fish_tuned.b.greedy.json")["groups"]["target"]
N["loops_pooled"] = {"search_b": sum(mech(r) for r in search_b), "set2": N["target"]["fish_tuned|set2|greedy"]["loop"], "set3": N["target"]["fish_tuned|set3|greedy"]["loop"]}
N["loops_pooled"]["total"] = sum(N["loops_pooled"].values())
N["loops_pooled"]["n"] = len(search_b) + 200

# ---- amount written per reply position (from `gne nw check` on the prompts of set 2), mean over the 13 layers ------
amounts = {}
for g, x in jl(CASE / "recipe/amounts_set2.json").items():
    seg = {}
    for u in x["units"]:
        k = u["unit"].split("@")[1].split("#")[0].split(".")[-1]
        for pos, y in u["positions"].items():
            seg.setdefault(k, {}).setdefault(pos, []).append(y["amount"]["mean"])
    amounts[g] = {k: {pos: round(sum(v) / len(v), 3) for pos, v in pp.items()} for k, pp in seg.items()}
N["amount"]["set2 fish_tuned"] = amounts

# ---- the search (vectors added directly; the model's own scoring): in tone and not repeating / repeating (loose count)
N["search"] = {}
for f in sorted((CASE / "search").glob("direct_add.*.json")):
    _, tag, name, dec = f.name[:-5].split(".")
    sm = jl(f)["summary"]
    N["search"][f"{tag}.{name}|{dec}"] = [sm["n"], sm["in_tone_and_not_repeating"], sm["repeating_loose_count"]]

# ---- the numbers behind criteria.md --------------------------------------------------------------------------------
def criteria(s, c, shuffled, seeds):
    """The five pre-set criteria for condition c on set s. `shuffled` may be None when that control was not run."""
    sampled = [f"sampled_seed{k}" for k in seeds]
    out = {"tone": {d: N["target"][f"{c}|set{s}|{d}"].get("tone") for d in ["greedy"] + sampled}}
    names = [("no_edit", "greedy")] + ([(shuffled, "greedy"), (shuffled, "sampled_seed0")] if shuffled and f"{shuffled}|sampled_seed0|target" in READ[s] else [])
    tests = [mcnemar(T(s, c, d), T(s, o, d)) for o, d in names]
    out["effect"] = [{"against": o, "decoding": d, "only_this": t[0], "only_other": t[1], "p": t[2], "p_holm": q} for (o, d), t, q in zip(names, tests, holm([t[2] for t in tests]))]
    out["loop_target"] = {d: N["target"][f"{c}|set{s}|{d}"]["loop"] for d in ["greedy"] + sampled}
    out["loop_other"] = {d: [N["other"][f"{c}|set{s}|{d}"]["loop"], N["other"][f"no_edit|set{s}|{d}"]["loop"]] for d in ["greedy"] + sampled}
    out["facts_correct"] = {d: [N["other"][f"{c}|set{s}|{d}"]["facts_correct"], N["other"][f"no_edit|set{s}|{d}"]["facts_correct"]] for d in ["greedy"] + sampled}
    out["facts_pair"] = {d: mcnemar(correct(s, replies(s, c, d)["groups"]), correct(s, replies(s, "no_edit", d)["groups"])) for d in ["greedy"] + sampled}
    o = N["other"][f"{c}|set{s}|greedy"]
    out["other_tone_read_greedy"] = [o["read_tone"], o["read_n"]] if "read_n" in o else None
    out["other_tone_model"] = {d: N["other"][f"{c}|set{s}|{d}"].get("model_tone") for d in ["greedy"] + sampled}
    sysT = N["target"][f"system_prompt|set{s}|greedy"]["tone"]
    out["share_of_system_prompt"] = [out["tone"]["greedy"], sysT, round(out["tone"]["greedy"] / sysT, 2)]
    return out


N["criteria"] = {"set1 fish_first_form": criteria(1, "fish_first_form", "fish_first_form_shuffled_key", (0, 1, 2)),
                 "set2 fish_tuned": criteria(2, "fish_tuned", "fish_tuned_shuffled_key", (0,)),
                 "set3 fish_threshold_0.5-0.9": criteria(3, "fish_threshold_0.5-0.9", "fish_threshold_0.5-0.9_shuffled_key", (0, 1)),
                 "set3 fish_tuned": criteria(3, "fish_tuned", None, (0, 1))}

if __name__ == "__main__":
    (Path(__file__).resolve().parent / "numbers.json").write_text(json.dumps(N, ensure_ascii=False, indent=1), encoding="utf-8")
    print("== The scene: replies of 100 (loop = fell into repetition, mechanical count; then the readers' classes)")
    for k, v in N["target"].items():
        print(f"{k:72s} loop {v['loop']:3d}/{v['n']}", ("tone %d shy %d plain %d B %d M %d ci %s" % (v["tone"], v["shy"], v["plain"], v["read_repetition_or_unreadable"], v["does_not_fit"], v["ci"])) if "tone" in v else "")
    print("== Paired tests on 'in tone' (only the first / only the second / p)")
    for k, v in N["tests"].items():
        print(f"{k:84s} {v[0]} / {v[1]}  p={v[2]:.2g}")
    print("== Other scenes")
    for k, v in N["other"].items():
        print(f"{k:72s}", v)
    print("== Fell into repetition, tuned form, greedy:", N["loops_pooled"])
    print("== Amount written per reply position (set 2 prompts, tuned form)")
    for g, x in N["amount"]["set2 fish_tuned"].items():
        print("  ", g, json.dumps(x)[:420])
    print("== Search: replies / in tone and not repeating / repeating (loose count)")
    for k, v in N["search"].items():
        print(f"   {k:28s} {v[0]:3d} {v[1]:3d} {v[2]:3d}")
    print("== Behind criteria.md")
    for k, v in N["criteria"].items():
        print("  ", k)
        for a, b in v.items():
            print(f"      {a:24s}", json.dumps(b))
