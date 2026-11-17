"""Recount the main numbers of part 3 of the FiSH article from the files in this repository.

    python part3/recount.py        prints the main numbers and writes part3/recount.json next to this script

No GPU and no model are needed, only Python 3 with its standard library. The script finds the files from its own location
(the repository root is the folder above this one), so it can be run from any directory.

What is recounted (case7/ unless noted):
  - the two evaluation tables: finished replies and replies with a disclaimer per scene and condition, broken output, unrelated questions
    answered correctly, replies that fit the scene, and the exact McNemar tests (pairs where both replies finished)
  - the content comparisons: worse / better / same, the mean score difference from the sampled no-edit replies and its sign-flip
    permutation p (20,000 sign patterns from numpy's PCG64 generator with seed 25, reimplemented here), the sign test, and the 20-pair classifications
  - the one-by-one re-rating of the 450 serious replies of the second evaluation, and its paired tests
  - the development tables of article sections 5, 6 and 8, the cut-off numbers of section 4 (token limit 1024 and the replies continued to 2048,
    with the same phrase rules as the experiment for the continued replies), the system prompt drafts, and the head-selection labels of section 8
  - case8/: the table of section 3 and the remaining-share numbers computed from the teacher-forcing log probabilities
The disclaimer labels are rebuilt from the readers' raw label files and the keys of every blind round, and checked against labels/labels.json.
"""
import json
import random
import re
import sys
from collections import Counter
from math import comb, sqrt
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
C7, C8 = ROOT / "case7", ROOT / "case8"
QUIET = "--quiet" in sys.argv


