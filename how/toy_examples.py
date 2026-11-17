"""Worked examples 1-6 of "How CHiPS and FiSH work" (https://balaena01.github.io/fish-steering/how/).
「CHiPS と FiSH のしくみ」の例題 1〜6 の数を計算するスクリプト。

It recomputes every number of the small examples on the page (not the measured values) and prints them,
together with the tables and the step-by-step equations, in Japanese and English.
ページの例題の数(実測値は除く)を計算し直し、表と式(日本語・英語)と一緒に表示する。GPU もモデルも使わない。

Needs numpy and a clone of gguf-neuron-explorer (https://github.com/balaena01/gguf-neuron-explorer); the formulas come from
gne.keyed (projection removal), gne.keyed_ridge (least squares) and gne.nwrite (the neuron pair).
    GNE_REPO=/path/to/gguf-neuron-explorer python toy_examples.py           # all values, tables and equations
    GNE_REPO=/path/to/gguf-neuron-explorer python toy_examples.py --json    # the values as JSON
"""
import json
import math
import os
import re
import sys
from pathlib import Path

import numpy as np

GNE = Path(os.environ.get("GNE_REPO", "gguf-neuron-explorer"))
sys.path.insert(0, str(GNE))
import gne.keyed as K            # noqa: E402
import gne.keyed_ridge as RG     # noqa: E402
import gne.nwrite as NW          # noqa: E402

V = {}        # 名前 → {"v": 値, "s": 本文での書き方, "src": 出どころ}
TABLES = {}   # 名前 → markdown の表(本文にそのまま貼る)


def fmt(x, nd=2):
    """本文の書き方: 小数 nd 桁、負は「−」。−0.00 は 0.00 にする。"""
    s = f"{float(x):.{nd}f}"
    if s.startswith("-"):
        s = ("0." + "0" * nd if nd else "0") if float(s) == 0 else "−" + s[1:]
    return s


def fint(x):
    return f"{int(x):,}"


def put(name, v, s=None, src="toy", nd=2):
    if s is None:
        s = fmt(v, nd) if isinstance(v, (float, np.floating)) else (fint(v) if isinstance(v, (int, np.integer)) else str(v))
    V[name] = {"v": (v.tolist() if isinstance(v, np.ndarray) else (float(v) if isinstance(v, (float, np.floating)) else v)), "s": s, "src": src}
    return s


def vec(x, nd=2):
    return "(" + ", ".join(fmt(t, nd) for t in x) + ")"


def putv(name, x, nd=2, src="toy"):
    x = np.asarray(x, dtype=np.float64)
    V[name] = {"v": x.tolist(), "s": vec(x, nd), "src": src}
    for i, t in enumerate(x):                      # 成分も 1 つずつ(本文で単独に出すとき用)
        V[f"{name}[{i}]"] = {"v": float(t), "s": fmt(t, nd), "src": src}
    return vec(x, nd)


def table(name, head, rows):
    out = ["| " + " | ".join(head) + " |", "|" + "|".join("---" for _ in head) + "|"]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    TABLES[name] = "\n".join(out)


# ---- 式のかたまり(本文の ```math 名前 にそのまま貼る。書き方は site/build.py の math_block) ------------------------------
# 決まり: 記号だけの式 → 数を入れた式 → 結果、を 1 段ずつ。途中の掛け算は、本文に出した桁の数どうしをそのまま掛けた値
# (Decimal で正確に)を出すので、読者が電卓で同じ数を得られる。最後の値は正確な値を丸めたもので、手計算と最後の桁まで
# 同じなら「=」、違えば「≈」にする(自動で決める)。
from decimal import Decimal as Dec   # noqa: E402

EQS = {}


def eq(name, *lines):
    EQS[name] = "\n".join(lines)


def dd(x, nd):
    """本文に nd 桁で出した数を、丸めたあとの値のまま計算に使う。"""
    return Dec(fmt(x, nd).replace("−", "-"))


def ts(d_, keep=2):
    """Decimal を本文の書き方にする。末尾の 0 は keep 桁まで削る。負は「−」。"""
    s_ = format(d_, "f")
    if "." in s_:
        ip, fp = s_.split(".")
        fp = fp.rstrip("0").ljust(keep, "0")
        s_ = ip + "." + fp if fp else ip
    s_ = s_.replace("-", "−")
    return s_.lstrip("−") if Dec(s_.replace("−", "-")) == 0 else s_


def pa(s_):
    """掛け算の中の負の数は括弧に入れる。"""
    return f"({s_})" if s_.startswith("−") else s_


def col(v, nd):
    return "[" + "; ".join(fmt(t, nd) for t in v) + "]"


def rowv(v, nd):
    return "[" + ", ".join(fmt(t, nd) for t in v) + "]"


def mat(M_, nd):
    return "[" + "; ".join(", ".join(fmt(t, nd) for t in r_) for r_ in M_) + "]"


def sumstr(ds_):
    out = ts(ds_[0])
    for t in ds_[1:]:
        s_ = ts(t)
        out += f" − {s_[1:]}" if s_.startswith("−") else f" + {s_}"
    return out


def dotparts(a, b, nda, ndb):
    """a·b の手計算: (「a1×b1 + a2×b2 + …」, 「積1 + 積2 + …」, 和)。"""
    A_, B_ = [dd(t, nda) for t in a], [dd(t, ndb) for t in b]
    pr = [p * q for p, q in zip(A_, B_)]
    return " + ".join(f"{pa(fmt(p, nda))}×{pa(fmt(q, ndb))}" for p, q in zip(a, b)), sumstr(pr), sum(pr)


def fin(hand, true, nd):
    """最後の値: 手計算(Decimal)が正確な値の表示と同じなら「= x」、違えば「= 手計算 ≈ x」。"""
    t_ = fmt(true, nd)
    return f"= {t_}" if Dec(t_.replace("−", "-")) == hand else f"= {ts(hand)} ≈ {t_}"


def vrel(hand, true, nd):
    """ベクトルの段の記号: 手計算を nd 桁に丸めたものが、正確な値の表示と全部同じなら「=」、違えば「≈」。"""
    return "=" if all(fmt(float(h_), nd) == fmt(t_, nd) for h_, t_ in zip(hand, true)) else "≈"


def dotline(lhs, a, b, nda, ndb, true, nd, note=""):
    """内積 1 本を 1 行で: lhs = a1×b1 + … = 積の和 = 結果。"""
    s1, s2, hs = dotparts(a, b, nda, ndb)
    return f"{lhs} = {s1} = {s2} {fin(hs, true, nd)}" + (f"  ← {note}" if note else "")


# =====================================================================================================================
# 例題 1: 層は足し算をする(3 次元)
# =====================================================================================================================
x0 = np.array([0.4, -0.1, -0.1])
head_v = np.array([0.5, 0.6, 0.4])          # ヘッドの書き込み(例題 3 でも使う)
mlp_m = np.array([0.1, 0.2, 0.1])
x1 = x0 + head_v + mlp_m
putv("e1.x0", x0, 1); putv("e1.v", head_v, 1); putv("e1.m", mlp_m, 1); putv("e1.x1", x1, 1)
eq("e1_add", f"x = x₀ + v + (MLP の出力) = {col(x0, 1)} + {col(head_v, 1)} + {col(mlp_m, 1)}",
   f"= {col(x1, 1)}  ← 成分ごとに足す")

# =====================================================================================================================
# 例題 2: 向き(3 次元)。指示あり 3 つ・なし 3 つの状態の平均の差。内積で成分を測る
# =====================================================================================================================
A = np.array([[1.1, 0.6, 0.5], [0.9, 0.4, 0.8], [1.0, 0.5, 0.5]])
B = np.array([[1.2, 0.1, 0.3], [0.9, 0.3, 0.1], [0.9, 0.2, 0.2]])
mA, mB = A.mean(0), B.mean(0)
r = mA - mB
rn = float(np.linalg.norm(r))
rhat = r / rn
for i, a in enumerate(A):
    putv(f"e2.A{i + 1}", a, 1)
for i, b in enumerate(B):
    putv(f"e2.B{i + 1}", b, 1)
putv("e2.mA", mA, 1); putv("e2.mB", mB, 1); putv("e2.r", r, 1); put("e2.r_len", rn, nd=1); putv("e2.rhat", rhat, 1)
put("e2.r_len2", float(r @ r))                                                     # 0.25(= 0.3² + 0.4²)
x = x1.copy()                                                                      # 例題 1 で足し算してできた状態
xb = np.array([1.1, 0.2, 0.1])
put("e2.x_dot", float(x @ rhat)); put("e2.xb_dot", float(xb @ rhat)); putv("e2.xb", xb, 1)
put("e2.mA_dot", float(mA @ rhat)); put("e2.mB_dot", float(mB @ rhat))
put("e2.x_dot_t1", float(x[1] * rhat[1])); put("e2.x_dot_t2", float(x[2] * rhat[2]))
along = (x @ rhat) * rhat
rest = x - along
putv("e2.along", along, 3); putv("e2.rest", rest, 3); put("e2.rest_dot", float(rest @ rhat), nd=3)
# なぜ差の方向か: A 自身の方向 Â で測って引く場合と、差の方向 r̂ で測って引く場合を比べる
nA, nB = float(np.linalg.norm(mA)), float(np.linalg.norm(mB))
Ahat = mA / nA
putv("e2.Ahat", Ahat, 2); put("e2.A_len", nA); put("e2.B_len", nB)
put("e2.A_dot_Ahat", float(mA @ Ahat)); put("e2.B_dot_Ahat", float(mB @ Ahat))
putv("e2.A_minus_Ahat", mA - (mA @ Ahat) * Ahat, 2); putv("e2.B_minus_Ahat", mB - (mB @ Ahat) * Ahat, 2)
putv("e2.A_minus_rhat", mA - (mA @ rhat) * rhat, 3); putv("e2.B_minus_rhat", mB - (mB @ rhat) * rhat, 3)
put("e2.AA", float(mA @ mA)); put("e2.AB", float(mA @ mB)); put("e2.A_dot_r", float(mA @ r))
assert abs(float(mA @ r) - (float(mA @ mA) - float(mA @ mB))) < 1e-12
# 例題 2 の図の座標: 横 = r̂ 方向の成分、縦 = r̂ に直交する成分の長さ(各ベクトルの長さと r̂ との角度はこの 2 つで正確に決まる)
for nm_, vv in (("A", mA), ("B", mB), ("x", x1), ("x2", xb)):
    pj = float(vv @ rhat)
    put(f"e2.fig.{nm_}.proj", pj); put(f"e2.fig.{nm_}.orth", float(np.linalg.norm(vv - pj * rhat)))
assert np.allclose(mA - (mA @ rhat) * rhat, mB - (mB @ rhat) * rhat)      # A と B の直交成分は同じ(同じ高さに並ぶ)
table("e2_why", ["測る方向", "A との内積", "B との内積", "引いたあとの A", "引いたあとの B"],
      [["A 自身の方向 Â", fmt(mA @ Ahat), fmt(mB @ Ahat), vec(mA - (mA @ Ahat) * Ahat, 2), vec(mB - (mB @ Ahat) * Ahat, 2)],
       ["差の方向 r̂", fmt(mA @ rhat), fmt(mB @ rhat), vec(mA - (mA @ rhat) * rhat, 3), vec(mB - (mB @ rhat) * rhat, 3)]])
# (表 e2_dot は式のかたまりに置き換えた)
# ---- 例題 2 の式 ----------------------------------------------------------------------------------------------------
eq("e2_mean",
   f"A = ({' + '.join(col(a_, 1) for a_ in A)}) ÷ 3",
   f"= {col(A.sum(0), 1)} ÷ 3  ← 成分ごとに足す",
   f"= {col(mA, 1)}  ← プロンプトありの平均",
   f"B = ({' + '.join(col(b_, 1) for b_ in B)}) ÷ 3",
   f"= {col(B.sum(0), 1)} ÷ 3",
   f"= {col(mB, 1)}  ← プロンプトなしの平均",
   f"r = A − B = {col(mA, 1)} − {col(mB, 1)}",
   f"= {col(r, 1)}  ← 1 番目の成分(どちらも 1.0)は消える")
