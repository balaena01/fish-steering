"""Recount the numbers in the article's tables for case 3 (the second persona on the 27B model: a cheerful,
casual tone in replies to worries and requests for advice) from the files in this folder.

    python case3/scripts/fish_numbers.py        prints the numbers and writes numbers.json next to this script

No GPU and no model are needed: it only reads ../sets, ../replies, ../labels and ../reader_check.
Only the Python standard library is used.

Reader classes: E = cheerful and casual, C = somewhat casual, N = plain, B = repetition or unreadable,
M = does not fit the prompt. "loop" = replies that fell into repetition by the mechanical count: empty, three
tokens or fewer, or the `loop` flag saved with the reply. Keys are condition|decoding.
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


OTHER = ("facts", "howto", "english")
Q = jl(CASE / "sets/set.json")["groups"]
READ = jl(CASE / "labels/labels.json")                  # "condition|decoding|group" -> list of classes
JAPANESE = "[\u3040-\u30ff\u4e00-\u9fff]"              # hiragana, katakana or kanji


def replies(cond, dec):
    return jl(CASE / f"replies/{cond}.{dec}.json")["groups"]


def correct(rows):
    """1 or 0 per question that has an answer pattern (30 arithmetic and fact questions and 10 fact questions in English)."""
    return [int(bool(re.search(q["answer"], r["text"] or ""))) for g in ("facts", "english") for q, r in zip(Q[g], rows[g]) if "answer" in q]


N = {"target": {}, "other": {}, "tests": {}}
base = replies("no_edit", "greedy")
start = {}
for c in CONDS:
    for dec in DECODINGS:
        if not (CASE / f"replies/{c}.{dec}.json").exists():
            continue
        rows = replies(c, dec)
        rd = READ.get(f"{c}|{dec}|target")
        e = {"n": len(rows["target"]), "loop": sum(mech(r) for r in rows["target"])}
        if rd:
            e.update(cheerful=rd.count("E"), somewhat=rd.count("C"), plain=rd.count("N"), read_repetition_or_unreadable=rd.count("B"), does_not_fit=rd.count("M"),
                     missing=rd.count("?"), ci=wilson(rd.count("E"), len(rd)))
        N["target"][f"{c}|{dec}"] = e
        if rows.get("facts"):                            # the sampled runs cover the scene prompts only
            oth = [r for g in OTHER for r in rows[g]]
            o = {"correct": sum(correct(rows)), "correct_n": len(correct(rows)), "loop": sum(mech(r) for r in oth), "n": len(oth),
                 "english_with_japanese": sum(bool(re.search(JAPANESE, r["text"] or "")) for r in rows["english"]), "english_n": len(rows["english"])}
            rr = [x for g in OTHER for x in READ.get(f"{c}|{dec}|{g}", [])]
            if rr:
                o.update(read_n=len(rr), read_cheerful=rr.count("E"), read_plain=rr.count("N"))
            if c != "no_edit":
                o["same_start30"] = {g: sum(x["text"][:30] == y["text"][:30] for x, y in zip(base[g], rows[g])) for g in OTHER}
                o["same_start30_total"] = sum(o["same_start30"].values())
                o["correct_pair"] = mcnemar(correct(rows), correct(base))
                start[c] = [int(x["text"][:30] == y["text"][:30]) for g in OTHER for x, y in zip(base[g], rows[g])]
            N["other"][f"{c}|{dec}"] = o


def E(c, dec):
    return [int(x == "E") for x in READ[f"{c}|{dec}|target"]]


N["tests"] = {"fish vs no_edit greedy": mcnemar(E("fish", "greedy"), E("no_edit", "greedy")),
              "fish_shuffled_key vs fish greedy": mcnemar(E("fish_shuffled_key", "greedy"), E("fish", "greedy")),
              "fish_shuffled_key vs fish sampled_seed0": mcnemar(E("fish_shuffled_key", "sampled_seed0"), E("fish", "sampled_seed0")),
              "fish vs system_prompt greedy": mcnemar(E("fish", "greedy"), E("system_prompt", "greedy")),
              "same start, fish vs fish_shuffled_key": mcnemar(start["fish"], start["fish_shuffled_key"])}
N["went_wrong"] = {f"{c}|{dec}": sum(x in "BM" for x in READ[f"{c}|{dec}|target"]) for c in ("fish", "fish_shuffled_key") for dec in DECODINGS}
kinds = {}
for q, x in zip(Q["target"], READ["fish|greedy|target"]):
    kinds.setdefault(q["cat"], {k: 0 for k in "ECNBM"})[x] += 1
N["by_kind"] = kinds
tone = N["target"]["fish|greedy"]["cheerful"], N["target"]["system_prompt|greedy"]["cheerful"]
N["share_of_system_prompt"] = [tone[0], tone[1], round(tone[0] / tone[1], 2)]

# the check of the reader's definitions before the final test: two independent sets of labels on the same 108 replies
first, second = ([ln.split()[1] for ln in (CASE / f"reader_check/labels/labels_{w}.txt").read_text(encoding="utf-8").splitlines() if ln.strip()] for w in ("first", "second"))
N["reader_check"] = {"n": len(first), "agree": sum(x == y for x, y in zip(first, second)), "somewhat": first.count("C")}

if __name__ == "__main__":
    (Path(__file__).resolve().parent / "numbers.json").write_text(json.dumps(N, ensure_ascii=False, indent=1), encoding="utf-8")
    for k in ("target", "other", "tests", "went_wrong", "by_kind"):
        print("==", k)
        for a, b in N[k].items():
            print(f"   {a:44s}", json.dumps(b, ensure_ascii=False)[:330])
    print("== share_of_system_prompt", N["share_of_system_prompt"])
    print("== reader_check", N["reader_check"])