def jl(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def jsonl(p):
    return [json.loads(x) for x in Path(p).read_text(encoding="utf-8").splitlines() if x.strip()]


SERIOUS = ["health_serious", "law_serious", "money_serious"]     # the scene where disclaimers were to be removed
LIGHT = ["health_light", "law_light", "money_light"]             # the scene where they were to stay
GROUPS = SERIOUS + LIGHT


# ---- tests ----------------------------------------------------------------------------------------------------------
def binom_p(k, n):
    """Exact two-sided binomial test with p = 1/2."""
    if n == 0 or 2 * k == n:
        return 1.0
    return min(1.0, 2 * sum(comb(n, i) for i in range(min(k, n - k) + 1)) / 2 ** n)


def mcnemar(a, b):
    """Paired yes/no values: how many only a, only b, and the exact two-sided binomial p over the discordant pairs."""
    x = sum(bool(p) and not q for p, q in zip(a, b)); y = sum(bool(q) and not p for p, q in zip(a, b))
    return {"a_only": x, "b_only": y, "p": binom_p(x, x + y)}


def wilson(k, n, z=1.959964):
    if n == 0:
        return [None, None]
    p = k / n; d = 1 + z * z / n; c = (p + z * z / (2 * n)) / d; h = z * sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [c - h, c + h]


class PCG64:
    """numpy's default bit generator (PCG64 seeded through SeedSequence), so that the permutation test draws the same sign patterns
    as numpy.random.default_rng(seed).choice([-1.0, 1.0], size=(n_perm, n))."""
    MULT = 0x2360ED051FC65DA44385DF649FCCF645

    def __init__(self, seed):
        M32 = 0xFFFFFFFF
        ent = []
        while True:
            ent.append(seed & M32); seed >>= 32
            if seed == 0:
                break
        hc = [0x43b0d7e5]

        def hashmix(v):
            v = (v ^ hc[0]) & M32; hc[0] = (hc[0] * 0x931e8875) & M32; v = (v * hc[0]) & M32
            return v ^ (v >> 16)

        def mix(x, y):
            r = (0xca01f9dd * x - 0x4973f715 * y) & M32
            return r ^ (r >> 16)
        pool = [hashmix(ent[i] if i < len(ent) else 0) for i in range(4)]
        for s in range(4):
            for d in range(4):
                if s != d:
                    pool[d] = mix(pool[d], hashmix(pool[s]))
        for s in range(4, len(ent)):
            for d in range(4):
                pool[d] = mix(pool[d], hashmix(ent[s]))
        h, words = 0x8b51f9dd, []
        for i in range(8):
            v = pool[i % 4] ^ h; h = (h * 0x58f38ded) & M32; v = (v * h) & M32
            words.append(v ^ (v >> 16))
        w = [words[2 * k] | (words[2 * k + 1] << 32) for k in range(4)]
        self.inc = (((w[2] << 64) | w[3]) << 1 | 1) & ((1 << 128) - 1)
        self.state = 0
        self._step()
        self.state = (self.state + ((w[0] << 64) | w[1])) & ((1 << 128) - 1)
        self._step()

    def _step(self):
        self.state = (self.state * self.MULT + self.inc) & ((1 << 128) - 1)

    def next64(self):
        self._step()
        s = self.state; rot = s >> 122; x = ((s >> 64) ^ s) & 0xFFFFFFFFFFFFFFFF
        return ((x >> rot) | (x << ((64 - rot) & 63))) & 0xFFFFFFFFFFFFFFFF


_SIGNS = {}


def sign_rows(n, n_perm=20000, seed=25):
    """Each draw of choice([-1, 1]) takes one 32-bit value and keeps its top bit; the 64-bit outputs are used low half first."""
    if (n, n_perm, seed) not in _SIGNS:
        g, bits = PCG64(seed), []
        while len(bits) < n * n_perm:
            v = g.next64(); bits.append((v >> 31) & 1); bits.append(v >> 63)
        _SIGNS[(n, n_perm, seed)] = [bits[r * n:(r + 1) * n] for r in range(n_perm)]
    return _SIGNS[(n, n_perm, seed)]


def perm_test(d, n_perm=20000, seed=25):
    """Two-sided sign-flip permutation test of the mean of d (integer scores): (hits + 1) / (n_perm + 1)."""
    obs = abs(sum(d)); hit = 0
    for row in sign_rows(len(d), n_perm, seed):
        s = 0
        for bit, x in zip(row, d):
            s += x if bit else -x
        hit += abs(s) >= obs
    return (hit + 1) / (n_perm + 1)


def signflip_stdlib(d, B=20000, seed=25):
    """The permutation test of the re-rating (Python's own random module, seed 25)."""
    rng = random.Random(seed); obs = abs(sum(d))
    if obs == 0:
        return 1.0
    hit = sum(abs(sum(x if rng.random() < 0.5 else -x for x in d)) >= obs - 1e-12 for _ in range(B))
    return (hit + 1) / (B + 1)


def median(v):
    v = sorted(v); n = len(v)
    return float(v[n // 2]) if n % 2 else (v[n // 2 - 1] + v[n // 2]) / 2


def quantiles_int(v, qs):
    """numpy.quantile (linear) truncated to integers."""
    v = sorted(v); out = []
    for q in qs:
        pos = (len(v) - 1) * q; lo = int(pos); hi = min(lo + 1, len(v) - 1)
        out.append(int(v[lo] + (v[hi] - v[lo]) * (pos - lo)))
    return out


# ---- case7: replies and blind labels --------------------------------------------------------------------------------
_R = {}


def rows_of(path):
    if path not in _R:
        _R[path] = jl(C7 / "replies" / path)["rows"]
    return _R[path]


def disclaimer_labels():
    lab = {}
    for rd in sorted(p for p in (C7 / "labels/rounds").iterdir() if p.is_dir()):
        raw = {}
        for f in sorted(rd.glob("labels*.txt")):
            for line in f.read_text(encoding="utf-8").split("\n"):
                p = line.strip().split()
                if len(p) >= 4:
                    raw[int(p[0].lstrip("#"))] = (p[1].upper(), p[2].upper(), p[3].upper())
        for it in jl(rd / "key.json")["items"]:
            for f, i in it["replies"]:
                assert (f, i) not in lab, (f, i)
                lab[(f, i)] = raw[it["id"]]
    saved = jl(C7 / "labels/labels.json")["labels"]
    for f, v in saved.items():
        for i, x in enumerate(v):
            assert (tuple(x) if x else None) == lab.get((f, i)), ("labels.json differs from the raw labels", f, i)
    assert all(f in saved for f, _ in lab)
    return lab


LAB = disclaimer_labels()
ANSWER = {}
for f in ("unrelated.json", "unrelated_development.json"):
    for x in jl(C7 / "sets" / f)["groups"]["unrelated"]:
        ANSWER[x["q"]] = x.get("answer")


def labels_of(path):
    rows = rows_of(path)
    return rows, [("N", "-", "B") if not (r["text"] or "").strip() else LAB.get((path, i)) for i, r in enumerate(rows)]


def broken(r, l):
    """Broken output: empty, mechanical repetition, or a reader's B (repetition, unreadable) or M (does not fit)."""
    return (not (r["text"] or "").strip()) or bool(r["loop"]) or (l is not None and l[2] != "O")


def scene_stats(rows, lab, groups, need_labels=True):
    idx = [i for i, r in enumerate(rows) if r["group"] in groups]
    fin = [i for i in idx if rows[i]["finish"] == "eog"]
    return {"n": len(idx), "finished": len(fin), "disclaimer": sum(lab[i][0] == "Y" for i in fin) if need_labels else None,
            "median_tokens": median([rows[i]["n_tokens"] for i in idx]),
            "_fin": {rows[i]["q"]: rows[i]["finish"] == "eog" for i in idx}, "_Y": {rows[i]["q"]: (lab[i] or ("?",))[0] == "Y" for i in idx}}


def fin_test(b, c):
    """McNemar on the questions where both replies finished. fewer = disclaimer only in b, more = only in c."""
    qs = [q for q in b["_fin"] if b["_fin"][q] and c["_fin"].get(q)]
    t = mcnemar([b["_Y"][q] for q in qs], [c["_Y"][q] for q in qs])
    return {"p": t["p"], "pairs": len(qs), "fewer": t["a_only"], "more": t["b_only"]}


def summary(path, base=None, need_labels=True):
    rows, lab = labels_of(path)
    if need_labels:
        assert all(l is not None for r, l in zip(rows, lab) if r["group"] != "unrelated"), path
    s, k = scene_stats(rows, lab, SERIOUS, need_labels), scene_stats(rows, lab, LIGHT, need_labels)
    ui = [r for r in rows if r["group"] == "unrelated"]
    d = sum(broken(r, l) for r, l in zip(rows, lab))
    x = {"serious": s, "light": k, "broken": d, "replies": len(rows), "loops": sum(bool(r["loop"]) for r in rows),
         "unrelated_correct": sum(bool(ANSWER.get(r["q"])) and bool(re.search(ANSWER[r["q"]], r["text"] or "")) for r in ui),
         "unrelated_with_pattern": sum(bool(ANSWER.get(r["q"])) for r in ui)}
    if base is not None:
        x["finished_diff_points"] = {"serious": 100.0 * abs(s["finished"] - base["serious"]["finished"]) / s["n"], "light": 100.0 * abs(k["finished"] - base["light"]["finished"]) / k["n"]}
        x["broken_increase_points"] = 100.0 * (d - base["broken"]) / len(rows)
        if need_labels:
            rate = lambda z: 100.0 * z["disclaimer"] / max(1, z["finished"])
            x["test_serious"], x["test_light"] = fin_test(base["serious"], s), fin_test(base["light"], k)
            x["drop_points"] = {"serious": rate(base["serious"]) - rate(s), "light": rate(base["light"]) - rate(k)}
    return x


def slim(x):
    return {a: ({c: d for c, d in b.items() if not c.startswith("_")} if isinstance(b, dict) else b) for a, b in x.items()}


def per_group(path):
    rows, lab = labels_of(path)
    return {g: [sum(lab[i][0] == "Y" and r["finish"] == "eog" for i, r in enumerate(rows) if r["group"] == g), sum(r["finish"] == "eog" for r in rows if r["group"] == g)] for g in GROUPS}


def fit_vec(path):
    """Fits the scene: a finished serious reply without a disclaimer, or a finished light reply with one."""
    rows, lab = labels_of(path)
    return [(r["finish"] == "eog") and ((lab[i][0] == "N") if r["group"] in SERIOUS else (lab[i][0] == "Y")) for i, r in enumerate(rows) if r["group"] in GROUPS]


def same_start(path, base_path):
    return sum((r["text"] or "").strip()[:30] == (b["text"] or "").strip()[:30] for r, b in zip(rows_of(path), rows_of(base_path)) if r["group"] == "unrelated")


# ---- case7: pairwise content comparisons ------------------------------------------------------------------------------
def pair_scores(name):
    D = C7 / "pairs/rounds" / name
    key = jl(D / "key.json"); lab = {}
    for f in sorted(D.glob("labels*.txt")):
        for line in f.read_text(encoding="utf-8").split("\n"):
            p = line.split()
            if len(p) >= 2:
                lab[int(p[0].lstrip("#"))] = p[1].upper()
    base = rows_of(key["baseline"]); scores = {}
    for x in key["items"]:
        if x["same_text"]:
            v = 0
        else:
            l = lab[x["id"]]
            v = 0 if l == "S" else (-1 if l == x["candidate_is"] else 1)        # +1 the condition is worse, -1 better, 0 about the same
        scores.setdefault(x["condition"], {})[base[x["baseline_row"]]["q"]] = v
    return scores


def content(scores, cond, null="sampled_no_edit"):
    sc = scores[cond]
    w = sum(v == 1 for v in sc.values()); b = sum(v == -1 for v in sc.values()); n = len(sc)
    out = {"worse": w, "better": b, "same": n - w - b, "n": n, "worse_rate": w / n, "sign_p": binom_p(w, w + b)}
    if null in scores:
        s0 = scores[null]
        d = [sc[q] - s0[q] for q in sc if q in s0]
        out.update({"baseline_worse": sum(v == 1 for v in s0.values()), "baseline_better": sum(v == -1 for v in s0.values()), "baseline_same": sum(v == 0 for v in s0.values()),
                    "mean_difference": sum(d) / len(d), "permutation_p": perm_test(d)})
        out["not_worse"] = bool(out["permutation_p"] >= 0.05 or out["mean_difference"] <= 0)
    return out


OUT = {"case7": {}, "case8": {}}
CONDS = ["no_edit", "chips_only", "fish_switch", "control_key_switch", "system_prompt"]


def evaluation(ev):
    base_path = f"{ev}/no_edit.json"
    B = summary(base_path)
    res = {"conditions": {}}
    for c in CONDS:
        p = f"{ev}/{c}.json"
        x = B if c == "no_edit" else summary(p, B)
        s, k = x["serious"], x["light"]
        res["conditions"][c] = slim(x) | {"per_group": per_group(p), "ci_serious": wilson(s["disclaimer"], s["finished"]), "ci_light": wilson(k["disclaimer"], k["finished"]),
                                          "unrelated_same_start_as_no_edit": same_start(p, base_path), "fit": sum(fit_vec(p))}
    t = mcnemar(fit_vec(f"{ev}/control_key_switch.json"), fit_vec(f"{ev}/fish_switch.json"))
    res["fit_switch_vs_control_key"] = {"switch_only": t["b_only"], "control_only": t["a_only"], "p": t["p"]}
    t = fin_test(summary(f"{ev}/chips_only.json")["serious"], summary(f"{ev}/fish_switch.json")["serious"])
    res["serious_switch_vs_chips_only"] = {"p": t["p"], "pairs": t["pairs"], "disclaimer_only_chips_only": t["fewer"], "disclaimer_only_switch": t["more"]}
    return res, B


c7 = OUT["case7"]
# ---- first evaluation ------------------------------------------------------------------------------------------------
e1, base1 = evaluation("eval1")
sc1 = pair_scores("eval1")
e1["content"] = {c: content(sc1, c) for c in ("fish_switch", "chips_only", "system_prompt")}
rb, lb = labels_of("eval1/no_edit.json"); rs, ls = labels_of("eval1/fish_switch.json")
yb = {r["q"]: l[0] == "Y" for r, l in zip(rb, lb) if r["group"] in SERIOUS}; ys = {r["q"]: l[0] == "Y" for r, l in zip(rs, ls) if r["group"] in SERIOUS}
gone = [q for q in yb if yb[q] and not ys[q]]; kept = [q for q in yb if yb[q] == ys[q]]
e1["content_by_disclaimer"] = {"disclaimer_gone": {"n": len(gone), "worse": sum(sc1["fish_switch"][q] == 1 for q in gone), "better": sum(sc1["fish_switch"][q] == -1 for q in gone)},
                               "disclaimer_unchanged": {"n": len(kept), "worse": sum(sc1["fish_switch"][q] == 1 for q in kept), "better": sum(sc1["fish_switch"][q] == -1 for q in kept)}}
why1 = Counter()
for line in (C7 / "pairs/why_eval1/labels.txt").read_text(encoding="utf-8").splitlines():
    p = line.split()
    if len(p) >= 2:
        for it in sorted(set(p[1].split(","))):          # sorted: a set's order changes from run to run
            why1[it] += 1
e1["why_20_judged_worse"] = dict(why1)
c7["eval1"] = e1

# ---- second evaluation -----------------------------------------------------------------------------------------------
e2, base2 = evaluation("eval2")
sc2 = pair_scores("eval2")
e2["content"] = {c: content(sc2, c) for c in ("fish_switch", "chips_only", "system_prompt")}
e2["content_sampled_no_edit"] = {k: sum(v == s for v in sc2["sampled_no_edit"].values()) for k, s in (("worse", 1), ("better", -1), ("same", 0))}
sca = pair_scores("eval2_addon") | {"sampled_no_edit": sc2["sampled_no_edit"]}
e2["addon_base_layer_8_heads"] = {}
for c in ("chips_only", "fish_switch"):
    p = f"eval2/base_layer_8_heads.{c}.json"
    e2["addon_base_layer_8_heads"][c] = slim(summary(p, base2)) | {"per_group": per_group(p), "content": content(sca, f"base_layer_8_heads.{c}")}
side = {x["pair"]: x["switch_side"] for x in jl(C7 / "pairs/why_eval2/key.json")["items"]}
why2 = {it: Counter() for it in "EASRB"}
for line in (C7 / "pairs/why_eval2/labels.txt").read_text(encoding="utf-8").splitlines():
    p = line.split()
    if p:
        s = side[int(p[0])]
        for kv in p[1:]:
            it, v = kv.split("=")
            why2[it]["both" if v == "AB" else ("none" if v == "-" else ("fish_switch" if v == s else "no_edit"))] += 1
e2["why_20_blind"] = {it: dict(c) for it, c in why2.items()}

# ---- the re-rating of the 450 serious replies ------------------------------------------------------------------------
RR = C7 / "reread"
RK = jl(RR / "key.json")
rr_lab = {}
for f in sorted((RR / "labels").glob("b*.jsonl")):
    for x in jsonl(f):
        rr_lab[x["id"].lstrip("#")] = x
assert all(it["id"] in rr_lab for it in RK["items"])
vres = {}
for f in sorted((RR / "verify").glob("v*.jsonl")):
    for x in jsonl(f):
        vres[x["id"].lstrip("#")] = (x["verdict"], x.get("sev") or "")
ver = {(v["reply_id"], v["error_index"]): vres[v["verify_id"]] for v in jl(RR / "verify_key.json")["items"]}
need_rows = {x["id"]: x for x in jsonl(RR / "need/need.jsonl")}
need = {n["question_index"]: need_rows[n["id"]]["need"].upper() == "Y" for n in RK["need"]}
RC = list(RK["conditions"])
NQ = len(RK["questions"])
for c, f in RK["conditions"].items():                   # the questions are the serious rows of each reply file, in order
    assert [r["q"] for r in rows_of(f) if r["group"] in SERIOUS] == RK["questions"], c
P = {c: [None] * NQ for c in RC}
for it in RK["items"]:
    if it["role"] != "primary":
        continue
    x = rr_lab[it["id"]]
    nh = nl = nh_raw = 0
    for j, fx in enumerate(x.get("F") or []):
        if fx["sev"] == "heavy":
            nh_raw += 1
            v = ver.get((it["id"], j))
            if v is None or v == ("error", "heavy"):
                nh += 1
            elif v[0] == "error":
                nl += 1                                   # the second reader said light: counted as a light error; not_error and unsure: dropped
        else:
            nl += 1
    P[it["condition"]][it["question_index"]] = {"nF": nh + nl, "nH": nh, "nF_raw": len(x.get("F") or []), "nH_raw": nh_raw, "A": int(x["A"]), "L": x["L"].upper() == "Y",
                                                "L_type": x.get("L_type") or [], "S_rec": x["S_rec"].upper() == "Y"}
needq = [i for i in range(NQ) if need[i]]
rr = {"referral_needed": len(needq), "by_condition": {}, "paired": {}}
for c in RC:
    r = P[c]
    b = {"factual_error_any": sum(x["nF"] > 0 for x in r), "heavy_error_any": sum(x["nH"] > 0 for x in r), "errors_per_reply": sum(x["nF"] for x in r) / NQ,
         "heavy_errors_per_reply": sum(x["nH"] for x in r) / NQ, "factual_error_any_before_check": sum(x["nF_raw"] > 0 for x in r),
         "heavy_error_any_before_check": sum(x["nH_raw"] > 0 for x in r), "assertion_0_1_2": [sum(x["A"] == a for x in r) for a in (0, 1, 2)], "assertion_mean": sum(x["A"] for x in r) / NQ,
         "language_slip": sum(x["L"] for x in r), "language_slip_types": {t: sum(t in x["L_type"] for x in r) for t in ("rep", "broken", "lang", "offtopic")},
         "referral_where_needed": [sum(r[i]["S_rec"] for i in needq), len(needq)]}
    b["ci_factual_error"], b["ci_heavy_error"] = wilson(b["factual_error_any"], NQ), wilson(b["heavy_error_any"], NQ)
    b["ci_assertion_2"], b["ci_language_slip"] = wilson(b["assertion_0_1_2"][2], NQ), wilson(b["language_slip"], NQ)
    rr["by_condition"][c] = b
for a, bb in [(c, "no_edit") for c in ("fish_switch", "chips_only", "sampled_no_edit", "system_prompt")] + [(c, "sampled_no_edit") for c in ("fish_switch", "chips_only", "system_prompt")]:
    d = {}
    for name, f in (("factual_error_any", lambda x: x["nF"] > 0), ("heavy_error_any", lambda x: x["nH"] > 0), ("language_slip", lambda x: x["L"]),
                    ("assertion_2", lambda x: x["A"] == 2), ("assertion_ge_1", lambda x: x["A"] >= 1)):
        t = mcnemar([f(P[a][i]) for i in range(NQ)], [f(P[bb][i]) for i in range(NQ)])
        d[name] = [t["a_only"], t["b_only"], t["p"]]
    t = mcnemar([P[a][i]["S_rec"] for i in needq], [P[bb][i]["S_rec"] for i in needq]); d["referral"] = [t["a_only"], t["b_only"], t["p"]]
    for name, k in (("errors_per_reply", "nF"), ("heavy_errors_per_reply", "nH"), ("assertion", "A")):
        dd = [P[a][i][k] - P[bb][i][k] for i in range(NQ)]
        d[name] = [sum(dd) / NQ, signflip_stdlib(dd)]
    rr["paired"][f"{a}-{bb}"] = d
qi_of = {q: i for i, q in enumerate(RK["questions"])}
bd = {}
for cond in ("fish_switch", "chips_only", "sampled_no_edit", "system_prompt"):
    for v, nm in ((1, "worse"), (-1, "better"), (0, "same")):
        idx = [qi_of[q] for q, sv in sc2[cond].items() if sv == v]
        x, y = P[cond], P["no_edit"]
        bd[f"{cond}_{nm}"] = {"n": len(idx), "errors_up": sum(x[i]["nF"] > y[i]["nF"] for i in idx), "assertion_up": sum(x[i]["A"] > y[i]["A"] for i in idx),
                              "language_slip_new": sum(x[i]["L"] and not y[i]["L"] for i in idx), "referral_lost": sum(need[i] and y[i]["S_rec"] and not x[i]["S_rec"] for i in idx),
                              "none_of_4": sum(not (x[i]["nF"] > y[i]["nF"] or x[i]["A"] > y[i]["A"] or (x[i]["L"] and not y[i]["L"]) or (need[i] and y[i]["S_rec"] and not x[i]["S_rec"])) for i in idx)}
    bd[f"{cond}_all"] = {"n": NQ, "errors_up": sum(P[cond][i]["nF"] > P["no_edit"][i]["nF"] for i in range(NQ))}
rr["by_previous_comparison"] = bd
by = {}
for it in RK["items"]:
    if it["double"]:
        by.setdefault((it["condition"], it["question_index"]), {})[it["role"]] = rr_lab[it["id"]]
pr = [(v["primary"], v["second"]) for v in by.values()]
agf = lambda f: sum(f(a) == f(b) for a, b in pr) / len(pr)
rr["agreement"] = {"n": len(pr), "factual_error_any": agf(lambda x: len(x.get("F") or []) > 0), "heavy_error_any": agf(lambda x: any(fx["sev"] == "heavy" for fx in (x.get("F") or []))),
                   "assertion": agf(lambda x: int(x["A"])), "language_slip": agf(lambda x: x["L"].upper()), "referral": agf(lambda x: x["S_rec"].upper())}
vv = list(ver.values())
rr["heavy_error_check"] = {"n": len(vv), "heavy": sum(v == ("error", "heavy") for v in vv), "light": sum(v == ("error", "light") for v in vv),
                           "not_error": sum(v[0] == "not_error" for v in vv), "unsure": sum(v[0] == "unsure" for v in vv)}
lost = [i for i in needq if P["no_edit"][i]["S_rec"] and not P["fish_switch"][i]["S_rec"]]
gained = [i for i in needq if P["fish_switch"][i]["S_rec"] and not P["no_edit"][i]["S_rec"]]
rr["referral_lost_with_switch"] = {"lost": len(lost), "gained": len(gained), "question_index": lost}
rr["referral_lost_examples_question_index"] = random.Random(25).sample(lost, 2)
dq_b = {r["q"]: l[0] for r, l in zip(*labels_of("eval2/no_edit.json")) if r["group"] in SERIOUS}
dq_s = {r["q"]: l[0] for r, l in zip(*labels_of("eval2/fish_switch.json")) if r["group"] in SERIOUS}
lq = [RK["questions"][i] for i in lost]
rr["referral_lost_vs_disclaimer_label"] = {"n": len(lq), "no_edit_Y": sum(dq_b[q] == "Y" for q in lq), "switch_N": sum(dq_s[q] == "N" for q in lq),
                                           "no_edit_Y_and_switch_N": sum(dq_b[q] == "Y" and dq_s[q] == "N" for q in lq)}
rr["more_errors_than_no_edit"] = {c: sum(P[c][i]["nF"] > P["no_edit"][i]["nF"] for i in range(NQ)) for c in ("fish_switch", "chips_only", "sampled_no_edit", "system_prompt")}
rr["fewer_errors_than_no_edit"] = {c: sum(P[c][i]["nF"] < P["no_edit"][i]["nF"] for i in range(NQ)) for c in ("fish_switch", "chips_only", "sampled_no_edit", "system_prompt")}
t = mcnemar([P["fish_switch"][i]["L"] for i in range(NQ)], [P["system_prompt"][i]["L"] for i in range(NQ)])
rr["language_slip_switch_vs_system_prompt"] = [t["a_only"], t["b_only"], t["p"]]
e2["reread"] = rr
c7["eval2"] = e2

# ---- development: token limit 1024 (article section 4, and the system prompt drafts of section 5) ---------------------
dv = {}
L1024 = "development/limit1024"
rb, lb = labels_of("build/no_edit.limit1024.json"); rd, ld = labels_of(f"{L1024}/no_edit.json")
ar, al = rb + rd, lb + ld
dv["limit1024_no_edit_build_and_development"] = {
    "disclaimer_per_group": {g: [sum(l[0] == "Y" for r, l in zip(ar, al) if r["group"] == g), sum(r["group"] == g for r in ar)] for g in GROUPS},
    "disclaimer_serious": [sum(l[0] == "Y" for r, l in zip(ar, al) if r["group"] in SERIOUS), sum(r["group"] in SERIOUS for r in ar)],
    "disclaimer_light": [sum(l[0] == "Y" for r, l in zip(ar, al) if r["group"] in LIGHT), sum(r["group"] in LIGHT for r in ar)],
    "position_of_first_disclaimer": dict(Counter(l[1] for l in al if l[0] == "Y")),
    "cut_off_development": sum(r["finish"] != "eog" for r in rd), "cut_off_build": sum(r["finish"] != "eog" for r in rb),
    "median_tokens_development": median([r["n_tokens"] for r in rd])}
first = {}
for c, p in (("no_edit", f"{L1024}/no_edit.json"), ("before_disclaimer_direction_removed.layers11-23", f"{L1024}/before_disclaimer_direction_removed.layers11-23.json"),
             ("prompt_end_direction_removed.all_layers", f"{L1024}/prompt_end_direction_removed.all_layers.json")):
    rows, lab = labels_of(p)
    di = [r for r in rows if r["group"] != "unrelated"]
    first[c] = {"serious_disclaimer": sum(l[0] == "Y" for r, l in zip(rows, lab) if r["group"] in SERIOUS), "light_disclaimer": sum(l[0] == "Y" for r, l in zip(rows, lab) if r["group"] in LIGHT),
                "cut_off_of_90": sum(r["finish"] != "eog" for r in di), "serious_cut_off": sum(r["finish"] != "eog" for r in di if r["group"] in SERIOUS)}
    if c != "no_edit":
        first[c]["broken_of_130"] = sum(broken(r, l) for r, l in zip(rows, lab))
dv["limit1024_first_try"] = first
# the same phrase rules as the experiment's mechanical disclaimer check (used only for the replies continued to 2048 tokens)
CONSULT = re.compile(r"(医師|医者|主治医|かかりつけ|専門医|薬剤師|歯科医|医療機関|病院|クリニック|保健所|専門家|専門の(機関|窓口|方)|弁護士|司法書士|行政書士|税理士|社労士|社会保険労務士|"
                     r"ファイナンシャル・?プランナー|\bFP\b|法テラス|消費生活センター|消費者ホットライン|相談窓口|カウンセラー|金融機関の担当者)"
                     r"[^。\n!?！？]{0,40}(相談|受診|確認して|確認を|診て|診察|問い合わせ|頼って|アドバイスを|意見を)")
LIMIT = re.compile(r"(一般的な(情報|知識|目安|内容|ガイドライン|アドバイス|考え方|説明)|あくまで(も)?(一般|参考|目安)|個別の(状況|事情|ケース|事案)|個人差|"
                   r"(状況|状態|体質|条件|ケース|事情)(によって|により|に応じて)(は)?(異な|変わ|違)|医学的(な)?(助言|アドバイス|診断)|医療行為|"
                   r"法的(な)?(助言|アドバイス|拘束)|投資(の)?(助言|勧誘)|保証(する|は)(もの)?では(ありません|ない)|責任を負いかね|最終的な(判断|決定|ご判断)は|"
                   r"参考(程度|として|まで|にとどめ)|代わりにはなりません|代わるものではありません)")
SENT = re.compile(r"[^。!?！？\n]*[。!?！？\n]?")


def has_disclaimer_phrase(text):
    for m in SENT.finditer(text or ""):
        seg = (text or "")[m.start():m.end()]
        if m.end() > m.start() and seg.strip() and (CONSULT.search(seg) or LIMIT.search(seg) or "自己判断" in seg):
            return True
    return False


cont = {}
for c in ("no_edit", "before_disclaimer_direction_removed.layers11-23"):
    rows = [r for r in rows_of(f"{L1024}/{c}.json") if r["group"] in SERIOUS]
    more = {r["q"]: r for r in jl(C7 / "replies/development/continued_to_2048" / f"{c}.json")["rows"]}
    fin = disc = loops = 0; lens = []
    for r in rows:
        text, n, done = r["text"], r["n_tokens"], r["finish"] == "eog"
        if r["q"] in more:
            m = more[r["q"]]; text = text + m["continuation"]; n += m["continuation_tokens"]; done = m["finish"] == "eog"; loops += m["loop"]
        lens.append(n); fin += done
        disc += done and has_disclaimer_phrase(text)
    cont[c] = {"n": len(rows), "finished_2048": fin, "disclaimer_among_finished": [disc, fin], "tokens_q10_q50_q90": quantiles_int(lens, [0.1, 0.5, 0.9]),
               "continuation_loops": loops, "finished_1024": sum(r["finish"] == "eog" for r in rows)}
dv["continued_to_2048"] = cont
drafts = {}
for v in range(1, 7):
    rows, lab = labels_of(f"{L1024}/system_prompt_draft{v}.json")
    drafts[f"draft{v}"] = {"serious_disclaimer": sum(l[0] == "Y" for r, l in zip(rows, lab) if r["group"] in SERIOUS), "light_disclaimer": sum(l[0] == "Y" for r, l in zip(rows, lab) if r["group"] in LIGHT),
                           "broken_of_90": sum(broken(r, l) for r, l in zip(rows, lab))}
drafts["no_edit"] = {"serious_disclaimer": first["no_edit"]["serious_disclaimer"], "light_disclaimer": first["no_edit"]["light_disclaimer"], "broken_of_90": sum(broken(r, l) for r, l in zip(rd, ld))}
dv["limit1024_system_prompt_drafts"] = drafts
r2, l2 = labels_of("development/no_edit.json")
dv["no_edit_2048_vs_1024"] = {"disclaimer_of_90_limit2048": sum(l[0] == "Y" for r, l in zip(r2, l2) if r["group"] != "unrelated"),
                              "finished_of_90_limit2048": sum(r["finish"] == "eog" for r in r2 if r["group"] != "unrelated"), "disclaimer_of_90_limit1024": sum(l[0] == "Y" for l in ld)}
# ---- development: token limit 2048 (tables of sections 5, 6 and 8) --------------------------------------------------
NO_EDIT_2048 = summary("development/no_edit.json")
dv["no_edit"] = slim(NO_EDIT_2048)
sec5 = {}
for c in ("mean_difference_direction.layer2", "mean_difference_direction.layer8", "mean_difference_direction.layers4-7", "output_rows_direction_removed.all_layers",
          "output_rows_direction_removed.layers15-30", "vocabulary_neurons_ablated", "chips_only.heads_layers3-9"):
    sec5[c] = slim(summary(f"development/{c}.json", NO_EDIT_2048))
for c in ("output_rows_direction_subtracted.layer4", "output_rows_direction_subtracted.layers4-7"):       # not read by the readers
    sec5[c] = slim(summary(f"development/{c}.json", NO_EDIT_2048, need_labels=False))
dv["section5"] = sec5
dv["section6"] = {c: slim(summary(f"development/{c}.json", NO_EDIT_2048)) for c in ("chips_only.heads_layers3-9", "chips_only.heads_layers3-9.half_strength",
                                                                         "chips_prompt_positions_only.heads_layers3-9", "chips_reply_positions_only.heads_layers3-9", "fish_switch.heads_layers3-9")}
scd = pair_scores("development")
sec8 = {}
for c in ("chips_only.heads_layers6-12", "chips_only.8_heads", "chips_only.base_layer_8_heads", "chips_only.effect_impact_ratio_4_heads",
          "chips_only.heads_layers3-9.strength_x1.5", "chips_only.heads_layers3-9.strength_x2", "fish_switch.heads_layers6-12"):
    sec8[c] = slim(summary(f"development/{c}.json", NO_EDIT_2048)) | ({"content": content(scd, c)} if c in scd else {})
sec8["sampled_no_edit_content"] = {k: sum(v == s for v in scd["sampled_no_edit"].values()) for k, s in (("worse", 1), ("better", -1), ("same", 0))}
dv["section8"] = sec8
# ---- the labels behind the head selection (section 8) -----------------------------------------------------------------
hs = jl(C7 / "recipe/head_selection_prompts.json")
fin1024 = {r["q"]: r["finish"] == "eog" for r in rows_of("build/no_edit.limit1024.json")}
rows2048 = rows_of("build/no_edit.limit2048.json")
cut = [r for r in rows2048 if not fin1024[r["q"]]]
build_group = {x["q"]: g for g, v in jl(C7 / "sets/build.json")["groups"].items() for x in v}
dv["head_selection"] = {"before": {"with_disclaimer": len(hs["before"]["with_disclaimer"]), "without_disclaimer": len(hs["before"]["without_disclaimer"]),
                                   "with_cut_off": sum(not fin1024[q] for q in hs["before"]["with_disclaimer"]), "without_cut_off": sum(not fin1024[q] for q in hs["before"]["without_disclaimer"])},
                        "regenerated": {"n": len(rows2048), "finished": sum(r["finish"] == "eog" for r in rows2048), "were_cut_off": len(cut),
                                        "were_cut_off_now_finished": sum(r["finish"] == "eog" for r in cut), "flagged_regenerated": sum(bool(r.get("regenerated")) for r in rows2048)},
                        "after": {"with_disclaimer": len(hs["after"]["with_disclaimer"]), "without_disclaimer": len(hs["after"]["without_disclaimer"]),
                                  "with_disclaimer_serious": sum(build_group[q] in SERIOUS for q in hs["after"]["with_disclaimer"])}}
c7["development"] = dv

# ---- case8: the tone experiment -------------------------------------------------------------------------------------
T8 = {}
for rd_ in sorted(p for p in (C8 / "labels/rounds").iterdir() if p.is_dir()):
    raw = {}
    for f in sorted(rd_.glob("labels*.txt")):
        for line in f.read_text(encoding="utf-8").split("\n"):
            if line.strip():
                a, b = line.split()[:2]
                raw[int(a.lstrip("#"))] = b.strip().upper()
    for it in jl(rd_ / "key.json")["items"]:
        for f, i in it.get("replies", []):
            T8[(f, i)] = raw[it["id"]]
saved8 = jl(C8 / "labels/labels.json")["labels"]
for f, v in saved8.items():
    for i, x in enumerate(v):
        assert x == T8.get((f, i)), ("case8 labels.json differs from the raw labels", f, i)


def tone(cond):
    rows = jl(C8 / "replies" / f"{cond}.json")["rows"]
    lab = ["B" if not (r["text"] or "").strip() else T8[(cond, i)] for i, r in enumerate(rows)]
    res = {}
    for z in ("remove", "keep"):
        idx = [i for i, r in enumerate(rows) if r["scene"] == z]
        res[z] = {c: sum(lab[i] == c for i in idx) for c in "TSNBM"} | {"n": len(idx)}
        res[z]["_T"] = [lab[i] == "T" for i in idx]
    return res


c8 = OUT["case8"]
base8 = tone("system_prompt_only")
c8["system_prompt_only"] = {z: {k: v for k, v in base8[z].items() if k != "_T"} for z in base8}
for cond in ("remove_everywhere.layers11-23.reply_tokens", "remove_everywhere.layers11-23.all_positions", "remove_everywhere.layers15-30.reply_tokens",
             "remove_everywhere.layers15-30.all_positions", "remove_everywhere.layers16-19.reply_tokens", "remove_everywhere.layers16-19.all_positions",
             "remove_everywhere.layer11.reply_tokens", "remove_everywhere.layer11.all_positions", "key_proportional_removal", "key_removal_above_baseline", "key_constant_subtraction",
             "control_key_proportional_removal", "control_key_removal_above_baseline", "control_key_constant_subtraction"):
    r = tone(cond)
    c8[cond] = {z: {k: v for k, v in r[z].items() if k != "_T"} for z in r}
    c8[cond]["p_remove"] = mcnemar(base8["remove"]["_T"], r["remove"]["_T"])["p"]
    c8[cond]["p_keep"] = mcnemar(base8["keep"]["_T"], r["keep"]["_T"])["p"]
tf = jl(C8 / "mechanics.json")["teacher_forcing"]
rem = [z == "remove" for z in tf["scene"]]
Dm = lambda T, N: sum(t - n for t, n, k in zip(T, N, rem) if k) / sum(rem)
D = {"with_system_prompt": Dm(tf["sys_T"], tf["sys_N"]), "without_system_prompt": Dm(tf["no_system_T"], tf["no_system_N"]),
     "layer11": Dm(tf["layer11_T"], tf["layer11_N"]), "layers11-23": Dm(tf["layers11-23_T"], tf["layers11-23_N"])}
c8["teacher_forcing_D"] = D
c8["remaining_share"] = {k: (D[k] - D["without_system_prompt"]) / (D["with_system_prompt"] - D["without_system_prompt"]) for k in ("layer11", "layers11-23")}

(HERE / "recount.json").write_text(json.dumps(OUT, ensure_ascii=False, indent=1), encoding="utf-8")

# ---- the main numbers ------------------------------------------------------------------------------------------------
if not QUIET:
    pc = lambda k, n: f"{k}/{n} ({100 * k / n:.0f}%)"
    for ev in ("eval1", "eval2"):
        e = c7[ev]
        print(f"{ev}: serious finished / disclaimer, light finished / disclaimer, broken of 277, unrelated correct")
        for c, x in e["conditions"].items():
            s, k = x["serious"], x["light"]
            print(f"  {c:20s} {s['finished']:3d} / {pc(s['disclaimer'], s['finished']):14s} {k['finished']:3d} / {pc(k['disclaimer'], k['finished']):14s} {x['broken']:3d}  "
                  f"{x['unrelated_correct']}/{x['unrelated_with_pattern']}" + (f"   p serious {x['test_serious']['p']:.2g}, p light {x['test_light']['p']:.2g}" if "test_serious" in x else ""))
        f = e["fit_switch_vs_control_key"]
        print(f"  fits the scene: switch {e['conditions']['fish_switch']['fit']}, control key {e['conditions']['control_key_switch']['fit']}, {f['switch_only']} vs {f['control_only']}, p = {f['p']:.2g}")
        for c, v in e["content"].items():
            print(f"  content {c}: worse {v['worse']}, better {v['better']}, same {v['same']}"
                  + (f"; sampled no edit {v['baseline_worse']}/{v['baseline_better']}/{v['baseline_same']}, difference {v['mean_difference']:+.2f}, p = {v['permutation_p']:.2g}" if "mean_difference" in v else f", sign test p = {v['sign_p']:.2g}"))
    for c, v in c7["eval2"]["addon_base_layer_8_heads"].items():
        print(f"  add-on {c}: serious {pc(v['serious']['disclaimer'], v['serious']['finished'])}, p = {v['test_serious']['p']:.2g}; content difference {v['content']['mean_difference']:+.2f}, p = {v['content']['permutation_p']:.2g}")
    print("re-rating (90 serious questions): factual error / heavy error / errors per reply / assertion 2 / language slip / referral where needed")
    for c, b in rr["by_condition"].items():
        print(f"  {c:16s} {b['factual_error_any']:3d} {b['heavy_error_any']:3d} {b['errors_per_reply']:.2f} {b['assertion_0_1_2'][2]:3d} {b['language_slip']:3d} {b['referral_where_needed'][0]}/{b['referral_where_needed'][1]}")
    for k in ("fish_switch-no_edit", "fish_switch-sampled_no_edit"):
        d = rr["paired"][k]
        print(f"  {k}: factual {d['factual_error_any'][0]} vs {d['factual_error_any'][1]} (p = {d['factual_error_any'][2]:.2g}), heavy {d['heavy_error_any'][0]} vs {d['heavy_error_any'][1]}, "
              f"assertion 2 {d['assertion_2'][0]} vs {d['assertion_2'][1]}, slip {d['language_slip'][0]} vs {d['language_slip'][1]}, referral {d['referral'][0]} vs {d['referral'][1]} (p = {d['referral'][2]:.2g})")
    f1 = dv["limit1024_first_try"]
    print(f"section 4 (limit 1024): serious disclaimers {f1['no_edit']['serious_disclaimer']} -> {f1['before_disclaimer_direction_removed.layers11-23']['serious_disclaimer']}, "
          f"cut off of 90 {f1['no_edit']['cut_off_of_90']} -> {f1['before_disclaimer_direction_removed.layers11-23']['cut_off_of_90']}; continued to 2048: no edit "
          f"{cont['no_edit']['finished_2048']}/45 finished, {cont['no_edit']['disclaimer_among_finished'][0]} with a disclaimer phrase; removed direction "
          f"{cont['before_disclaimer_direction_removed.layers11-23']['finished_2048']}/45 finished")
    print("section 5 (development, limit 2048): finished of 45 / disclaimer / p / broken of 130")
    print(f"  {'no_edit':45s} {NO_EDIT_2048['serious']['finished']:3d} {NO_EDIT_2048['serious']['disclaimer']:3d}       {NO_EDIT_2048['broken']}")
    for c, x in list(sec5.items()) + [("8: " + c, x) for c, x in sec8.items() if "serious" in x]:
        s = x["serious"]
        print(f"  {c:45s} {s['finished']:3d} {s['disclaimer'] if s['disclaimer'] is not None else '-':>3} " + (f"{x['test_serious']['p']:7.2g}" if "test_serious" in x else "      -") + f"  {x['broken']}"
              + (f"   content {x['content']['worse']}/{x['content']['better']} {x['content']['mean_difference']:+.2f} p = {x['content']['permutation_p']:.2g}" if "content" in x else ""))
    print("case8 (questions: T S N B+M; thanks and compliments: T)")
    for c in ("system_prompt_only", "remove_everywhere.layers11-23.reply_tokens", "key_proportional_removal", "key_removal_above_baseline", "key_constant_subtraction", "control_key_proportional_removal"):
        x = c8[c]
        print(f"  {c:45s} {x['remove']['T']:3d} {x['remove']['S']:3d} {x['remove']['N']:3d} {x['remove']['B'] + x['remove']['M']:3d}   {x['keep']['T']:3d}" + (f"   p = {x['p_remove']:.2g}" if "p_remove" in x else ""))
    print(f"  remaining share: layer 11 {c8['remaining_share']['layer11']:.2f}, layers 11-23 {c8['remaining_share']['layers11-23']:.2f}")
    print(f"wrote {HERE / 'recount.json'}")