eq("e2_norm",
   "‖r‖ = √(r·r)",
   f"= √({fmt(r[0], 1)}² + {fmt(r[1], 1)}² + {fmt(r[2], 1)}²)",
   f"= √{fmt(r @ r)} = {fmt(rn, 1)}",
   f"r̂ = r ÷ ‖r‖ = {col(r, 1)} ÷ {fmt(rn, 1)}",
   f"= {col(rhat, 1)}  ← 長さ 1 のベクトル(単位ベクトル)")
_s1, _s2, _hs = dotparts(x1, rhat, 1, 1)
eq("e2_dot",
   "x·r̂ = (1 番目どうしの積) + (2 番目どうしの積) + (3 番目どうしの積)",
   f"= {_s1}  ← x = {vec(x1, 1)}、r̂ = {vec(rhat, 1)}",
   f"= {_s2}",
   f"{fin(_hs, x1 @ rhat, 2)}",
   dotline("x₂·r̂", xb, rhat, 1, 1, xb @ rhat, 2, f"x₂ = {vec(xb, 1)}"),
   dotline("A·r̂", mA, rhat, 1, 1, mA @ rhat, 2, "プロンプトありの平均"),
   dotline("B·r̂", mB, rhat, 1, 1, mB @ rhat, 2, "プロンプトなしの平均"))
_al = dd(x1 @ rhat, 2)
_alv = [_al * dd(t, 1) for t in rhat]
_rsv = [dd(a_, 1) - b_ for a_, b_ in zip(x1, _alv)]
_c1, _c2, _ch = dotparts(rhat, rest, 1, 3)
eq("e2_proj",
   f"(x·r̂) × r̂ = {fmt(x1 @ rhat)} × {col(rhat, 1)}",
   f"{vrel(_alv, along, 3)} {col(along, 3)}  ← r̂ への射影",
   f"x − (x·r̂) × r̂ = {col(x1, 1)} − {col(along, 3)}",
   f"{vrel(_rsv, rest, 3)} {col(rest, 3)}  ← 直交成分",
   f"r̂·(直交成分) = {_c1}",
   f"= {_c2} {fin(_ch, rest @ rhat, 3)}  ← 内積が 0 なので、r̂ と直交している")
_lines = []
for nm_, vv in (("A", mA), ("B", mB)):
    pj = vv @ rhat
    sub_ = pj * rhat
    _lines += [f"{nm_} − ({nm_}·r̂) × r̂ = {col(vv, 1)} − {fmt(pj)} × {col(rhat, 1)}",
               f"= {col(vv, 1)} − {col(sub_, 3)}",
               f"= {col(vv - sub_, 3)}" + ("  ← A と同じ" if nm_ == "B" else "")]
eq("e2_why_r", *_lines)
_Ah3 = [dd(t, 1) / dd(nA, 3) for t in mA]
_b1, _b2, _bh = dotparts(mB, Ahat, 1, 3)
_bsub = [dd(mB @ Ahat, 3) * dd(t, 3) for t in Ahat]
eq("e2_why_A",
   f"A·A = {fmt(mA[0], 1)}² + {fmt(mA[1], 1)}² + {fmt(mA[2], 1)}² = {fmt(mA @ mA)}",
   f"A·B = {dotparts(mA, mB, 1, 1)[0]} = {fmt(mA @ mB)}",
   f"‖A‖ = √(A·A) = √{fmt(mA @ mA)} = {fmt(nA, 3)}",
   f"Â = A ÷ ‖A‖ = {col(mA, 1)} ÷ {fmt(nA, 3)}",
   f"{vrel(_Ah3, Ahat, 3)} {col(Ahat, 3)}",
   f"A·Â = A·A ÷ ‖A‖ = ‖A‖ = {fmt(nA, 3)}  ← 表の 1.27(Â = A ÷ ‖A‖ で、A·A = ‖A‖² なので)",
   f"B·Â = {_b1}",
   f"= {_b2} {fin(_bh, mB @ Ahat, 3)}  ← B のほとんどが「A 方向の成分」になる",
   f"B − (B·Â) × Â = {col(mB, 1)} − {fmt(mB @ Ahat, 3)} × {col(Ahat, 3)}",
   f"{vrel(_bsub, (mB @ Ahat) * Ahat, 3)} {col(mB, 1)} − {col((mB @ Ahat) * Ahat, 3)}",
   f"= {col(mB - (mB @ Ahat) * Ahat, 3)}  ← A を同じように引くと 0 になるので、引いたあとの A と B は別のベクトル",
   "A·r̂ = A·r ÷ ‖r‖  ← r̂ = r ÷ ‖r‖",
   "= (A·A − A·B) ÷ ‖r‖  ← r = A − B で、内積は引き算に分けられる",
   f"= ({fmt(mA @ mA)} − {fmt(mA @ mB)}) ÷ {fmt(rn, 1)} = {fmt(mA @ r)} ÷ {fmt(rn, 1)} = {fmt(mA @ rhat)}")

# =====================================================================================================================
# 例題 3: CHiPS。ヘッドの書き込み v = W_h x_h の、r̂ に沿った成分だけを (1 − s) 倍にする
# =====================================================================================================================
Wh = np.array([[0.5, 0.0], [0.2, 0.4], [0.1, 0.3]])
xh_on, xh_off = np.array([1.0, 1.0]), np.array([1.0, -0.5])
s = 2.0
v_on, v_off = Wh @ xh_on, Wh @ xh_off
assert np.allclose(v_on, head_v)
rows3 = []
for tag, v in (("on", v_on), ("off", v_off)):
    c = float(rhat @ v)
    v2 = v - s * c * rhat
    put(f"e3.{tag}.c", c); putv(f"e3.{tag}.v", v, 2); putv(f"e3.{tag}.sc_r", s * c * rhat, 3); putv(f"e3.{tag}.v2", v2, 3)
    put(f"e3.{tag}.c2", float(rhat @ v2)); put(f"e3.{tag}.sc", s * c, nd=2)
    put(f"e3.{tag}.change", float(np.linalg.norm(v2 - v)))
    restv = v - c * rhat
    putv(f"e3.{tag}.rest", restv, 3)
    rows3.append((tag, v, c, s * c, v2, float(rhat @ v2)))
put("e3.s", s, nd=0)
# (表 e3_steps は式のかたまりに置き換えた)
# 重みの書き換えと LoRA
rW = rhat @ Wh                                   # r̂ᵀ W_h(1 × 2)
Arow = s * rW                                    # LoRA の A
Bcol = -rhat                                     # LoRA の B
Wh2 = Wh + np.outer(Bcol, Arow)
assert np.allclose(Wh2, (np.eye(3) - s * np.outer(rhat, rhat)) @ Wh)
assert np.allclose(Wh2 @ xh_on, v_on - s * (rhat @ v_on) * rhat)
putv("e3.rW", rW, 2); putv("e3.A", Arow, 2); putv("e3.B", Bcol, 1)
for i in range(3):
    putv(f"e3.Wh.row{i}", Wh[i], 1); putv(f"e3.Wh2.row{i}", Wh2[i], 3); putv(f"e3.BA.row{i}", np.outer(Bcol, Arow)[i], 3)
putv("e3.xh_on", xh_on, 1); putv("e3.xh_off", xh_off, 1)
putv("e3.Wh.col0", Wh[:, 0], 1); putv("e3.Wh.col1", Wh[:, 1], 1)
put("e3.BA10", float(np.outer(Bcol, Arow)[1, 0]))                  # 本文の「−0.6 × 0.40 = −0.24」
put("e4.e", float(np.e), nd=3)
putv("e3.Wh2x", Wh2 @ xh_on, 3)
# (表 e3_lora は式のかたまりに置き換えた)
# 丸ごと倍率(gain)と比べる: 同じだけ向きの成分を動かすと、それ以外も動く
k_gain = rows3[0][5] / rows3[0][2]               # 向きの成分を c → c′ にする倍率(ここでは −1)
v_gain = k_gain * v_on
put("e3.k_gain", k_gain, nd=0)
put("e3.rest_len", float(np.linalg.norm(v_on - rows3[0][2] * rhat))); put("e3.rest_len3", float(np.linalg.norm(v_on - rows3[0][2] * rhat)), nd=3)
put("e3.gain_rest_change", float(np.linalg.norm((v_gain - (rhat @ v_gain) * rhat) - (v_on - rows3[0][2] * rhat))))
put("e3.x_dot_after", float(x1 @ rhat + rhat @ (rows3[0][4] - rows3[0][1])))       # 層を出たときの射影の値(MLP の書く量は変えないとして)
put("e3.chips_rest_change", float(np.linalg.norm((rows3[0][4] - (rhat @ rows3[0][4]) * rhat) - (v_on - rows3[0][2] * rhat))))
table("e3_factor", ["s", "r̂ 方向の成分が何倍になるか", "意味"],
      [["0", "× 1", "変えない"], ["1", "× 0", "消す"], ["2", "× (−1)", "反転する"], ["3", "× (−2)", "反転して 2 倍にする"], ["−1", "× 2", "2 倍に強める"]])

# ---- 例題 3 の式 ----------------------------------------------------------------------------------------------------
for tag, v in (("on", v_on), ("off", v_off)):
    p_ = float(rhat @ v)
    s1_, s2_, hs_ = dotparts(rhat, v, 1, 2)
    sp = s * p_
    sub_ = sp * rhat
    v2 = v - sub_
    q1_, q2_, qh_ = dotparts(rhat, v2, 1, 3)
    hsub = [dd(sp, 2) * dd(t, 1) for t in rhat]
    hv2 = [dd(a_, 2) - b_ for a_, b_ in zip(v, hsub)]
    lines_ = [f"p = r̂·v = {s1_}  ← v = {vec(v)}",
              f"= {s2_} {fin(hs_, p_, 2)}  ← r̂ 方向の成分",
              f"s × p = {fmt(s, 0)} × {pa(fmt(p_))} = {fmt(sp)}",
              "v′ = v − (s × p) × r̂",
              f"= {col(v, 2)} − {pa(fmt(sp))} × {col(rhat, 1)}",
              f"{vrel(hsub, sub_, 3)} {col(v, 2)} − {col(sub_, 3)}",
              f"{vrel(hv2, v2, 3)} {col(v2, 3)}"]
    _ro = v - p_ * rhat
    _orth_line = f"‖v − p × r̂‖ = ‖{col(_ro, 3)}‖ = √({' + '.join(pa(fmt(t, 3)) + '²' for t in _ro)}) {fin((sum(dd(t, 3) ** 2 for t in _ro)).sqrt().quantize(Dec('0.0001')), float(np.linalg.norm(_ro)), 3)}  ← 直交成分の長さ(v′ でも同じ。図の縦)"
    if tag == "on":
        lines_ += [f"p′ = r̂·v′ = {q1_}", f"= {q2_} {fin(qh_, rhat @ v2, 2)}  ← 成分が反転した", _orth_line,
                   f"‖v′ − v‖ = ‖−(s × p) × r̂‖ = |s × p| × ‖r̂‖ = {fmt(sp)} × 1 = {fmt(sp)}  ← 変化の大きさ。長さなので符号を取る(|…| は符号を取った値)"]
    else:
        lines_ += [f"p′ = r̂·v′ = {q1_}", f"= {q2_} {fin(qh_, rhat @ v2, 2)}", _orth_line,
                   f"‖v′ − v‖ = |s × p| × ‖r̂‖ = |{fmt(sp)}| × 1 = {fmt(abs(sp))}  ← 成分がもともと 0 に近いので、ほとんど変わらない"]
    eq(f"e3_{tag}", *lines_)
