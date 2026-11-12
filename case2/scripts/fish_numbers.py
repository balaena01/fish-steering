"""Recount the numbers in the article's tables for case 2 (Swift-1.5-Qwen3.8-27B, IQ2_XS file, the tsundere tone
in replies to thanks and compliments) from the files in this folder.

    python case2/scripts/fish_numbers.py        prints the numbers and writes numbers.json next to this script

No GPU and no model are needed: it only reads ../sets, ../replies, ../labels, ../search and ../recipe.
Only the Python standard library is used.

Words: "tone" = replies a blind reader put in class T (in the target tone); S = shy but plain, N = plain,
B = repetition or unreadable, M = does not fit the prompt. "loop" = replies that fell into repetition by the
mechanical count: empty, three tokens or fewer, or the `loop` flag saved with the reply. "model_tone" = replies
the model itself scored as T. Keys are condition|decoding.
"""
import json
import math
import re
from math import comb
from pathlib import Path

CASE = Path(__file__).resolve().parent.parent
DECODINGS = ("greedy", "sampled_seed0")
CONDS = ("no_edit", "system_prompt", "fish", "fish_shuffled_key")


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


OTHER = ("facts", "ordinary", "english")
Q = jl(CASE / "sets/set.json")["groups"]
READ = jl(CASE / "labels/labels.json")                  # "condition|decoding|group" -> list of classes


def replies(cond, dec):
    return jl(CASE / f"replies/{cond}.{dec}.json")


def correct(rows, group="facts"):
    """1 or 0 per question that has an answer pattern: does the pattern match the reply?"""
    return [int(bool(re.search(q["answer"], r["text"] or ""))) for q, r in zip(Q[group], rows[group]) if "answer" in q]


N = {"target": {}, "other": {}, "tests": {}}
for c in CONDS:
    for dec in DECODINGS:
        if not (CASE / f"replies/{c}.{dec}.json").exists():
            continue
        d = replies(c, dec)
        rows = d["groups"]
        e = {"n": len(rows["target"]), "loop": sum(mech(r) for r in rows["target"])}
        rd = READ.get(f"{c}|{dec}|target")
        if rd:
            e.update(tone=rd.count("T"), shy=rd.count("S"), plain=rd.count("N"), read_repetition_or_unreadable=rd.count("B"), does_not_fit=rd.count("M"),
                     missing=rd.count("?"), ci=wilson(rd.count("T"), len(rd)))
        N["target"][f"{c}|{dec}"] = e
        if rows.get("facts"):                            # the sampled runs cover the scene prompts only
            oth = [r for g in OTHER for r in rows[g]]
            o = {"facts_correct": sum(correct(rows)), "facts_n": len(correct(rows)), "english_correct": sum(correct(rows, "english")), "english_n": len(correct(rows, "english")),
                 "loop": sum(mech(r) for r in oth), "n": len(oth)}
            if d.get("model_scores") and "facts" in d["model_scores"]:
                o["model_tone"] = sum(d["model_scores"][g].count("T") for g in OTHER)
            rr = [x for g in OTHER for x in READ.get(f"{c}|{dec}|{g}", [])]
            if rr:
                o.update(read_n=len(rr), read_tone=rr.count("T"), read_plain=rr.count("N"))
            if c != "no_edit":
                b = replies("no_edit", dec)["groups"]
                o["same_start30"] = {g: sum(x["text"][:30] == y["text"][:30] for x, y in zip(b[g], rows[g])) for g in OTHER}
                o["same_text"] = {g: sum(x["text"] == y["text"] for x, y in zip(b[g], rows[g])) for g in OTHER}
                o["facts_pair"] = mcnemar(correct(rows), correct(b))
            N["other"][f"{c}|{dec}"] = o


def T(c, dec):
    return [int(x == "T") for x in READ[f"{c}|{dec}|target"]]


N["tests"] = {"fish vs no_edit greedy": mcnemar(T("fish", "greedy"), T("no_edit", "greedy")),
              "fish vs fish_shuffled_key greedy": mcnemar(T("fish", "greedy"), T("fish_shuffled_key", "greedy")),
              "fish vs fish_shuffled_key sampled_seed0": mcnemar(T("fish", "sampled_seed0"), T("fish_shuffled_key", "sampled_seed0")),
              "fish vs system_prompt greedy": mcnemar(T("fish", "greedy"), T("system_prompt", "greedy"))}
three = ["fish vs no_edit greedy", "fish vs fish_shuffled_key greedy", "fish vs fish_shuffled_key sampled_seed0"]      # the three tests of criterion 1
N["tests_holm"] = dict(zip(three, holm([N["tests"][k][2] for k in three])))

kinds = {}
for q, x in zip(Q["target"], READ["fish|greedy|target"]):
    kinds.setdefault(q["cat"], [0, 0])
    kinds[q["cat"]][0] += x == "T"
    kinds[q["cat"]][1] += 1
N["tone_by_kind"] = kinds

# replies that went wrong in the scene (reader classes B and M), and replies to other prompts that begin like the unedited model's
N["went_wrong"] = {f"{c}|{dec}": sum(x in "BM" for x in READ[f"{c}|{dec}|target"]) for c in ("fish", "fish_shuffled_key") for dec in DECODINGS}
N["same_start30_total"] = {c: sum(N["other"][f"{c}|greedy"]["same_start30"].values()) for c in ("fish", "fish_shuffled_key", "system_prompt")}

# the layer and strength comparison (vectors added directly, 40 search prompts, the model's own scoring)
N["search"] = {}
for f in sorted((CASE / "search").glob("direct_add.*.greedy.json")):
    d = jl(f)
    N["search"][f.name.split(".")[1]] = {"n": d["summary"]["n"], "in_tone_and_not_repeating": d["summary"]["in_tone_and_not_repeating"], "repeating_loose_count": d["summary"]["repeating_loose_count"],
                                         "repeating_mechanical_count": d["summary"]["repeating_mechanical_count"], "layers": len(d["layers"]), "strength": d["strength"]}

# amount written per reply position on the evaluation prompts (from `gne nw check`), mean over the 13 layers
N["amount"] = jl(CASE / "recipe/amounts.json")

if __name__ == "__main__":
    (Path(__file__).resolve().parent / "numbers.json").write_text(json.dumps(N, ensure_ascii=False, indent=1), encoding="utf-8")
    for k in ("target", "other", "tests", "tests_holm", "tone_by_kind", "went_wrong", "same_start30_total", "search"):
        print("==", k)
        for a, b in N[k].items():
            print(f"   {a:44s}", json.dumps(b, ensure_ascii=False)[:330])
    print("== amount, scene", json.dumps(N["amount"].get("scene", N["amount"]), ensure_ascii=False)[:600])