_rows = "; ".join(f"{fmt(Wh[i, 0], 1)}×{fmt(xh_on[0], 1)} + {fmt(Wh[i, 1], 1)}×{fmt(xh_on[1], 1)}" for i in range(3))
eq("e3_head",
   f"v = W_i x_i = {mat(Wh, 1)} {col(xh_on, 1)}",
   f"= [{_rows}]  ← 各行と x_i の内積を、上から並べる",
   f"= {col(Wh @ xh_on, 2)}")
_rW = "[" + ", ".join(dotparts(rhat, Wh[:, j], 1, 1)[0] for j in range(2)) + "]"
_out = "[" + "; ".join(", ".join(f"{fmt(rhat[i], 1)}×{fmt(rW[j])}" for j in range(2)) for i in range(3)) + "]"
_RR = np.outer(rhat, rW)
_DW = -s * _RR
_W2r = "; ".join(", ".join(f"{pa(fmt(Wh2[i, j], 3))}×{fmt(xh_on[j], 1)}" for j in range(2)).replace(", ", " + ") for i in range(3))
eq("e3_weight",
   f"r̂ᵀ W_i = {rowv(rhat, 1)} {mat(Wh, 1)}",
   f"= {_rW}",
   f"= {rowv(rW, 2)}  ← W_i の各列と r̂ の内積(ᵀ は転置。縦のベクトルを横にする)",
   f"r̂ (r̂ᵀ W_i) = {col(rhat, 1)} {rowv(rW, 2)}",
   f"= {_out}",
   f"= {mat(_RR, 3)}  ← 縦のベクトル × 横のベクトル(外積)",
   f"ΔW_i = −s × r̂ (r̂ᵀ W_i) = −{fmt(s, 0)} × {mat(_RR, 3)}",
   f"= {mat(_DW, 3)}  ← 差分",
   f"W_i′ = W_i + ΔW_i = {mat(Wh, 1)} + {mat(_DW, 3)}",
   f"= {mat(Wh2, 3)}  ← 新しい重み",
   f"# 確かめ: 新しい重みで、振る舞いが出ている入力 x_i = {vec(xh_on, 1)} を計算する",
   f"W_i′ x_i = {mat(Wh2, 3)} {col(xh_on, 1)}",
   f"= [{_W2r}]",
   f"= {col(Wh2 @ xh_on, 3)}  ← 上の v′ と同じ")
eq("e3_why",
   "W_i′ x_i = (W_i − s × r̂ (r̂ᵀ W_i)) x_i",
   "= W_i x_i − s × r̂ (r̂ᵀ W_i x_i)  ← 括弧の位置を変える(掛ける順番はそのまま)。行列の掛け算は、並びを変えなければ、どこから先に計算しても結果が同じ(結合法則)",
   "= v − s × r̂ (r̂ᵀ v)  ← W_i x_i = v",
   "= v − s × (r̂·v) × r̂  ← r̂ᵀ v は数 1 つで、r̂ と v の内積",
   f"# 例題の数で: r̂ᵀ W_i x_i = {rowv(rW, 2)} {col(xh_on, 1)} = {dotparts(rW, xh_on, 2, 1)[0]} = {fmt(rW @ xh_on)} で、r̂·v = {fmt(rhat @ v_on)} と同じ")
eq("e3_lora",
   f"B = −r̂ = {col(Bcol, 1)}",
   f"A = s × r̂ᵀ W_i = {fmt(s, 0)} × {rowv(rW, 2)} = {rowv(Arow, 2)}",
   f"B A = {col(Bcol, 1)} {rowv(Arow, 2)}",
   f"= {mat(np.outer(Bcol, Arow), 3)} = ΔW_i  ← 上の差分と同じ")

# =====================================================================================================================
# 例題 4: ゲートつきの MLP のニューロン。silu と、2 個で 1 つのスイッチ(gne.nwrite の式そのまま)
# =====================================================================================================================
S_CAP, CA, CB = NW.S_CAP, NW.CAP_DEFAULT[0], NW.CAP_DEFAULT[1]
put("e4.s", S_CAP, nd=0); put("e4.a", CA, nd=1); put("e4.b", CB, nd=1); put("e4.den", S_CAP * (CB - CA), nd=1)
zs = [-4, -2, -1, 0, 1, 2, 4, 8]
table("e4_silu", ["z"] + [fmt(z, 0) for z in zs],
      [["SiLU(z) = z ÷ (1 + e^(−z))"] + [fmt(NW.silu(z)) for z in zs],
       ["ReLU: max(0, z)"] + [fmt(max(0, z)) for z in zs]])
for z in zs:
    put(f"e4.silu({z})", float(NW.silu(z)))
rhos = [0.2, 0.4, 0.5, 0.6, 0.8, 0.9, 1.3]
rows4 = []
for p in rhos:
    z1, z2 = S_CAP * (p - CA), S_CAP * (p - CB)
    a1, a2 = float(NW.silu(z1)), float(NW.silu(z2))
    amt = float(NW.amount_cap(p))
    assert abs(amt - (a1 - a2) / (S_CAP * (CB - CA))) < 1e-12
    ramp = min(max((p - CA) / (CB - CA), 0.0), 1.0)
    rows4.append([fmt(p, 1), fmt(z1, 1), fmt(a1), fmt(z2, 1), fmt(a2), fmt(a1 - a2), f"**{fmt(amt)}**", fmt(ramp)])
    put(f"e4.amt({p})", amt); put(f"e4.ramp({p})", ramp); put(f"e4.z1({p})", z1, nd=1); put(f"e4.z2({p})", z2, nd=1)
    put(f"e4.a1({p})", a1); put(f"e4.a2({p})", a2)
table("e4_switch", ["ρ", "16(ρ − 0.4)", "SiLU", "16(ρ − 0.8)", "SiLU", "差", "g = 差 ÷ 6.4", "ReLU で近似した g"], rows4)
put("e4.dip_min", float(min(NW.amount_cap(p) for p in np.linspace(0, 0.4, 401))))   # 0.4 より下の小さな負の谷
_ps = np.linspace(0.4, 1.6, 120001)
_gs = np.array([NW.amount_cap(p_) for p_ in _ps])
put("e4.gmax", float(_gs.max()), nd=3); put("e4.gmax_rho", float(_ps[_gs.argmax()]), nd=2)
put("e4.dip_rho", float(min(np.linspace(0, 0.4, 401), key=lambda p: NW.amount_cap(p))))

# ---- 例題 4 の式(ニューロン 1 個の計算と、2 個 1 組の係数 g) -------------------------------------------------------------
h4 = np.array([1.0, 0.5, -0.2])                  # MLP への入力
wg4, wu4, wd4 = np.array([0.0, 2.0, -1.0]), np.array([0.5, 1.0, 1.0]), np.array([0.2, 0.0, -0.4])
zg4, zu4 = float(wg4 @ h4), float(wu4 @ h4)
act4 = float(NW.silu(zg4)) * zu4
putv("e4n.h", h4, 1); putv("e4n.wg", wg4, 1); putv("e4n.wu", wu4, 1); putv("e4n.wd", wd4, 1)
put("e4n.zg", zg4); put("e4n.zu", zu4); put("e4n.silu", float(NW.silu(zg4)), nd=3); put("e4n.act", act4, nd=3); putv("e4n.out", act4 * wd4, 3)
_g1, _g2, _gh = dotparts(wg4, h4, 1, 1)
_u1, _u2, _uh = dotparts(wu4, h4, 1, 1)
_hs = dd(NW.silu(zg4), 3) * dd(zu4, 2)
_ho = [dd(act4, 3) * dd(t, 1) for t in wd4]
eq("e4_neuron",
   "活性化値 = SiLU(w_{gate}·h) × (w_{up}·h)",
   f"= SiLU({_g1}) × ({_u1})",
   f"= SiLU({_g2}) × ({_u2})",
   f"= SiLU({fmt(zg4)}) × {fmt(zu4)}",
   f"= {fmt(NW.silu(zg4), 3)} × {fmt(zu4)}  ← すぐ下の行で SiLU を計算",
   f"{fin(_hs, act4, 3)}",
   f"SiLU({fmt(zg4)}) = {fmt(zg4)} ÷ (1 + e^{{−{fmt(zg4)}}}) = {fmt(zg4)} ÷ (1 + {fmt(math.exp(-zg4), 3)}) = {fmt(NW.silu(zg4), 3)}  ← e^{{−1.20}} は約 {fmt(math.exp(-zg4), 3)}",
   f"加えるベクトル = 活性化値 × w_{{down}} = {fmt(act4, 3)} × {col(wd4, 1)}",
   f"{vrel(_ho, act4 * wd4, 3)} {col(act4 * wd4, 3)}")
eq("e4_gate",
   "w_{gate,1}·h = 16 × (κ − 0.4 × κ_c)·h",
   "= 16 × (κ·h − 0.4 × κ_c·h)  ← 内積は、足し算と数倍に分けて計算できる",
   "≈ 16 × (ρ − 0.4)  ← κ·h = ρ、κ_c·h ≈ 1",
   "w_{up,1}·h = κ_c·h ≈ 1",
   "活性化値_1 ≈ SiLU(16 × (ρ − 0.4)) × 1  ← ニューロン 2 は 0.4 が 0.8 になる",
   "加えるベクトル = 活性化値_1 × (d ÷ 6.4) + 活性化値_2 × (−d ÷ 6.4)",
   "= (活性化値_1 − 活性化値_2) ÷ 6.4 × d",
   "= g × d")
_p = 0.6
_z1, _z2 = S_CAP * (_p - CA), S_CAP * (_p - CB)
_a1, _a2 = float(NW.silu(_z1)), float(NW.silu(_z2))
_hd = dd(_a1, 2) - dd(_a2, 2)
eq("e4_one",
   f"ゲート入力_1 = 16 × ({fmt(_p, 1)} − 0.4) = {fmt(_z1, 1)}  ← ρ = {fmt(_p, 1)} の場合",
   f"SiLU({fmt(_z1, 1)}) = {fmt(_z1, 1)} ÷ (1 + e^{{−{fmt(_z1, 1)}}}) = {fmt(_z1, 1)} ÷ (1 + {fmt(math.exp(-_z1), 3)}) = {fmt(_a1)}",
   f"ゲート入力_2 = 16 × ({fmt(_p, 1)} − 0.8) = {fmt(_z2, 1)}",
   f"SiLU({fmt(_z2, 1)}) = {fmt(_z2, 1)} ÷ (1 + e^{{{fmt(-_z2, 1)}}}) = {fmt(_z2, 1)} ÷ (1 + {fmt(math.exp(-_z2), 2)}) = {fmt(_a2)}",
   f"g = (SiLU(ゲート入力_1) − SiLU(ゲート入力_2)) ÷ 6.4",
   f"= ({fmt(_a1)} − {pa(fmt(_a2))}) ÷ 6.4",
   f"= {ts(_hd)} ÷ 6.4 {fin((_hd / Dec('6.4')).quantize(Dec('0.0001')), NW.amount_cap(_p), 2)}")

# =====================================================================================================================
# 例題 5: 鍵の作り方(3 次元、位置 12 個)。1 番目の数はいつも 1(どの状態にも共通する成分の代わり)
#   狙う場面 = お礼(書きたい位置 = 返事の位置 1)。書きたくない = 同じ返事の位置 0、近況の報告の返事、質問の返事。
#   長い返事の後ろの位置は、何個かを選んで「代表する位置の数」の重み ω を付ける(gne の行の間引きと同じ考え)。
# =====================================================================================================================
GROUPS = ["T", "N", "Q"]
GNAME = {"T": "お礼", "N": "近況報告", "Q": "質問"}
ROWS5 = [  # (群, 返事の番号, 位置, 2 番目の数, 3 番目の数, ω)
    ("T", 0, 0, 0.2, 0.0, 1), ("T", 0, 1, -0.2, 0.9, 1),
    ("T", 1, 0, 0.4, -0.1, 1), ("T", 1, 1, 0.0, 0.7, 1),
    ("N", 0, 0, 0.3, 0.1, 1), ("N", 0, 1, 1.0, 0.5, 1), ("N", 0, 2, 0.1, 0.0, 3),
    ("Q", 0, 0, 0.1, 0.1, 1), ("Q", 0, 1, -0.1, 0.0, 1), ("Q", 0, 2, 0.5, -0.1, 10), ("Q", 0, 3, -0.4, 0.0, 10), ("Q", 0, 4, 0.0, -0.1, 10),
]
LBL = ["お礼 1・位置 0", "お礼 1・位置 1", "お礼 2・位置 0", "お礼 2・位置 1", "近況報告・位置 0", "近況報告・位置 1", "近況報告・位置 2 以降",
       "質問・位置 0", "質問・位置 1", "質問・位置 2 以降 a", "質問・位置 2 以降 b", "質問・位置 2 以降 c"]
V["e5.rows"] = {"v": [list(r_) for r_ in ROWS5], "s": "", "src": "toy"}     # 図(make_figures.py)が読む
table("e5_data", ["位置", "隠れ状態 h", "サンプル重み"],
      [[(f"**{LBL[i]}(対象)**" if (g == "T" and p_ == 1) else LBL[i]), f"(1.0, {fmt(a_, 1)}, {fmt(b_, 1)})", fint(w_)] for i, (g, rr, p_, a_, b_, w_) in enumerate(ROWS5)])
WKEY = (1, 2)            # 書きたい区間 = 位置 1(本物では 位置 1〜3 にあたる)
qids = {}
for g, rr, *_ in ROWS5:
    qids.setdefault((g, rr), len(qids))
X5 = np.array([[1.0, a, b] for g, rr, p, a, b, w in ROWS5])
om5 = np.array([w for *_, w in ROWS5], dtype=np.float64)
q5 = np.array([qids[(g, rr)] for g, rr, *_ in ROWS5])
pos5 = np.array([p for g, rr, p, *_ in ROWS5])
qg5 = np.zeros(len(qids), dtype=int)
for (g, rr), i in qids.items():
    qg5[i] = GROUPS.index(g)
TABLE5 = {"q": q5, "pos": pos5, "om": om5, "q_group": qg5}
inW = (pos5 >= WKEY[0]) & (pos5 < WKEY[1])
isT = np.array([g == "T" for g, *_ in ROWS5])
W5 = isT & inW
U5 = ~W5
put("e5.q_tail_positions", int(sum(w for g, rr, p, aa, bb, w in ROWS5 if g == "Q" and p >= 2)))
put("e5.n_tail_positions", int(sum(w for g, rr, p, aa, bb, w in ROWS5 if g == "N" and p >= 2)))
put("e5.n_rows", int(len(ROWS5))); put("e5.n_W", int(W5.sum())); put("e5.n_U", int(U5.sum()))

# --- 前の作り方(gne の既定、key_fit = mean): μ = 書きたい位置の、返事ごとの平均の平均。
#     Q の行 = 書きたくない側の、返事ごとの平均(お礼の返事は位置 1 以外、ほかの群は全部の位置)+ ほかの群の返事の位置 0。
#     Q = その行が張る向き(特異値の二乗の和の 99% まで)。k = μ − QQᵀμ、κ = k ÷ (μ·k)。
wmean = lambda m: (X5[m] * om5[m, None]).sum(0) / om5[m].sum()
EA = [wmean((q5 == i) & W5) for k, i in qids.items() if k[0] == "T"]
mu = np.mean(EA, 0)
Qrows, Qlab = [], []
for k, i in qids.items():
    m = q5 == i
    if k[0] == "T":
        Qrows.append(wmean(m & ~inW)); Qlab.append(f"{GNAME['T']} {k[1] + 1} の位置 1 以外の平均")
    else:
        Qrows.append(wmean(m)); Qlab.append(f"{GNAME[k[0]]}の応答の平均(重みつき)")
        Qrows.append(wmean(m & (pos5 == 0))); Qlab.append(f"{GNAME[k[0]]}の応答の位置 0")
Qrows = np.array(Qrows)
sv = np.linalg.svd(Qrows, compute_uv=False)
energy = sv ** 2
frac = np.cumsum(energy) / energy.sum()
Qb = K.orth_basis(Qrows, energy=0.99)
k_old = mu - Qb @ (Qb.T @ mu)
kap_old, info_old = K.make_key(mu, Qb)
assert np.allclose(kap_old, k_old / (mu @ k_old))
putv("e5.mu", mu, 2)
for i, (row, lab) in enumerate(zip(Qrows, Qlab)):
    putv(f"e5.Qrow{i}", row, 2)
put("e5.Q_rank", int(Qb.shape[1]))
for i, (e_, f_) in enumerate(zip(energy, frac)):
    put(f"e5.energy{i}", float(e_), nd=3); put(f"e5.energy_frac{i}", float(e_ / energy.sum() * 100), nd=1); put(f"e5.energy_cum{i}", float(f_ * 100), nd=1)
for j_ in range(Qb.shape[1]):
    q_ = Qb[:, j_] * (1 if Qb[np.flatnonzero(np.abs(Qb[:, j_]) > 1e-9)[0], j_] > 0 else -1)   # 向きの符号を見やすくそろえる(QQᵀ は変わらない)
    putv(f"e5.q{j_ + 1}", q_, 2); put(f"e5.mu_q{j_ + 1}", float(mu @ q_))
putv("e5.QQmu", Qb @ (Qb.T @ mu), 2)
putv("e5.k_old", k_old, 2); putv("e5.kap_old", kap_old, 2); put("e5.kn_old", float(info_old["kn"]))
table("e5_qrows", ["Q のもとになるベクトル(対象外の位置を応答ごとにまとめたもの)", "ベクトル"], [[lab, vec(row, 2)] for lab, row in zip(Qlab, Qrows)])

# --- 最小二乗の鍵(gne.keyed_ridge.fit をそのまま呼ぶ)。c は gne と同じ決め方(質問単位の分割。ここでは狙う場面の返事が 2 つなので 2 つに分ける)
fit_cv = RG.fit(lambda L: X5, [0], TABLE5, [WKEY], c=None, weights="cells", group_names=GROUPS)
C5 = float(fit_cv["info"]["c"])
put("e5.c", C5, nd=1); put("e5.folds", int(fit_cv["info"]["folds"]))
fits = {wn: RG.fit(lambda L: X5, [0], TABLE5, [WKEY], c=C5, weights=wn, group_names=GROUPS) for wn in ("uniform", "cells")}
kap = {"old": kap_old, "uniform": fits["uniform"]["kappa"][0][0], "cells": fits["cells"]["kappa"][0][0]}
for nm in ("uniform", "cells"):
    putv(f"e5.kap_{nm}", kap[nm], 2)
    put(f"e5.tau_{nm}", float(fits[nm]["tau"][0][0]), nd=3)
put("e5.n_cells", int(fit_cv["info"]["cells"][0]))
# 重みを、gne の決まりどおりに自分でも付けて、同じ鍵になるかを確かめる(本文の重みの説明が正しいかの確かめ)
bins = RG.bins_of([WKEY]); bidx = RG._bin_index(pos5, bins)
cell = qg5[q5] * len(bins) + bidx
wts = {}
for nm in ("uniform", "cells"):
    w = np.zeros(len(ROWS5))
    w[W5] = om5[W5] / om5[W5].sum()
    if nm == "uniform":
        w[U5] = om5[U5] / om5[U5].sum()
    else:
        cs_ = np.unique(cell[U5])
        for cc in cs_:
            m = U5 & (cell == cc)
            w[m] = om5[m] / om5[m].sum() / len(cs_)
    G = (X5 * w[:, None]).T @ X5
    b = (X5[W5] * w[W5, None]).sum(0)
    lam = C5 * np.trace(G) / 3
    kh = np.linalg.solve(G + lam * np.eye(3), b)
    km = kh / (kh @ b)
    assert np.allclose(km, kap[nm], atol=1e-10), (nm, km, kap[nm])
    wts[nm] = w
    put(f"e5.lambda_{nm}", lam, nd=3)
    putv(f"e5.khat_{nm}", kh, 2)
    put(f"e5.khat_m_{nm}", float(kh @ b), nd=2)
put("e5.Uw_total", float(om5[U5].sum()), s=fint(om5[U5].sum()))
for i in range(len(ROWS5)):
    for nm in ("uniform", "cells"):
        put(f"e5.w_{nm}{i}", float(wts[nm][i] * 100), nd=1)
# 書きたくない側の、ますごとの重みの割合(%)
cells_show = [("T", "0"), ("N", "0"), ("N", "1"), ("N", "2+"), ("Q", "0"), ("Q", "1"), ("Q", "2+")]
cellrows = []
for g, bn in cells_show:
    m = U5 & np.array([gg == g for gg, *_ in ROWS5]) & ((pos5 == int(bn)) if bn != "2+" else (pos5 >= 2))
    wu, wc = wts["uniform"][m].sum() * 100, wts["cells"][m].sum() * 100
    put(f"e5.cellw_uniform.{g}{bn}", float(wu), nd=1); put(f"e5.cellw_cells.{g}{bn}", float(wc), nd=1)
    cellrows.append([f"{GNAME[g]}・位置 {bn.replace('2+', '2 以降')}", fint(m.sum()), fint(om5[m].sum()), fmt(wu, 1) + "%", fmt(wc, 1) + "%"])
table("e5_cells", ["対象外の位置のセル", "サンプル数", "サンプル重みの合計", "位置ごとに均等", "セルごとに均等"], cellrows)
# 反応の表
resp = {nm: X5 @ kap[nm] for nm in kap}
rows5 = []
for i, (g, rr, p, a, b, w) in enumerate(ROWS5):
    cells_ = [fmt(resp[nm][i]) for nm in ("old", "uniform", "cells")]
    if i == 5:
        cells_ = [f"**{c}**" for c in cells_]
    lab_ = f"**{LBL[i]}(対象)**" if W5[i] else LBL[i]
    rows5.append([lab_, f"({fmt(a, 1)}, {fmt(b, 1)})", fint(w)] + cells_)
    for nm in ("old", "uniform", "cells"):
        put(f"e5.resp_{nm}{i}", float(resp[nm][i]))
table("e5_resp", ["位置", "(2 番目, 3 番目の成分)", "サンプル重み", "射影除去法", "最小二乗(位置ごとに均等)", "最小二乗(セルごとに均等)"], rows5)
table("e5_resp_short", ["位置", "(2 番目, 3 番目の成分)", "射影除去法", "最小二乗(位置ごとに均等)", "最小二乗(セルごとに均等)"],
      [[r_[0], r_[1]] + r_[3:] for k_, r_ in enumerate(rows5) if k_ in (1, 3, 5, 10)])
for nm in ("old", "uniform", "cells"):
    oth = [i for i in range(len(ROWS5)) if U5[i] and i != 5]
    put(f"e5.maxU_other_{nm}", float(max(resp[nm][oth]))); put(f"e5.minU_{nm}", float(min(resp[nm][U5])))
    put(f"e5.minW_{nm}", float(min(resp[nm][W5]))); put(f"e5.maxW_{nm}", float(max(resp[nm][W5])))
    put(f"e5.amt_N1_{nm}", float(NW.amount_cap(resp[nm][5]))); put(f"e5.amt_Wmin_{nm}", float(NW.amount_cap(min(resp[nm][W5]))))
    put(f"e5.len_{nm}", float(np.linalg.norm(kap[nm])))
put("e5.wu_Qtail", float(wts["uniform"][9]), nd=3)
put("e5.N1_share_uniform", float(wts["uniform"][5] * 100), nd=1); put("e5.N1_share_cells", float(wts["cells"][5] * 100), nd=1)
# 正則化の強さ c を変えると(組み合わせごとに同じ重み)
lrows = []
for c in RG.CS:
    f = RG.fit(lambda L: X5, [0], TABLE5, [WKEY], c=c, weights="cells", group_names=GROUPS)
    kk = f["kappa"][0][0]
    rr_ = X5 @ kk
    oth = [i for i in range(len(ROWS5)) if U5[i] and i != 5]
    lrows.append([fmt(c, 2).rstrip("0").rstrip(".") if c < 1 else fint(c), vec(kk, 2), fmt(np.linalg.norm(kk)), fmt(min(rr_[W5])), fmt(rr_[5]), fmt(max(rr_[oth]))])
    put(f"e5.c{c}.len", float(np.linalg.norm(kk))); put(f"e5.c{c}.N1", float(rr_[5])); put(f"e5.c{c}.maxU", float(max(rr_[oth]))); put(f"e5.c{c}.minW", float(min(rr_[W5])))
table("e5_lambda", ["c", "キー κ", "長さ", "対象の位置での出力(2 つのうち小さいほう)", "近況報告・位置 1 での出力", "ほかの対象外の位置での出力(最大)"], lrows)
put("e5.cv_score_c", float(fit_cv["info"]["score"][list(RG.CS).index(C5)]), nd=3)

# --- できた鍵(組み合わせごとに同じ重み)を、ニューロン 2 個の 3 つの重みに入れる。d は例題 2 の差 r(向きそのままの大きさ)
k1 = np.array([1.0, 0.0, 0.0])            # どの位置でもほぼ 1 を返す鍵。例題では 1 番目の数がいつも 1 なので、ちょうど 1
kc = kap["cells"]
d = r.copy()
g1, g2 = S_CAP * (kc - CA * k1), S_CAP * (kc - CB * k1)
o1, o2 = d / (S_CAP * (CB - CA)), -d / (S_CAP * (CB - CA))
putv("e5n.kc3", kc, 3); putv("e5n.k1", k1, 0); putv("e5n.g1", g1, 2); putv("e5n.g2", g2, 2); putv("e5n.o1", o1, 4); putv("e5n.o2", o2, 4); putv("e5n.d", d, 1)
nrows = []
for i in (1, 5, 9):
    h = X5[i]
    pg1, pg2, pu = float(g1 @ h), float(g2 @ h), float(k1 @ h)
    a1, a2 = float(NW.silu(pg1)) * pu, float(NW.silu(pg2)) * pu
    out = a1 * o1 + a2 * o2
    amt = float(out @ d / (d @ d))
    assert abs(amt - float(NW.amount_cap(kc @ h))) < 1e-12
    nrows.append([LBL[i], vec(h, 1), fmt(kc @ h), fmt(pg1), fmt(a1), fmt(pg2), fmt(a2), vec(out, 3), f"**{fmt(amt)}** × d"])
    put(f"e5n.amt{i}", amt); put(f"e5n.rho{i}", float(kc @ h)); put(f"e5n.pg1_{i}", pg1); put(f"e5n.pg2_{i}", pg2)
    put(f"e5n.a1_{i}", a1); put(f"e5n.a2_{i}", a2); putv(f"e5n.out{i}", out, 3)
    put(f"e5n.diff{i}", float(round(a1, 2) - round(a2, 2)))          # 本文の「11.82 − 5.40 = 6.42」(表の 2 桁どうしの差)
table("e5_neuron", ["位置", "h", "κ·h", "ゲート入力 1", "活性化値 1", "ゲート入力 2", "活性化値 2", "加えるベクトル", "g"], nrows)

# ---- 例題 5 の式 ----------------------------------------------------------------------------------------------------
def gchain(rho, nd_r, nd_g, rho_txt=None):
    """係数 g を、キーの出力 ρ から 1 段ずつ計算する行(第 4 節の式)。"""
    z1_, z2_ = S_CAP * (rho - CA), S_CAP * (rho - CB)
    a1_, a2_ = float(NW.silu(z1_)), float(NW.silu(z2_))
    r_ = dd(rho, nd_r)
    hz1, hz2 = Dec(16) * (r_ - Dec("0.4")), Dec(16) * (r_ - Dec("0.8"))
    sz = "=" if fmt(float(hz1)) == fmt(z1_) and fmt(float(hz2)) == fmt(z2_) else "≈"
    sa = "=" if fmt(NW.silu(float(dd(z1_, 2))), 3) == fmt(a1_, 3) and fmt(NW.silu(float(dd(z2_, 2))), 3) == fmt(a2_, 3) else "≈"
    hd = dd(a1_, 3) - dd(a2_, 3)
    rt = rho_txt or fmt(rho, nd_r)
    return [f"g = (SiLU(16 × ({rt} − 0.4)) − SiLU(16 × ({rt} − 0.8))) ÷ 6.4",
            f"{sz} (SiLU({fmt(z1_)}) − SiLU({fmt(z2_)})) ÷ 6.4",
            f"{sa} ({fmt(a1_, 3)} − {pa(fmt(a2_, 3))}) ÷ 6.4",
            f"= {ts(hd)} ÷ 6.4 {fin((hd / Dec('6.4')).quantize(Dec('0.0001')), NW.amount_cap(rho), nd_g)}"]


_T = [X5[i] for i in range(len(ROWS5)) if W5[i]]
eq("e5_mu",
   "μ = (お礼 1・位置 1 の h + お礼 2・位置 1 の h) ÷ 2  ← 対象の位置の平均",
   f"= ({col(_T[0], 1)} + {col(_T[1], 1)}) ÷ 2",
   f"= {col(_T[0] + _T[1], 1)} ÷ 2",
   f"= {col(mu, 2)}")
_nm = (q5 == qids[("N", 0)])
eq("e5_dilute",
   "近況報告の応答の平均 = (" + " + ".join(f"{fint(om5[i])} × {col(X5[i], 1)}" for i in np.flatnonzero(_nm)) + ") ÷ ("
   + " + ".join(fint(om5[i]) for i in np.flatnonzero(_nm)) + ")  ← 位置 0、位置 1、位置 2 以降(サンプル重み 3)",
   f"= {col((X5[_nm] * om5[_nm, None]).sum(0), 1)} ÷ {fint(om5[_nm].sum())}",
   f"= {col(wmean(_nm), 2)}  ← 位置 1 の 3 番目の成分 0.5 が、平均では 0.12 に薄まる")
_q = [np.array(V[f"e5.q{j}"]["v"]) for j in (1, 2)]
_Qm = np.column_stack(_q)
_qm = [float(t @ mu) for t in _q]
_qq = sum(c_ * t for c_, t in zip(_qm, _q))
_hqq = [dd(_qm[0], 3) * dd(a_, 3) + dd(_qm[1], 3) * dd(b_, 3) for a_, b_ in zip(*_q)]
_k = mu - _qq
_hk = [dd(a_, 2) - dd(b_, 3) for a_, b_ in zip(mu, _qq)]
_m1, _m2, _mh = dotparts(mu, _k, 2, 3)
_hkap = [dd(t, 3) / dd(mu @ _k, 3) for t in _k]
assert np.allclose(_k, k_old) and np.allclose(_k / (mu @ _k), kap_old)
eq("e5_proj",
   f"Q = [q_1, q_2] = {mat(_Qm, 3)}  ← 2 本の方向を列として並べる",
   f"Qᵀ = {mat(_Qm.T, 3)}  ← 転置すると q_1 と q_2 が行になる",
   f"Qᵀμ = {mat(_Qm.T, 3)} {col(mu, 2)} = [q_1·μ; q_2·μ]  ← 各行と μ の内積",
   "= [" + "; ".join(dotparts(t, mu, 3, 2)[0] for t in _q) + "]",
   f"{vrel([dotparts(t, mu, 3, 2)[2] for t in _q], _qm, 3)} {col(_qm, 3)}",
   f"Q Qᵀμ = {mat(_Qm, 3)} {col(_qm, 3)}",
   "= [" + "; ".join(f"{fmt(_Qm[i, 0], 3)}×{fmt(_qm[0], 3)} + {pa(fmt(_Qm[i, 1], 3))}×{fmt(_qm[1], 3)}" for i in range(3)) + "]  ← 各行との内積(第 3 節の決まり)",
   f"= {fmt(_qm[0], 3)} × {col(_q[0], 3)} + {fmt(_qm[1], 3)} × {col(_q[1], 3)}  ← 同じ掛け算を、列ごとにまとめ直したもの。つまり {fmt(_qm[0], 3)} × q_1 + {fmt(_qm[1], 3)} × q_2 で、μ の q_1 と q_2 への射影の和",
   f"{vrel(_hqq, _qq, 3)} {col(_qq, 3)}",
   f"k = μ − Q Qᵀμ = {col(mu, 2)} − {col(_qq, 3)}",
   f"{vrel(_hk, _k, 3)} {col(_k, 3)}  ← q_1 と q_2 の方向の成分を持たない",
   f"μ·k = {_m1}",
   f"= {_m2} {fin(_mh, mu @ _k, 3)}",
   f"κ = k ÷ (μ·k) = {col(_k, 3)} ÷ {fmt(mu @ _k, 3)}",
   f"{vrel(_hkap, kap_old, 3)} {col(kap_old, 3)}  ← μ でのキーの出力が 1 になるように割る")
_h = X5[5]
_lines = [f"# 近況報告・位置 1 の h = {vec(_h, 1)} でのキーの出力(キーは小数第 3 位まで)"]
for nm_, lab_ in (("old", "射影除去法"), ("uniform", "最小二乗・位置ごとに均等"), ("cells", "最小二乗・セルごとに均等")):
    s1_, s2_, hs_ = dotparts(kap[nm_], _h, 3, 1)
    _lines += [f"# {lab_}のキー", f"κ·h = {s1_}", f"= {s2_} {fin(hs_, resp[nm_][5], 2)}"]
eq("e5_out", *_lines)
eq("e5_g_cells", *gchain(resp["cells"][5], 4, 2))
_s1, _s2, _hs = dotparts(kap["old"], X5[5], 3, 1)
eq("e5_g_old", f"κ·h = {_s1}  ← 射影除去法のキー(小数第 3 位まで)と、近況報告・位置 1 の h = {vec(X5[5], 1)}",
   f"= {_s2} {fin(_hs, resp['old'][5], 2)}  ← キーの出力 ρ(下では 4 桁の 0.6094 を使う)", *gchain(resp["old"][5], 4, 2))
# 最小二乗の解き方(セルごとに均等な重み)
_w = wts["cells"]
_G = (X5 * _w[:, None]).T @ X5
_b = (X5[W5] * _w[W5, None]).sum(0)
_lam = C5 * np.trace(_G) / 3
_Gl = _G + _lam * np.eye(3)
_kh = np.linalg.solve(_Gl, _b)
_h1 = X5[1]
_hh = np.outer(_h1, _h1)
_hhs = "[" + "; ".join(", ".join(f"{pa(fmt(a_, 1))}×{pa(fmt(b_, 1))}" for b_ in _h1) for a_ in _h1) + "]"
_chk = [sum(dd(_Gl[i, j], 3) * dd(_kh[j], 3) for j in range(3)) for i in range(3)]
_km1, _km2, _kmh = dotparts(_kh, _b, 3, 2)
_hkap2 = [dd(t, 3) / dd(_kh @ _b, 3) for t in _kh]
assert np.allclose(_kh / (_kh @ _b), kap["cells"])
table("e5_w", ["位置", "隠れ状態 h", "目標", "w(セルごとに均等)", "w(位置ごとに均等)"],
      [[LBL[i], f"(1.0, {fmt(X5[i, 1], 1)}, {fmt(X5[i, 2], 1)})", "1" if W5[i] else "0", fmt(wts["cells"][i], 3), fmt(wts["uniform"][i], 3)] for i in range(len(ROWS5))])
put("e5.w_T", float(_w[1]), nd=1); put("e5.w_cell", 1 / 7, nd=3); put("e5.w_Qtail", float(_w[9]), nd=3); put("e5.w_T0", float(_w[0]), nd=3)
eq("e5_ls",
   f"# 1 件分の例: お礼 1・位置 1（h = {vec(_h1, 1)}、重み w = {fmt(_w[1], 1)}）",
   f"h hᵀ = {col(_h1, 1)} {rowv(_h1, 1)}",
   f"= {_hhs}",
   f"= {mat(_hh, 2)}  ← 縦のベクトル × 横のベクトル(外積)",
   f"w × h hᵀ = {fmt(_w[1], 1)} × {mat(_hh, 2)}",
   f"= {mat(_w[1] * _hh, 3)}",
   "# 12 個の位置すべてについて w × h hᵀ を作り、足し合わせる",
   f"G = Σ w × h hᵀ = {mat(_G, 3)}",
   f"b = Σ_{{対象}} w × h = {fmt(_w[1], 1)} × {col(X5[1], 1)} + {fmt(_w[3], 1)} × {col(X5[3], 1)}",
   f"= {col(_b, 2)} = m  ← 対象の位置の重みの合計が 1 なので、対象の位置の平均になる",
   "λ = c × (G の対角成分の平均)",
   f"= {fmt(C5, 1)} × ({fmt(_G[0, 0], 3)} + {fmt(_G[1, 1], 3)} + {fmt(_G[2, 2], 3)}) ÷ 3",
   fin(dd(C5, 1) * (dd(_G[0, 0], 3) + dd(_G[1, 1], 3) + dd(_G[2, 2], 3)) / 3, _lam, 3),
   f"G + λI = {mat(_Gl, 3)}  ← 対角成分に λ を足す(I は単位行列)",
   "# 解く連立方程式 (G + λI) κ̃ = b を、数で書くと",
   f"b = {col(_b, 2)} = {mat(_Gl, 3)} κ̃",
   "# これを解くと(連立 1 次方程式を解くプログラムの関数で)",
   f"κ̃ = {col(_kh, 3)}",
   "# 確かめ: 解を左辺に入れると、右辺の b に戻る",
   f"(G + λI) κ̃ = {mat(_Gl, 3)} {col(_kh, 3)}",
   "= [" + "; ".join(ts(t.quantize(Dec('0.0001'))) for t in _chk) + f"] ≈ {col(_b, 2)} = b",
   f"κ̃·m = {_km1}",
   f"= {_km2} {fin(_kmh, _kh @ _b, 3)}",
   f"κ = κ̃ ÷ (κ̃·m) = {col(_kh, 3)} ÷ {fmt(_kh @ _b, 3)}",
   f"{vrel(_hkap2, kap['cells'], 3)} {col(kap['cells'], 3)}  ← m でのキーの出力が 1 になるように割る")
assert all(fmt(float(c_), 2) == fmt(t, 2) for c_, t in zip(_chk, _b))
# できたキーをニューロンに入れる
_kc4 = kc
_gv1 = [Dec(16) * (dd(a_, 4) - Dec("0.4") * dd(b_, 0)) for a_, b_ in zip(_kc4, k1)]
_gv2 = [Dec(16) * (dd(a_, 4) - Dec("0.8") * dd(b_, 0)) for a_, b_ in zip(_kc4, k1)]
_hn = X5[1]
_z1, _z2 = float(g1 @ _hn), float(g2 @ _hn)
_n1, _n2, _nh = dotparts(g1, _hn, 2, 1)
_p1, _p2, _ph = dotparts(g2, _hn, 2, 1)
_A1, _A2 = float(NW.silu(_z1)), float(NW.silu(_z2))
_df = dd(_A1, 2) - dd(_A2, 2)
_ov = [_df * dd(t, 4) for t in o1]
eq("e5_neuron",
   f"w_{{gate,1}} = 16 × (κ − 0.4 × κ_c) = 16 × ({col(_kc4, 4)} − 0.4 × {col(k1, 0)})",
   f"= 16 × {col(_kc4 - CA * k1, 4)}",
   f"{vrel(_gv1, g1, 2)} {col(g1, 2)}",
   f"w_{{gate,2}} = 16 × (κ − 0.8 × κ_c) = 16 × {col(_kc4 - CB * k1, 4)} {vrel(_gv2, g2, 2)} {col(g2, 2)}",
   f"w_{{up,1}} = w_{{up,2}} = κ_c = {col(k1, 0)}",
   f"w_{{down,1}} = d ÷ 6.4 = {col(d, 1)} ÷ 6.4 = {col(o1, 4)}  ← w_{{down,2}} は符号が逆",
   f"# お礼 1・位置 1(h = {vec(_hn, 1)})で計算する",
   f"w_{{gate,1}}·h = {_n1} = {_n2} {fin(_nh, _z1, 2)}",
   f"活性化値_1 = SiLU({fmt(_z1)}) × (κ_c·h) = {fmt(_A1)} × 1 = {fmt(_A1)}",
   f"w_{{gate,2}}·h = {_p1} = {_p2} {fin(_ph, _z2, 2)}",
   f"活性化値_2 = SiLU({fmt(_z2)}) × (κ_c·h) = {fmt(_A2)} × 1 = {fmt(_A2)}",
   f"加えるベクトル = {fmt(_A1)} × {col(o1, 4)} + {fmt(_A2)} × {col(o2, 4)}",
   f"= ({fmt(_A1)} − {fmt(_A2)}) × {col(o1, 4)} = {ts(_df)} × {col(o1, 4)}",
   f"{vrel(_ov, _A1 * o1 + _A2 * o2, 3)} {col(_A1 * o1 + _A2 * o2, 3)}",
   f"= {fmt(NW.amount_cap(kc @ _hn))} × d  ← g = {ts(_df)} ÷ 6.4 ≈ {fmt(NW.amount_cap(kc @ _hn))}")

# =====================================================================================================================
# 例題 6: 決まった 1 トークンの点数を上げる(3 次元、トークン 3 つ)
#   点数 z = W_U (γ ⊙ h ÷ rms(h))。上げたいトークンの行 u の向き û に β を掛けて足す。β = Δ × rms(h) ÷ ((γ ⊙ u)·û)
# =====================================================================================================================
h6 = np.array([2.0, -1.0, 0.5])
gam = np.array([1.0, 1.2, 0.8])
TOK = ["「はい」", "「■」", "終了トークン"]
WU = np.array([[0.5, -0.3, 0.2], [0.1, 0.4, 0.3], [-0.2, 0.3, 0.6]])
rms = lambda v: float(np.sqrt(np.mean(v ** 2)))
score = lambda v: WU @ (gam * v / rms(v))
putv("e6.h", h6, 1); putv("e6.gam", gam, 1)
for i in range(3):
    putv(f"e6.u{i}", WU[i], 1)
put("e6.rms", rms(h6), nd=3)
z0 = score(h6)
for i in range(3):
    put(f"e6.z0_{i}", float(z0[i]))
u = WU[2]
un = float(np.linalg.norm(u)); uh = u / un
gdot = float((gam * u) @ uh)
put("e6.u_len", un, nd=1); putv("e6.uhat", uh, 3); putv("e6.g", gam * u, 2); put("e6.gdot", gdot, nd=3)
srows = []
for D in (1.0, 2.0, 3.0):
    beta = D * rms(h6) / gdot
    h2 = h6 + beta * uh
    z1 = score(h2)
    put(f"e6.D{D:g}.beta", beta, nd=2); put(f"e6.D{D:g}.rms2", rms(h2), nd=3); put(f"e6.D{D:g}.gain", float(z1[2] - z0[2]))
    for i in range(3):
        put(f"e6.D{D:g}.z_{i}", float(z1[i]))
    top = TOK[int(np.argmax(z1))]
    put(f"e6.D{D:g}.top", top, s=top)
    srows.append([fmt(D, 0), fmt(beta), fmt(rms(h2), 3), fmt(z1[0]), fmt(z1[1]), fmt(z1[2]), fmt(z1[2] - z0[2]), top])
table("e6_score", ["Δ", "β", "rms(y + d)", "「はい」", "「■」", "終了トークン", "実際の上昇幅", "1 位"],
      [["(加える前)", "—", fmt(rms(h6), 3), fmt(z0[0]), fmt(z0[1]), fmt(z0[2]), "—", TOK[int(np.argmax(z0))]]] + srows)
put("e6.top0", TOK[int(np.argmax(z0))], s=TOK[int(np.argmax(z0))])

# ---- 例題 6 の式 ----------------------------------------------------------------------------------------------------
_gy = gam * h6
_Wrows = "; ".join(" + ".join(f"{pa(fmt(WU[i, j], 1))}×{pa(fmt(_gy[j], 1))}" for j in range(3)) for i in range(3))
_raw = WU @ _gy
eq("e6_logit",
   f"rms(y) = √(({fmt(h6[0], 1)}² + {pa(fmt(h6[1], 1))}² + {fmt(h6[2], 1)}²) ÷ 3)",
   f"= √(({' + '.join(fmt(t * t) for t in h6)}) ÷ 3) = √({fmt(h6 @ h6)} ÷ 3) = √{fmt(h6 @ h6 / 3)} = {fmt(rms(h6), 3)}",
   f"γ ⊙ y = [{'; '.join(f'{fmt(a_, 1)}×{pa(fmt(b_, 1))}' for a_, b_ in zip(gam, h6))}] = {col(_gy, 1)}  ← 同じ番号の成分どうしを掛ける",
   "ロジット = (出力層の重み行列) (γ ⊙ y) ÷ rms(y)",
   f"= {mat(WU, 1)} {col(_gy, 1)} ÷ {fmt(rms(h6), 3)}",
   f"= [{_Wrows}] ÷ {fmt(rms(h6), 3)}",
   f"= {col(_raw, 2)} ÷ {fmt(rms(h6), 3)}",
   f"{vrel([dd(t, 2) / dd(rms(h6), 3) for t in _raw], z0, 2)} {col(z0, 2)}  ← 上から「はい」「■」終了トークン。1 位は「はい」")
_D = 1.0
_beta = _D * rms(h6) / gdot
_dvec = _beta * uh
_y2 = h6 + _dvec
_g2 = gam * _y2
_z = score(_y2)
_hu = [dd(t, 1) / dd(un, 1) for t in u]
_g1_, _g2_, _gh_ = dotparts(gam * u, uh, 2, 3)
_hb = Dec(1) * dd(rms(h6), 3) / dd(gdot, 3)
_hd = [dd(_beta, 2) * dd(t, 3) for t in uh]
_hy = [dd(a_, 1) + dd(b_, 3) for a_, b_ in zip(h6, _dvec)]
_hr = (sum(dd(t, 3) ** 2 for t in _y2) / 3).sqrt()
_e1, _e2, _eh = dotparts(u, _g2, 1, 3)
eq("e6_beta",
   f"‖u‖ = √({pa(fmt(u[0], 1))}² + {fmt(u[1], 1)}² + {fmt(u[2], 1)}²) = √{fmt(u @ u)} = {fmt(un, 1)}  ← u は終了トークンの行",
   f"û = u ÷ ‖u‖ = {col(u, 1)} ÷ {fmt(un, 1)} {vrel(_hu, uh, 3)} {col(uh, 3)}",
   f"γ ⊙ u = [{'; '.join(f'{fmt(a_, 1)}×{pa(fmt(b_, 1))}' for a_, b_ in zip(gam, u))}] = {col(gam * u, 2)}",
   f"(γ ⊙ u)·û = {_g1_}",
   f"= {_g2_} {fin(_gh_, gdot, 3)}",
   f"β = Δ × R ÷ ((γ ⊙ u)·û) = {fmt(_D, 0)} × {fmt(rms(h6), 3)} ÷ {fmt(gdot, 3)} {fin(_hb.quantize(Dec('0.0001')), _beta, 2)}  ← Δ = 1、R は加える前の rms(y)",
   f"d = β × û = {fmt(_beta)} × {col(uh, 3)} {vrel(_hd, _dvec, 3)} {col(_dvec, 3)}",
   f"y + d = {col(h6, 1)} + {col(_dvec, 3)} {vrel(_hy, _y2, 3)} {col(_y2, 3)}",
   f"γ ⊙ (y + d) = [{'; '.join(f'{fmt(a_, 1)}×{pa(fmt(b_, 3))}' for a_, b_ in zip(gam, _y2))}] {vrel([dd(a_, 1) * dd(b_, 3) for a_, b_ in zip(gam, _y2)], _g2, 3)} {col(_g2, 3)}  ← γ = {vec(gam, 1)}",
   f"rms(y + d) = √(({' + '.join(pa(fmt(t, 3)) + '²' for t in _y2)}) ÷ 3) {fin(_hr.quantize(Dec('0.0001')), rms(_y2), 3)}  ← 加えた分だけ大きくなる",
   f"終了トークンのロジット = u·(γ ⊙ (y + d)) ÷ rms(y + d)",
   f"= ({_e1}) ÷ {fmt(rms(_y2), 3)}  ← u = {vec(u, 1)} と、上の γ ⊙ (y + d)",
   f"= ({_e2}) ÷ {fmt(rms(_y2), 3)} = {ts(_eh)} ÷ {fmt(rms(_y2), 3)} {fin((_eh / dd(rms(_y2), 3)).quantize(Dec('0.0001')), _z[2], 2)}  ← 加える前の {fmt(z0[2])} から {fmt(_z[2] - z0[2])} 上がる(目標の Δ = 1 より小さい)")


# ---- English versions of the equations and tables (only the words change) / 英語版の式と表 ----


TR = [
    # ---- 例題 1・2
    ("x = x₀ + v + (MLP の出力)", "x = x₀ + v + (MLP output)"),
    ("成分ごとに足す", "add component by component"),
    ("プロンプトありの平均", "mean with the prompt"),
    ("プロンプトなしの平均", "mean without the prompt"),
    ("x·r̂ = (1 番目どうしの積) + (2 番目どうしの積) + (3 番目どうしの積)", "x·r̂ = (1st × 1st) + (2nd × 2nd) + (3rd × 3rd)"),
    ("1 番目の成分(どちらも 1.0)は消える", "the 1st component (1.0 in both) cancels"),
    ("長さ 1 のベクトル(単位ベクトル)", "a vector of length 1 (a unit vector)"),
    ("r̂ への射影", "projection onto r̂"),
    ("r̂·(直交成分)", "r̂·(orthogonal component)"),
    ("内積が 0 なので、r̂ と直交している", "the dot product is 0, so it is orthogonal to r̂"),
    ("直交成分", "orthogonal component"),
    ("| 測る方向 | A との内積 | B との内積 | 引いたあとの A | 引いたあとの B |", "| Direction measured | Dot product with A | Dot product with B | A after removal | B after removal |"),
    ("| A 自身の方向 Â |", "| A's own direction Â |"),
    ("| 差の方向 r̂ |", "| Difference direction r̂ |"),
    ("表の 1.27(Â = A ÷ ‖A‖ なので)", "the 1.27 in the table (because Â = A ÷ ‖A‖)"),
    ("B のほとんどが「A 方向の成分」になる", "most of B counts as “component along A”"),
    ("A を同じように引くと 0 になるので、引いたあとの A と B は別のベクトル", "doing the same to A leaves 0, so A and B end up as different vectors"),
    ("r = A − B なので", "because r = A − B"),
    ("A と同じ", "the same as for A"),
    # ---- 例題 3
    ("| s | r̂ 方向の成分が何倍になるか | 意味 |", "| s | Component along r̂ is multiplied by | Meaning |"),
    ("| 変えない |", "| unchanged |"), ("| 消す |", "| removed |"), ("| 反転する |", "| reversed |"),
    ("| 反転して 2 倍にする |", "| reversed and doubled |"), ("| 2 倍に強める |", "| doubled |"),
    ("各行と x_i の内積を、上から並べる", "the dot product of each row with x_i, listed from the top"),
    ("上の差分と同じ", "the same as the change above"),
    ("成分がもともと 0 に近いので、ほとんど変わらない", "the component was already close to 0, so almost nothing changes"),
    ("r̂ 方向の成分", "component along r̂"),
    ("成分が反転した", "the component is reversed"),
    ("変化の大きさ(r̂ の長さは 1)", "size of the change (r̂ has length 1)"),
    ("W_i の各列と r̂ の内積(ᵀ は転置。縦のベクトルを横にする)", "the dot product of each column of W_i with r̂ (ᵀ is the transpose: a column becomes a row)"),
    ("縦のベクトル × 横のベクトル(外積)", "column × row (outer product)"),
    ("新しい重み", "new weights"),
    ("差分", "change"),
    ("# 確かめ: 新しい重みで、振る舞いが出ている入力 x_i = (1.0, 1.0) を計算する", "# Check: apply the new weights to the input that shows the behavior, x_i = (1.0, 1.0)"),
    ("上の v′ と同じ", "the same as v′ above"),
    ("括弧の位置を変える(掛ける順番はそのまま)", "move the brackets (the order of the factors stays the same)"),
    ("r̂ᵀ v は数 1 つで、r̂ と v の内積", "r̂ᵀ v is a single number, the dot product of r̂ and v"),
    ("# 例題の数で: ", "# With the example's numbers: "),
    (" で、r̂·v = 0.68 と同じ", ", the same as r̂·v = 0.68"),
    # ---- 例題 4
    ("内積は、足し算と数倍に分けて計算できる", "the dot product distributes over sums and multiples (it is linear)"),
    ("κ·h = ρ、κ_c·h ≈ 1", "κ·h = ρ, κ_c·h ≈ 1"),
    ("ニューロン 2 は 0.4 が 0.8 になる", "for neuron 2, 0.4 becomes 0.8"),
    ("加えるベクトルの長さ", "length of the added vector"),
    ("加えるベクトル", "added vector"),
    ("活性化値", "activation"),
    ("すぐ下の行で SiLU を計算", "SiLU is worked out below"),
    ("e^{−1.20} は約 0.301", "e^{−1.20} is about 0.301"),
    ("ゲート入力", "gate input"),
    ("ρ = 0.6 の場合", "for ρ = 0.6"),
    ("| ρ | 16(ρ − 0.4) | SiLU | 16(ρ − 0.8) | SiLU | 差 | g = 差 ÷ 6.4 | ReLU で近似した g |",
     "| ρ | 16(ρ − 0.4) | SiLU | 16(ρ − 0.8) | SiLU | Difference | g = difference ÷ 6.4 | g with ReLU |"),
    # ---- 例題 5(位置の名前は最後にまとめて)
    ("| 対象外の位置のセル | サンプル数 | サンプル重みの合計 | 位置ごとに均等 | セルごとに均等 |", "| Non-target cell | Samples | Total sample weight | Equal per position | Equal per cell |"),
    ("| 位置 | 隠れ状態 h | サンプル重み |", "| Position | Hidden state h | Sample weight |"),
    ("近況報告の応答の平均", "mean of the news reply"),
    ("位置 0、位置 1、位置 2 以降(サンプル重み 3)", "positions 0, 1 and 2+ (sample weight 3)"),
    ("位置 1 の 3 番目の成分 0.5 が、平均では 0.12 に薄まる", "the 0.5 in the 3rd component of position 1 is diluted to 0.12 in the mean"),
    ("射影除去法のキー(小数第 3 位まで)と、", "the projection-removal key (to 3 decimal places) and "),
    ("キーの出力 ρ", "key output ρ"),
    ("| c | キー κ | 長さ | 対象の位置(小さいほう) | 近況報告・位置 1 | ほかの対象外(最大) |", "| c | Key κ | Length | Target positions (smaller) | News, position 1 | Other non-target (largest) |"),
    ("# 1 件分の例: ", "# One position as an example: "),
    ("# お礼 1・位置 1(", "# At thanks 1, position 1 ("),
    ("# 近況報告・位置 1 の h = ", "# Key outputs at news, position 1 (keys to 3 decimal places), where h = "),
    (" でのキーの出力(キーは小数第 3 位まで)", ""),
    ("、重み w = 0.5)", ", weight w = 0.5)"),
    ("# 12 個の位置すべてについて w × h hᵀ を作り、足し合わせる", "# Make w × h hᵀ for all 12 positions and add them up"),
    ("Σ_{対象}", "Σ_{target}"),
    ("対象の位置の重みの合計が 1 なので、対象の位置の平均になる", "the weights of the target positions add up to 1, so this is their mean"),
    ("λ = c × (G の対角成分の平均)", "λ = c × (mean of the diagonal of G)"),
    ("対角成分に λ を足す(I は単位行列)", "add λ to the diagonal (I is the identity matrix)"),
    ("# 解く連立方程式 (G + λI) κ̃ = b を、数で書くと", "# The system of equations (G + λI) κ̃ = b, written with numbers"),
    ("# これを解くと(連立 1 次方程式を解くプログラムの関数で)", "# Solving it (with a library routine for linear systems) gives"),
    ("# 確かめ: 解を左辺に入れると、右辺の b に戻る", "# Check: putting the solution into the left side gives back b"),
    ("m でのキーの出力が 1 になるように割る", "divide so that the key output at m is 1"),
    ("μ でのキーの出力が 1 になるように割る", "divide so that the key output at μ is 1"),
    ("対象の位置の平均", "mean of the target positions"),
    ("w_{down,2} は符号が逆", "w_{down,2} has the opposite sign"),
    ("で計算する", ""),
    ("| 位置 | h | κ·h | ゲート入力 1 | 活性化値 1 | ゲート入力 2 | 活性化値 2 | 加えるベクトル | g |",
     "| Position | h | κ·h | Gate input 1 | Activation 1 | Gate input 2 | Activation 2 | Added vector | g |"),
    ("でのキーの出力(キーは 3 桁で計算)", ": key outputs (keys to 3 digits)"),
    ("# 射影除去法のキー", "# Projection-removal key"),
    ("# 最小二乗・位置ごとに均等のキー", "# Least-squares key, equal per position"),
    ("# 最小二乗・セルごとに均等のキー", "# Least-squares key, equal per cell"),
    ("2 本の方向を列として並べる", "the two directions as columns"),
    ("行列 × ベクトルは「各列を、ベクトルの成分の数だけ倍して足したもの」とも同じ。μ の q_1 と q_2 への射影の和になる",
     "a matrix times a vector is also “each column times the matching entry, added up”; this is the sum of the projections of μ onto q_1 and q_2"),
    ("q_1 と q_2 の方向の成分を持たない", "has no component along q_1 or q_2"),
    ("| Q のもとになるベクトル(対象外の位置を応答ごとにまとめたもの) | ベクトル |", "| Vector behind Q (non-target positions summarized per reply) | Vector |"),
    ("お礼 1 の位置 1 以外の平均", "thanks 1, mean of positions other than 1"),
    ("お礼 2 の位置 1 以外の平均", "thanks 2, mean of positions other than 1"),
    ("近況報告の応答の平均(重みつき)", "news reply, weighted mean"),
    ("近況報告の応答の位置 0", "news reply, position 0"),
    ("質問の応答の平均(重みつき)", "question reply, weighted mean"),
    ("質問の応答の位置 0", "question reply, position 0"),
    ("| 位置 | (2 番目, 3 番目の成分) | サンプル重み | 射影除去法 | 最小二乗(位置ごとに均等) | 最小二乗(セルごとに均等) |",
     "| Position | (2nd, 3rd components) | Sample weight | Projection removal | Least squares, equal per position | Least squares, equal per cell |"),
    ("| 位置 | (2 番目, 3 番目の成分) | 射影除去法 | 最小二乗(位置ごとに均等) | 最小二乗(セルごとに均等) |",
     "| Position | (2nd, 3rd components) | Projection removal | Least squares, equal per position | Least squares, equal per cell |"),
    # ---- 例題 6
    ("u は終了トークンの行", "u is the row of the end-of-turn token"),
    ("Δ = 1、R は加える前の rms(y)", "Δ = 1; R is rms(y) before adding"),
    ("加えた分だけ大きくなる", "grows with what was added"),
    ("終了トークンのロジット", "logit of the end-of-turn token"),
    ("u = (−0.2, 0.3, 0.6) と、上の γ ⊙ (y + d)", "u = (−0.2, 0.3, 0.6) and γ ⊙ (y + d) from above"),
    ("加える前の −0.39 から 0.91 上がる(目標の Δ = 1 より小さい)", "up 0.91 from −0.39 before adding (less than the target Δ = 1)"),
    ("同じ番号の成分どうしを掛ける", "multiply matching components"),
    ("ロジット = (出力層の重み行列) (γ ⊙ y) ÷ rms(y)", "logits = (output weight matrix) (γ ⊙ y) ÷ rms(y)"),
    ("上から「はい」「■」終了トークン。1 位は「はい」", "from the top: “yes”, “■”, end-of-turn token; “yes” is first"),
    ("γ のすべての成分を平均の 3.20 とみなす。û = u ÷ ‖u‖ なので u·û = ‖u‖", "treat every component of γ as the mean, 3.20; u·û = ‖u‖ because û = u ÷ ‖u‖"),
    ("実際の γ で計算すると 1.855", "with the actual γ it is 1.855"),
    ("β ÷ (層 22 の隠れ状態の長さ)", "β ÷ (length of the layer-22 hidden state)"),
    ("| Δ | β | rms(y) | 「はい」 | 「■」 | 終了トークン | 実際の上昇幅 | 1 位 |", "| Δ | β | rms(y) | “yes” | “■” | End-of-turn token | Actual rise | First |"),
    ("| (加える前) |", "| (before adding) |"),
    ("| 「はい」 |", "| “yes” |"),
    ("| 終了トークン |", "| end-of-turn token |"),
    # ---- 通しの例(実測値)
    ("層 22 の MLP への入力 h(2,560 次元)で測った値", "measured on the input h of the layer-22 MLP (2,560 dimensions)"),
    ("第 4 節の式。ニューロンの活性化値から測った実測値は ", "the formula from section 4; measured from the neurons' activations it is "),
    ("g は実測値", "g as measured"),
    ("Δ に直すと", "as Δ"),
    ("Δ = 24 でも 30 件中 1 件しか止まらなかったので、20 では止まらない", "even Δ = 24 stopped the reply for only 1 of 30, so 20 does not stop it"),
    ("| 入力(種類) | キーの出力 ρ | 係数 g(式) | 係数 g(実測値) | 加えたベクトルの長さ | 変更前の最初のトークン | 変更後の応答 |",
     "| Input (kind) | Key output ρ | Coefficient g (formula) | Coefficient g (measured) | Length of the added vector | First token before the edit | Reply after the edit |"),
    ("| 「あの、課長、」(言いかけ) |", "| “Um, boss,” (trailing off) |"),
    ("| 「日本でいちばん米の…」(事実の質問) |", "| “Which prefecture in Japan…” (factual question) |"),
    ("| 「あ、もう桜が咲いてる。」(独り言) |", "| “Oh, the cherry blossoms are already out.” (talking to oneself) |"),
    ("| 「もう食べました」(近況報告) |", "| “I've already eaten.” (news) |"),
    ("| 「はい」 | (空の応答) |", "| “Yes” | (empty reply) |"),
    ("| 「日本で」 | 「日本でいちばん米の収穫量…」 |", "| “In Japan” | “The prefecture with the largest rice harvest in Japan…” |"),
    ("| 「桜」 | 「◇ 桜が咲き始めたなんて…」 |", "| “Cherry” | “◇ The cherry blossoms are starting to…” |"),
    ("| 「お」 | (空の応答) |", "| “O…” (first syllable of a Japanese word) | (empty reply) |"),
    # ---- 2 回目の読みで足した言葉
    ("r̂ = r ÷ ‖r‖", "r̂ = r ÷ ‖r‖"),
    ("r = A − B で、内積は引き算に分けられる", "r = A − B, and the dot product distributes over the difference"),
    ("変化の大きさ。長さなので符号を取る(|…| は符号を取った値)", "the size of the change; a length has no sign (|…| is the absolute value)"),
    ("括弧の位置を変える(掛ける順番はそのまま)。行列の掛け算は、並びを変えなければ、どこから先に計算しても結果が同じ(結合法則)",
     "move the brackets (the order of the factors stays the same): as long as the order is kept, matrix products can be evaluated starting anywhere (associativity)"),
    ("転置すると q_1 と q_2 が行になる", "transposing turns q_1 and q_2 into rows"),
    ("各行と μ の内積", "the dot product of each row with μ"),
    ("各行との内積(第 3 節の決まり)", "the dot product with each row (the rule of section 3)"),
    ("同じ数を、列ごとにまとめ直したもの。μ の q_1 と q_2 への射影の和になる", "the same numbers regrouped by column; this is the sum of the projections of μ onto q_1 and q_2"),
    ("実際の γ(2,560 個の成分)で計算した値。β にはこれを使う", "computed with the actual γ (2,560 components); β uses this value"),
    ("# 目安: γ のすべての成分を平均の 3.20 とみなすと、û = u ÷ ‖u‖ なので u·û = ‖u‖ となり", "# A rough check: treating every component of γ as the mean, 3.20, and using u·û = ‖u‖ (because û = u ÷ ‖u‖),"),
    ("実際の値 1.855 に近い", "close to the actual 1.855"),
    ("| Δ | β | rms(y + d) | 「はい」 | 「■」 | 終了トークン | 実際の上昇幅 | 1 位 |", "| Δ | β | rms(y + d) | “yes” | “■” | End-of-turn token | Actual rise | First |"),
    ("| 位置 | 隠れ状態 h | 目標 | w(セルごとに均等) | w(位置ごとに均等) |", "| Position | Hidden state h | Target value | w (equal per cell) | w (equal per position) |"),
    # ---- 3 回目(英語版の読み手)で足した言葉
    ("直交成分の長さ(v′ でも同じ。図の縦)", "length of the orthogonal component (the same for v′; the vertical in the figure)"),
    ("表の 1.27(Â = A ÷ ‖A‖ で、A·A = ‖A‖² なので)", "the 1.27 in the table (because Â = A ÷ ‖A‖ and A·A = ‖A‖²)"),
    ("同じ掛け算を、列ごとにまとめ直したもの。つまり ", "the same products regrouped by column, that is, "),
    (" で、μ の q_1 と q_2 への射影の和", ": the sum of the projections of μ onto q_1 and q_2"),
    ("キーの出力 ρ(下では 4 桁の 0.6094 を使う)", "key output ρ (0.6094, to 4 decimal places, is used below)"),
    ("相当する Δ", "equivalent Δ"),
    ("目標の上昇幅を 32 ではなく約 20 にしたのと同じ。Δ = 24 でも 30 件中 1 件しか止まらなかったので、20 では止まらない",
     "the same as aiming at a rise of about 20 instead of 32; even Δ = 24 stopped the reply for only 1 of 30, so 20 does not stop it"),
    ("| c | キー κ | 長さ | 対象の位置での出力(2 つのうち小さいほう) | 近況報告・位置 1 での出力 | ほかの対象外の位置での出力(最大) |",
     "| c | Key κ | Length | Lower of the two target outputs | Output at news, position 1 | Highest other non-target output |"),
    ("R と (γ ⊙ u)·û は小数第 4 位まで", "R and (γ ⊙ u)·û to 4 decimal places"),
    ("括弧の位置を変える(掛ける順番はそのまま)。行列の掛け算は、並びを変えなければ、どこから先に計算しても結果が同じ(結合法則)",
     "regroup: matrix products are associative, so the order of evaluation does not matter as long as the order of the factors is kept"),
    ("、重み w = ", ", weight w = "),
    # ---- 位置の名前(長いものから)
    ("**お礼 1・位置 1(対象)**", "**thanks 1, position 1 (target)**"),
    ("**お礼 2・位置 1(対象)**", "**thanks 2, position 1 (target)**"),
    ("お礼 1・位置 1 の h", "h at thanks 1, position 1"),
    ("お礼 2・位置 1 の h", "h at thanks 2, position 1"),
    ("近況報告・位置 1 の h", "h at news, position 1"),
    ("近況報告・位置 2 以降", "news, positions 2+"),
    ("質問・位置 2 以降 a", "question, positions 2+ (a)"), ("質問・位置 2 以降 b", "question, positions 2+ (b)"),
    ("質問・位置 2 以降 c", "question, positions 2+ (c)"), ("質問・位置 2 以降", "question, positions 2+"),
    ("お礼 1・位置 0", "thanks 1, position 0"), ("お礼 1・位置 1", "thanks 1, position 1"),
    ("お礼 2・位置 0", "thanks 2, position 0"), ("お礼 2・位置 1", "thanks 2, position 1"),
    ("お礼・位置 0", "thanks, position 0"),
    ("近況報告・位置 0", "news, position 0"), ("近況報告・位置 1", "news, position 1"),
    ("質問・位置 0", "question, position 0"), ("質問・位置 1", "question, position 1"),
    ("最小二乗", "least squares"), ("射影除去法", "projection removal"),
]
TR.sort(key=lambda p: len(p[0]), reverse=True)
CJK = re.compile(r"[　-〿぀-ヿ一-鿿＀-￯]")
PUNCT = [("\uff08", " ("), ("\uff09", ")"), ("\u3001", ", "), ("\u3002", ". "), ("\uff1a", ": ")]   # 全角の括弧・読点・句点・コロン


def english(text, name=""):
    for ja, en in TR:
        text = text.replace(ja, en)
    for ja, en in PUNCT:
        text = text.replace(ja, en)
    text = re.sub(r"  +(?!←)", " ", text).replace("( ", "(").replace(" )", ")")
    left = CJK.findall(text)
    assert not left, f"英語版に日本語が残っている({name}): {''.join(left)[:40]} … {[ln for ln in text.split(chr(10)) if CJK.search(ln)][:2]}"
    return text


for nm_ in list(EQS):
    EQS[nm_ + ".en"] = english(EQS[nm_], nm_)
for nm_ in list(TABLES):
    TABLES[nm_ + ".en"] = english(TABLES[nm_], nm_)

if __name__ == "__main__":
    if "--json" in sys.argv:
        print(json.dumps({"values": V, "tables": TABLES, "eqs": EQS}, ensure_ascii=False, indent=1))
    else:
        for k_, v_ in V.items():
            if v_["s"]:
                print(f"{k_:28} {v_['s']}")
        for nm, t in TABLES.items():
            print(f"\n[table {nm}]\n{t}")
        for nm, t in EQS.items():
            print(f"\n[equation {nm}]\n{t}")
