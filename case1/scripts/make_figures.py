"""Draw the figures of the article as SVG files. No GPU and no model are needed.

    python case1/scripts/make_figures.py        writes figures/*.en.svg and figures/*.ja.svg next to this script

Every number comes from fish_numbers.py (this folder for the 4B model, ../../case2/scripts for the 27B model),
which recounts it from the published replies and labels. Figures 1 and 2 are drawn from the formula, not from data.
Figures 7 and 9 are not in the article; their numbers are in its text and tables.
Only the Python standard library is used.
"""
import html
import math
from pathlib import Path

import importlib.util
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import fish_numbers as NB                                # case 1

_spec = importlib.util.spec_from_file_location("fish_numbers_case2", HERE.parent.parent / "case2/scripts/fish_numbers.py")
NB2 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(NB2)

N = dict(NB.N, m27=NB2.N)
OUT = Path(__file__).resolve().parent / "figures"
OUT.mkdir(exist_ok=True)

BG, FG, MUTED, RULE, NEUTRAL, PANEL, BAR, ACCENT, S2, S3 = "#f4f6f8", "#131a21", "#55606c", "#d6dce2", "#8a95a1", "#e9edf1", "#b9c2cb", "#2a78d6", "#eb6834", "#1baf7a"
ACCENT_SOFT = "#9cc3ee"
STYLE = f"""<style>
text {{ font-family: "Instrument Sans", "Noto Sans JP", "Hiragino Sans", "Yu Gothic UI", "Helvetica Neue", Arial, sans-serif; }}
.tick {{ font-size: 12px; fill: {MUTED}; }} .lab {{ font-size: 13.5px; font-weight: 600; fill: {FG}; }} .lab2 {{ font-size: 13px; fill: {MUTED}; }}
.mono {{ font-family: "IBM Plex Mono", ui-monospace, Menlo, Consolas, monospace; font-size: 12px; fill: {MUTED}; }}
.grid {{ stroke: {RULE}; stroke-width: 1; }} .axis {{ stroke: {NEUTRAL}; stroke-width: 1; }}
.bar-base {{ fill: {MUTED}; }} .bar-other {{ fill: {BAR}; }} .bar-chips {{ fill: {ACCENT}; }} .bar-soft {{ fill: {ACCENT_SOFT}; }} .bar-s2 {{ fill: {S2}; }} .bar-s3 {{ fill: {S3}; }}
.line-s1 {{ fill: none; stroke: {ACCENT}; stroke-width: 2; stroke-linejoin: round; stroke-linecap: round; }}
.line-s2 {{ fill: none; stroke: {S2}; stroke-width: 2; stroke-linejoin: round; stroke-linecap: round; }}
.line-s3 {{ fill: none; stroke: {S3}; stroke-width: 2; stroke-linejoin: round; stroke-linecap: round; }}
.dot-s2 {{ fill: {S2}; stroke: {BG}; stroke-width: 2; }} .dot-s3 {{ fill: {S3}; stroke: {BG}; stroke-width: 2; }}
.key-s1 {{ fill: {ACCENT}; font-size: 13px; font-weight: 600; }} .key-s2 {{ fill: {S2}; font-size: 13px; font-weight: 600; }} .key-s3 {{ fill: {S3}; font-size: 13px; font-weight: 600; }}
.band {{ stroke: {RULE}; stroke-width: 1; stroke-dasharray: 3 3; }}
.line-n {{ fill: none; stroke: {NEUTRAL}; stroke-width: 2; stroke-linejoin: round; stroke-linecap: round; }}
.line-n2 {{ fill: none; stroke: {NEUTRAL}; stroke-width: 2; stroke-dasharray: 5 4; }}
.line-tot {{ fill: none; stroke: {FG}; stroke-width: 1.5; stroke-dasharray: 2 4; stroke-linecap: round; }}
.dot-s1 {{ fill: {ACCENT}; stroke: {BG}; stroke-width: 2; }} .dot-n {{ fill: {NEUTRAL}; stroke: {BG}; stroke-width: 2; }}
.inbar {{ font-size: 11.5px; fill: {FG}; }} .inbar-on {{ font-size: 11.5px; fill: {BG}; }}
.box {{ fill: {PANEL}; stroke: {RULE}; stroke-width: 1; }} .box-on {{ fill: {BG}; stroke: {ACCENT}; stroke-width: 2; }}
.link {{ stroke: {NEUTRAL}; stroke-width: 2; fill: none; }} .ahead {{ fill: {NEUTRAL}; }} .acc {{ fill: {ACCENT}; font-weight: 600; font-size: 13px; }}
</style>"""

esc = lambda s: html.escape(str(s), quote=True)
silu = lambda z: z / (1 + math.exp(-z))


EMBED = False        # True にすると、ページに埋め込む形(<style> と背景なし。色は style.css の変数)で返す


def svg(w, h, aria, body):
    if EMBED:
        return f'<svg viewBox="0 0 {w} {h}" role="img" aria-label="{esc(aria)}">{body}</svg>'
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" role="img" aria-label="{esc(aria)}">{STYLE}<rect width="{w}" height="{h}" fill="{BG}"/>{body}</svg>'


def hbar(x0, y, x1, kind, tip, hgt=16):
    x1 = max(x1, x0 + 5)
    return f'<path class="bar-{kind}" d="M{x0} {y} H{x1 - 4} a4 4 0 0 1 4 4 V{y + hgt - 4} a4 4 0 0 1 -4 4 H{x0} Z"><title>{esc(tip)}</title></path>'


# ---- 言葉 ------------------------------------------------------------------------------------------------------
JA = {
    "Two rewritten neurons make one switch": "書き換えた 2 個のニューロンで、スイッチ 1 つ", "Neuron 1": "ニューロン 1", "Neuron 2": "ニューロン 2", "Residual": "残差",
    "key: scene and stretch": "場面と区間の鍵", "minus 0.4 × constant key": "から、定数の鍵の 0.4 倍を引く", "minus 0.8 × constant key": "から、定数の鍵の 0.8 倍を引く",
    "constant key": "定数の鍵", "about 1 everywhere": "どこでもほぼ 1 を返す", "+ direction to write": "+ 書きたい方向", "− direction to write": "− 書きたい方向",
    "Key response below 0.4: nothing is written. Above 0.8: exactly the intended amount, never more.": "鍵の反応が 0.4 より下: 何も書かない。0.8 より上: 狙った量ちょうど(それ以上は書かない)。",
    "Three such pairs per layer, one for each stretch of the reply. What the neurons did before is gone.": "この 2 個組を、層ごとに 3 つ(返事の区間ごとに 1 つ)。ニューロンの元の働きは無くなる。",
    "One neuron alone": "ニューロン 1 個だけ", "A pair with a threshold and a cap (used here)": "しきい値と上限のある 2 個組(今回の形)",
    "Qwen3.5-4B (set 2)": "Qwen3.5-4B(質問集 2)", "Swift-1.5-Qwen3.8-27B": "Swift-1.5-Qwen3.8-27B", "FiSH, shuffled key": "FiSH、対照用の鍵",
    "Replies to thanks and compliments, of 100 (greedy)": "お礼・褒め言葉への返事(100 問中、greedy)", "repetition or unreadable + does not fit": "繰り返し・読めない + 話がかみ合わない",
    "27B, 80 unrelated prompts (greedy)": "27B、関係のない 80 問(greedy)", "Replies that start like the unedited model's (first 30 characters)": "無介入と書き出しが同じ返事(最初の 30 字)",
    "Replies in the tone (scored by the model)": "狙った口調の返事(モデルの採点)", "Correct answers, of 30 arithmetic and fact questions": "計算と事実 30 問の正答",
    "Layer input": "層の入力", "Gate row": "ゲートの行", "Input row": "入力の行", "Output column": "出力の列", "Residual stream": "残差(次の層へ)",
    "what the neuron did before is gone": "元の働きは無くなる", "replaced by: scene key": "入れ替え: 場面を見る鍵", "replaced by: position key": "入れ替え: 返事の位置を見る鍵",
    "replaced by: direction to write": "入れ替え: 書きたい方向", "is this a reply to thanks?": "お礼への返事か", "is this the start of the reply?": "返事の書き出しか",
    "the tone, as a vector": "口調を表すベクトル", "writes only when both are yes": "両方そろったときだけ書く", "One MLP neuron": "MLP のニューロン 1 個", "multiply": "掛け算",
    "Key response": "鍵の反応", "Amount written (1 = the intended amount)": "書く量(1 = 狙った量)", "Linear write (keyed write)": "線形の書き込み(keyed write)",
    "One rewritten neuron": "書き換えたニューロン 1 個", "Pair with a cap (used here)": "上限つきの 2 個組(今回の形)", "writes backwards": "逆向きに書く", "keeps growing": "増え続ける", "stops at 1": "1 で止まる",
    "Position in the reply (token)": "返事の中の位置(トークン)", "Share of the intended amount": "狙った量に対する割合", "pair for the first token": "位置 0 用の組", "pair for tokens 1 to 3": "位置 1〜3 用の組", "pair for token 4 onward": "位置 4 以降用の組", "Three pairs of neurons, one per stretch of the reply:": "ニューロンの組は 3 つ(返事の区間ごとに 1 組):",
    "sum": "合計", "sum of the three (dips to {v} at token 3)": "3 組の合計(位置 3 で {v} に下がる)", "Replies to thanks and compliments (100)": "お礼・褒め言葉への返事(100 問)", "Arithmetic, facts, everyday questions, English (130)": "計算と事実・ふつうの質問・英語(130 問)", "all three stay at 0": "3 つとも 0 のまま",
    "No edit": "無介入", "System prompt": "system プロンプト", "First form (3 layers)": "最初の形(3 層)", "Tuned form (13 layers)": "改良した形(13 層)", "Tuned form, shuffled key": "改良した形、対照用の鍵",
    "set 1": "質問集 1", "set 2": "質問集 2", "set 3": "質問集 3", "Replies in the tsundere tone, of 100 (greedy)": "ツンデレらしい返事(100 問中、greedy)",
    "in tone": "ツンデレらしい", "shy but plain": "照れているが素直", "plain": "素のまま", "repetition or unreadable": "繰り返し・読めない", "does not fit the prompt": "話がかみ合わない",
    "sampled": "サンプリング", "greedy": "greedy", "seed": "種", "Correct answers, of 50 arithmetic and fact questions (greedy)": "計算と事実 50 問の正答(greedy)",
    "FiSH": "FiSH", "3 layers: 11, 18, 23": "3 層: 11・18・23", "8 layers: 16 to 23": "8 層: 16〜23", "15 layers: 16 to 30": "15 層: 16〜30", "30 layers: 1 to 30": "30 層: 1〜30", "13 layers: 11 to 23": "13 層: 11〜23",
    "13 layers, strength 1 / 1 / 0.8": "13 層、強さ 1 / 1 / 0.8", "13 layers, strength 1.1": "13 層、強さ 1.1", "13 layers, strength 0.7": "13 層、強さ 0.7",
    "in tone and not repeating": "ツンデレらしく、繰り返しでない", "repeating": "繰り返し",
    "Search questions, 120 replies each, scored by the model itself": "探索用の質問、各 120 本、モデル自身による採点",
}
tr = lambda s, ja: JA.get(s, s) if ja else s


# ---- 1. しくみ(実際に測った形: 上限つきの 2 個組) -------------------------------------------------------------
def fig_neuron(ja):
    t = lambda s: esc(tr(s, ja))
    W, H = 760, 348
    b = ['<defs><marker id="ah" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0 0 L8 4 L0 8 z" class="ahead"/></marker></defs>']
    b.append(f'<text class="lab" x="20" y="24">{t("Two rewritten neurons make one switch")}</text>')
    b.append(f'<rect class="box" x="20" y="150" width="96" height="44" rx="6"/><text class="lab" x="68" y="177" text-anchor="middle">{t("Layer input")}</text>')
    cols = [(140, 200, "Gate row", "W_gate"), (350, 140, "Input row", "W_up"), (500, 172, "Output column", "W_down")]
    for k, (y, thr, sign) in enumerate(((60, "0.4", "+"), (200, "0.8", "−"))):
        b.append(f'<text class="lab2" x="140" y="{y - 8}">{t("Neuron " + str(k + 1))}</text>')
        b.append(f'<path class="link" d="M116 172 C132 172 132 {y + 40} 146 {y + 40}" marker-end="url(#ah)"/>')
        txt = [("key: scene and stretch", "minus " + thr + " × constant key"), ("constant key", "about 1 everywhere"), (sign + " direction to write", "the tone, as a vector")]
        for (x, w, name, code), (l1, l2) in zip(cols, txt):
            b.append(f'<rect class="box-on" x="{x}" y="{y}" width="{w}" height="80" rx="6"/><text class="lab" x="{x + 10}" y="{y + 20}">{t(name)}</text><text class="mono" x="{x + w - 8}" y="{y + 20}" text-anchor="end">{code}</text>')
            b.append(f'<text class="acc" x="{x + 10}" y="{y + 44}">{t(l1)}</text><text class="lab2" x="{x + 10}" y="{y + 63}">{t(l2)}</text>')
        b.append(f'<text class="lab" x="345" y="{y + 45}" text-anchor="middle">×</text><text class="lab" x="495" y="{y + 45}" text-anchor="middle">→</text>')
        b.append(f'<path class="link" d="M672 {y + 40} C692 {y + 40} 690 172 706 172" marker-end="url(#ah)"/>')
    b.append(f'<circle cx="726" cy="172" r="16" class="box"/><text class="lab" x="726" y="177" text-anchor="middle">+</text>')
    b.append(f'<text class="lab2" x="726" y="208" text-anchor="middle">{t("Residual")}</text>')
    b.append(f'<text class="lab2" x="20" y="312">{t("Key response below 0.4: nothing is written. Above 0.8: exactly the intended amount, never more.")}</text>')
    b.append(f'<text class="lab2" x="20" y="332">{t("Three such pairs per layer, one for each stretch of the reply. What the neurons did before is gone.")}</text>')
    aria = "Two rewritten neurons form one switch. Each gate row holds a key for the scene and a stretch of the reply, shifted by 0.4 or 0.8 times a constant key. Each input row holds the constant key. The output columns hold the direction to write with opposite signs. Their sum writes nothing below a key response of 0.4 and the intended amount above 0.8."
    return svg(W, H, aria, "".join(b))


# ---- 2. 鍵の反応と書く量 -----------------------------------------------------------------------------------------
def fig_curve(ja):
    t = lambda s: esc(tr(s, ja))
    W, H, l, r, tp, bt = 760, 340, 56, 300, 30, 46
    sx = lambda v: l + (v + 1) / 3 * (W - l - r)
    sy = lambda v: tp + (2.5 - v) / 3.5 * (H - tp - bt)
    xs = [-1 + 3 * i / 150 for i in range(151)]
    lin = lambda p: p
    one = lambda p: silu(4 * p) * p / silu(4)
    cap = lambda p: (silu(16 * (p - 0.4)) - silu(16 * (p - 0.8))) / (16 * 0.4)
    path = lambda f: "M" + " L".join(f"{sx(x):.1f} {sy(max(-1, min(2.5, f(x)))):.1f}" for x in xs if -1 <= f(x) <= 2.5)
    b = []
    for v in (-1, 0, 1, 2):
        b.append(f'<line class="grid" x1="{l}" y1="{sy(v)}" x2="{W - r}" y2="{sy(v)}"/><text class="tick" x="{l - 8}" y="{sy(v) + 4}" text-anchor="end">{v}</text>')
        b.append(f'<line class="grid" x1="{sx(v)}" y1="{tp}" x2="{sx(v)}" y2="{H - bt}"/><text class="tick" x="{sx(v)}" y="{H - bt + 18}" text-anchor="middle">{v}</text>')
    b.append(f'<line class="axis" x1="{l}" y1="{sy(0)}" x2="{W - r}" y2="{sy(0)}"/>')
    b.append(f'<path class="line-n2" d="{path(lin)}"/><path class="line-n" d="{path(one)}"/><path class="line-s1" d="{path(cap)}"/>')
    b.append(f'<text class="lab2" x="{W - r + 8}" y="{sy(2) + 4}">{t("Linear write (keyed write)")}</text>')
    b.append(f'<text class="lab2" x="{sx(1.58) + 8}" y="{sy(2.5) + 14}">{t("One neuron alone")}</text>')
    b.append(f'<text class="lab" x="{W - r + 8}" y="{sy(1) + 4}">{t("A pair with a threshold and a cap (used here)")}</text>')
    b.append(f'<text class="tick" x="{sx(-0.95)}" y="{sy(-0.72)}">{t("writes backwards")}</text>')
    b.append(f'<text class="tick" x="{(l + W - r) / 2}" y="{H - 6}" text-anchor="middle">{t("Key response")}</text><text class="tick" x="{l}" y="{tp - 12}">{t("Amount written (1 = the intended amount)")}</text>')
    return svg(W, H, "Amount written against key response. A linear write is proportional and goes negative. One rewritten neuron writes almost nothing below zero and grows quickly above one. A pair of neurons with a cap is near zero below 0.4 and flat at one above 0.8.", "".join(b))


# ---- 3. 位置ごとに書く量 -----------------------------------------------------------------------------------------
def fig_amount(ja):
    t = lambda s: esc(tr(s, ja))
    A = N["amount"]["set2 fish_tuned"]
    dip = 0
    pos = ["0", "1", "2", "3", "4", "5", "6", "7", "8+"]
    W, H, l, tp, bt, gap = 760, 376, 50, 128, 44, 44
    pw = (W - l - gap - 16) / 2
    sy = lambda v: tp + (1.1 - v) / 1.2 * (H - tp - bt)
    b = []
    for k, (title, groups) in enumerate((("Replies to thanks and compliments (100)", ["scene"]), ("Arithmetic, facts, everyday questions, English (130)", ["dont_touch:facts", "dont_touch:ordinary", "dont_touch:english"]))):
        x0 = l + k * (pw + gap)
        sx = lambda i: x0 + 10 + i * (pw - 20) / 8
        b.append(f'<text class="lab" x="{x0}" y="{tp - 26}">{t(title)}</text>')
        for i in (0.5, 3.5):
            b.append(f'<line class="band" x1="{sx(i):.1f}" y1="{tp - 8}" x2="{sx(i):.1f}" y2="{H - bt}"/>')
        for v in (0, 0.5, 1):
            b.append(f'<line class="grid" x1="{x0}" y1="{sy(v)}" x2="{x0 + pw}" y2="{sy(v)}"/>' + (f'<text class="tick" x="{x0 - 8}" y="{sy(v) + 4}" text-anchor="end">{v}</text>' if k == 0 else ""))
        for i, p in enumerate(pos):
            b.append(f'<text class="tick" x="{sx(i)}" y="{H - bt + 18}" text-anchor="middle">{p}</text>')
        b.append(f'<text class="tick" x="{x0 + pw / 2}" y="{H - 6}" text-anchor="middle">{t("Position in the reply (token)")}</text>')
        segs = {s: [sum(A[g][s][p] for g in groups) / len(groups) for p in pos] for s in ("seg0", "seg1", "seg2")}
        if k == 0:
            tot = [sum(segs[s][i] for s in segs) for i in range(9)]
            b.append('<path class="line-tot" d="M' + " L".join(f"{sx(i):.1f} {sy(v):.1f}" for i, v in enumerate(tot)) + '"/>')
            dip = tot[3]
        for s, name, c in (("seg0", "pair for the first token", "s1"), ("seg1", "pair for tokens 1 to 3", "s2"), ("seg2", "pair for token 4 onward", "s3")):
            b.append(f'<path class="{"line-" + c if k == 0 else "line-n"}" d="M' + " L".join(f"{sx(i):.1f} {sy(v):.1f}" for i, v in enumerate(segs[s])) + '"/>')
            for i, v in enumerate(segs[s]):
                if k == 0 and v > 0.2:
                    b.append(f'<circle class="dot-{c}" cx="{sx(i):.1f}" cy="{sy(v):.1f}" r="4"><title>{esc(f"{name}, position {pos[i]}: {v:.2f}")}</title></circle>')
        if k == 1:
            mx = max(abs(v) for s in segs.values() for v in s)
            b.append(f'<text class="lab2" x="{x0 + pw / 2}" y="{sy(0) - 12}" text-anchor="middle">{t("all three stay at 0")} (≤ {mx:.3f})</text>')
    b.append(f'<text class="lab2" x="{l}" y="22">{t("Three pairs of neurons, one per stretch of the reply:")}</text>')
    kx = l
    for name, c in (("pair for the first token", "s1"), ("pair for tokens 1 to 3", "s2"), ("pair for token 4 onward", "s3")):
        lab = tr(name, ja)
        b.append(f'<line class="line-{c}" x1="{kx}" y1="42" x2="{kx + 22}" y2="42"/><circle class="dot-{c}" cx="{kx + 11}" cy="42" r="4"/><text class="key-{c}" x="{kx + 30}" y="46.5">{esc(lab)}</text>')
        kx += 30 + (13.5 if ja else 7.4) * len(lab) + 26
    lab = tr("sum of the three (dips to {v} at token 3)", ja).format(v=f"{dip:.2f}")
    b.append(f'<line class="line-tot" x1="{l}" y1="64" x2="{l + 22}" y2="64"/><text class="lab2" x="{l + 30}" y="68.5">{esc(lab)}</text>')
    b.append(f'<text class="tick" x="{l - 42}" y="{tp - 8}">{t("Share of the intended amount")}</text>')
    return svg(W, H, "Amount written at each reply position. Three pairs of neurons, shown in three colors. In replies to thanks, the first-token pair writes at position 0, the next at positions 1 to 3 and the last from position 4 on, each near the intended amount, with a dip at position 3. In other scenes all three stay at zero.", "".join(b))


# ---- 4. 口調の出方 -----------------------------------------------------------------------------------------------
def tone_rows():
    T = N["target"]
    g = lambda k: T[k]
    return [("No edit", "set 2", g("no_edit|set2|greedy"), "base"), ("No edit", "set 3", g("no_edit|set3|greedy"), "base"),
            ("First form (3 layers)", "set 1", g("fish_first_form|set1|greedy"), "soft"), ("First form (3 layers)", "set 2", g("fish_first_form|set2|greedy"), "soft"),
            ("Tuned form (13 layers)", "set 2", g("fish_tuned|set2|greedy"), "chips"), ("Tuned form (13 layers)", "set 3", g("fish_tuned|set3|greedy"), "chips"),
            ("Tuned form, shuffled key", "set 2", g("fish_tuned_shuffled_key|set2|greedy"), "other"),
            ("System prompt", "set 1", g("system_prompt|set1|greedy"), "other"), ("System prompt", "set 2", g("system_prompt|set2|greedy"), "other"), ("System prompt", "set 3", g("system_prompt|set3|greedy"), "other")]


def fig_tone(ja):
    t = lambda s: esc(tr(s, ja))
    rows = tone_rows()
    W, left, top, rowh = 700, 262, 30, 28
    sx = lambda v: left + v / 100 * (W - left - 44)
    h = top + rowh * len(rows) + 30
    b = [f'<text class="tick" x="{left}" y="16">{t("Replies in the tsundere tone, of 100 (greedy)")}</text>']
    for v in (0, 25, 50, 75, 100):
        b.append(f'<line class="grid" x1="{sx(v)}" y1="{top}" x2="{sx(v)}" y2="{h - 26}"/><text class="tick" x="{sx(v)}" y="{h - 8}" text-anchor="middle">{v}</text>')
    for k, (lab, st, m, kind) in enumerate(rows):
        y = top + k * rowh + 5
        tip = f"{lab}, {st}: {m['tone']} of {m['n']} in tone (95% interval {m['ci'][0]} to {m['ci'][1]}), {m['loop']} fell into repetition"
        cls = "lab" if kind == "chips" else "lab2"
        b.append(f'<text class="{cls}" x="{left - 10}" y="{y + 13}" text-anchor="end">{t(lab)}, {t(st)}</text>')
        b.append(hbar(left, y, sx(m["tone"]), kind, tip))
        b.append(f'<text class="{cls}" x="{sx(m["tone"]) + 7}" y="{y + 13}">{m["tone"]}</text>')
    return svg(W, h, "Replies in the tsundere tone out of 100. No edit 0. First form 27 and 29. Tuned form 53 and 53. Tuned form with a shuffled key 3. System prompt 86, 78 and 87.", "".join(b))


# ---- 5. 返事の内訳 -----------------------------------------------------------------------------------------------
def fig_classes(ja):
    t = lambda s: esc(tr(s, ja))
    T = N["target"]
    rows = [("No edit", "set 2", "greedy", T["no_edit|set2|greedy"]), ("First form (3 layers)", "set 2", "greedy", T["fish_first_form|set2|greedy"]),
            ("Tuned form (13 layers)", "set 2", "greedy", T["fish_tuned|set2|greedy"]), ("Tuned form (13 layers)", "set 3", "greedy", T["fish_tuned|set3|greedy"]),
            ("Tuned form (13 layers)", "set 2", "sampled", T["fish_tuned|set2|sampled_seed0"]), ("Tuned form (13 layers)", "set 3", "sampled", T["fish_tuned|set3|sampled_seed0"]), ("Tuned form (13 layers)", "set 3", "sampled, seed 1", T["fish_tuned|set3|sampled_seed1"]),
            ("Tuned form, shuffled key", "set 2", "greedy", T["fish_tuned_shuffled_key|set2|greedy"]), ("System prompt", "set 2", "greedy", T["system_prompt|set2|greedy"]), ("System prompt", "set 3", "greedy", T["system_prompt|set3|greedy"])]
    cats = [("tone", "in tone", "chips"), ("shy", "shy but plain", "soft"), ("plain", "plain", "other"), ("does_not_fit", "does not fit the prompt", "s3"), ("read_repetition_or_unreadable", "repetition or unreadable", "s2")]
    W, left, top, rowh = 760, 330, 40, 28
    sx = lambda v: left + v / 100 * (W - left - 20)
    h = top + rowh * len(rows) + 30
    b = []
    x = left
    for key, name, kind in cats:                                   # 凡例
        b.append(f'<rect class="bar-{kind}" x="{x - left + 20}" y="8" width="11" height="11" rx="2"/><text class="lab2" x="{x - left + 36}" y="18">{t(name)}</text>')
        x += 24 + (len(tr(name, ja)) * (13.5 if ja else 7.4))
    for v in (0, 25, 50, 75, 100):
        b.append(f'<line class="grid" x1="{sx(v)}" y1="{top}" x2="{sx(v)}" y2="{h - 26}"/><text class="tick" x="{sx(v)}" y="{h - 8}" text-anchor="middle">{v}</text>')
    for k, (lab, st, how, m) in enumerate(rows):
        y = top + k * rowh + 5
        hw = tr("sampled", ja) + ((("、" if ja else ", ") + tr("seed", ja) + " 1") if "seed" in how else "") if "sampled" in how else "greedy"
        b.append(f'<text class="lab2" x="{left - 10}" y="{y + 13}" text-anchor="end">{t(lab)}, {t(st)}, {esc(hw)}</text>')
        acc = 0
        for key, name, kind in cats:
            v = m[key]
            if v:
                x0, x1 = sx(acc) + (1 if acc else 0), sx(acc + v) - 1
                b.append(f'<rect class="bar-{kind}" x="{x0:.1f}" y="{y}" width="{max(x1 - x0, 1):.1f}" height="16" rx="2"><title>{esc(f"{lab}, {st}, {how}: {name} {v} of {m['n']}")}</title></rect>')
                if v >= 9:
                    b.append(f'<text x="{(x0 + x1) / 2:.1f}" y="{y + 12.5}" text-anchor="middle" class="{"inbar-on" if kind in ("chips", "s2", "s3") else "inbar"}">{v}</text>')
            acc += v
    return svg(W, h, "How blind readers sorted 100 replies per condition into five classes: in tone, shy but plain, plain, does not fit the prompt, repetition or unreadable.", "".join(b))


# ---- 6. 狙っていない場面の正答 -----------------------------------------------------------------------------------
def fig_other(ja):
    t = lambda s: esc(tr(s, ja))
    O = N["other"]
    rows = []
    for s, fish in ((1, "fish_first_form"), (2, "fish_tuned"), (3, "fish_tuned")):
        rows += [("No edit", f"set {s}", O[f"no_edit|set{s}|greedy"], "base"), ("FiSH", f"set {s}", O[f"{fish}|set{s}|greedy"], "chips"), ("System prompt", f"set {s}", O[f"system_prompt|set{s}|greedy"], "other")]
    W, left, top, rowh = 700, 230, 30, 26
    sx = lambda v: left + v / 50 * (W - left - 44)
    h = top + rowh * len(rows) + 16 * 2 + 30
    b = [f'<text class="tick" x="{left}" y="16">{t("Correct answers, of 50 arithmetic and fact questions (greedy)")}</text>']
    for v in (0, 10, 20, 30, 40, 50):
        b.append(f'<line class="grid" x1="{sx(v)}" y1="{top}" x2="{sx(v)}" y2="{h - 26}"/><text class="tick" x="{sx(v)}" y="{h - 8}" text-anchor="middle">{v}</text>')
    for k, (lab, st, m, kind) in enumerate(rows):
        y = top + k * rowh + (k // 3) * 16 + 5
        name = tr(lab, ja) + ((("(最初の形)" if ja else " (first form)") if st == "set 1" else ("(改良した形)" if ja else " (tuned form)")) if lab == "FiSH" else "")
        cls = "lab" if kind == "chips" else "lab2"
        b.append(f'<text class="{cls}" x="{left - 10}" y="{y + 13}" text-anchor="end">{esc(name)}, {t(st)}</text>')
        b.append(hbar(left, y, sx(m["facts_correct"]), kind, f"{lab}, {st}: {m['facts_correct']} of 50 correct"))
        b.append(f'<text class="{cls}" x="{sx(m["facts_correct"]) + 7}" y="{y + 13}">{m["facts_correct"]}</text>')
    return svg(W, h, "Correct answers out of 50 arithmetic and fact questions on three question sets. No edit 46 each time. FiSH 46, 47 and 46. System prompt 38, 41 and 41.", "".join(b))


# ---- 7. 層と強さの探索 -------------------------------------------------------------------------------------------
def fig_layers(ja):
    t = lambda s: esc(tr(s, ja))
    D = {}
    for nm in ("B0", "Ltop8", "L16_30", "Lall", "L11_23", "D07", "D11", "E2"):
        a, c = NB.jl(NB.CASE / f"search/direct_add.a.{nm}.greedy.json")["summary"], NB.jl(NB.CASE / f"search/direct_add.a.{nm}.sampled_seed0.json")["summary"]
        D[nm] = (a["in_tone_and_not_repeating"] + c["in_tone_and_not_repeating"], a["repeating_loose_count"] + c["repeating_loose_count"])
    rows = [("3 layers: 11, 18, 23", "B0"), ("8 layers: 16 to 23", "Ltop8"), ("15 layers: 16 to 30", "L16_30"), ("30 layers: 1 to 30", "Lall"), ("13 layers: 11 to 23", "L11_23"),
            ("13 layers, strength 0.7", "D07"), ("13 layers, strength 1.1", "D11"), ("13 layers, strength 1 / 1 / 0.8", "E2")]
    W, left, top, rowh = 700, 250, 46, 34
    sx = lambda v: left + v / 120 * (W - left - 44)
    h = top + rowh * len(rows) + 30
    b = [f'<text class="tick" x="{left}" y="14">{t("Search questions, 120 replies each, scored by the model itself")}</text>',
         f'<rect class="bar-chips" x="{left}" y="24" width="11" height="11" rx="2"/><text class="lab2" x="{left + 16}" y="34">{t("in tone and not repeating")}</text>',
         f'<rect class="bar-s2" x="{left + (250 if ja else 200)}" y="24" width="11" height="11" rx="2"/><text class="lab2" x="{left + (266 if ja else 216)}" y="34">{t("repeating")}</text>']
    for v in (0, 30, 60, 90, 120):
        b.append(f'<line class="grid" x1="{sx(v)}" y1="{top}" x2="{sx(v)}" y2="{h - 26}"/><text class="tick" x="{sx(v)}" y="{h - 8}" text-anchor="middle">{v}</text>')
    for k, (lab, nm) in enumerate(rows):
        y = top + k * rowh + 4
        a, c = D[nm]
        cls = "lab" if nm == "E2" else "lab2"
        b.append(f'<text class="{cls}" x="{left - 10}" y="{y + 15}" text-anchor="end">{t(lab)}</text>')
        b.append(hbar(left, y, sx(a), "chips" if nm == "E2" else "soft", f"{lab}: {a} of 120 in tone and not repeating", 12) + f'<text class="{cls}" x="{sx(a) + 7}" y="{y + 11}">{a}</text>')
        b.append(hbar(left, y + 14, sx(c), "s2", f"{lab}: {c} of 120 repeating", 8) + f'<text class="tick" x="{sx(c) + 7}" y="{y + 23}">{c}</text>')
    return svg(W, h, "Search over layers and strengths on the search questions, 120 replies each, scored by the model itself. Three spread layers 40 in tone. Thirteen consecutive layers 70. With strength 1, 1, 0.8 it is 77 with 5 repeating. Strength 1.1 gives 82 but 19 repeating.", "".join(b)), D


# ---- 8. 2 つのモデル: 口調と、うまくいかなかった返事 ---------------------------------------------------------
def fig_models(ja):
    t = lambda s: esc(tr(s, ja))
    T, M = N["target"], N["m27"]["target"]
    groups = [("Qwen3.5-4B (set 2)", [("No edit", T["no_edit|set2|greedy"], "base"), ("FiSH", T["fish_tuned|set2|greedy"], "chips"), ("FiSH, shuffled key", T["fish_tuned_shuffled_key|set2|greedy"], "other"), ("System prompt", T["system_prompt|set2|greedy"], "other")]),
              ("Swift-1.5-Qwen3.8-27B", [("No edit", M["no_edit|greedy"], "base"), ("FiSH", M["fish|greedy"], "chips"), ("FiSH, shuffled key", M["fish_shuffled_key|greedy"], "other"), ("System prompt", M["system_prompt|greedy"], "other")])]
    W, left, top, rowh = 760, 190, 64, 36
    sx = lambda v: left + v / 100 * (W - left - 44)
    h = top + sum(len(g[1]) for g in groups) * rowh + 30 * 2 + 20
    b = [f'<text class="tick" x="{left}" y="14">{t("Replies to thanks and compliments, of 100 (greedy)")}</text>',
         f'<rect class="bar-chips" x="{left}" y="24" width="11" height="11" rx="2"/><text class="lab2" x="{left + 16}" y="34">{t("in tone")}</text>',
         f'<rect class="bar-s2" x="{left + 130}" y="24" width="11" height="11" rx="2"/><text class="lab2" x="{left + 146}" y="34">{t("repetition or unreadable + does not fit")}</text>']
    y = top
    for title, rows in groups:
        b.append(f'<text class="lab" x="20" y="{y + 4}">{t(title)}</text>')
        y += 14
        for lab, m, kind in rows:
            bad = m["read_repetition_or_unreadable"] + m["does_not_fit"]
            cls = "lab" if kind == "chips" else "lab2"
            b.append(f'<text class="{cls}" x="{left - 10}" y="{y + 15}" text-anchor="end">{t(lab)}</text>')
            b.append(hbar(left, y, sx(m["tone"]), kind if kind != "base" else "base", f"{title}, {lab}: {m['tone']} of 100 in tone", 13) + f'<text class="{cls}" x="{sx(m["tone"]) + 7}" y="{y + 11}">{m["tone"]}</text>')
            b.append(hbar(left, y + 15, sx(bad), "s2", f"{title}, {lab}: {m['read_repetition_or_unreadable']} repetition or unreadable, {m['does_not_fit']} not fitting the prompt", 8) + f'<text class="tick" x="{sx(bad) + 7}" y="{y + 24}">{bad}</text>')
            y += rowh
        y += 24
    for v in (0, 25, 50, 75, 100):
        b.append(f'<line class="grid" x1="{sx(v)}" y1="{top - 10}" x2="{sx(v)}" y2="{h - 26}"/><text class="tick" x="{sx(v)}" y="{h - 8}" text-anchor="middle">{v}</text>')
    return svg(W, h, "Replies in tone and replies that went wrong, of 100, on two models. On the 4B model a shuffled key gives 3 in tone and 92 that went wrong. On the 27B model a shuffled key gives 70 in tone, more than the real key at 55, with 30 that went wrong against 10.", "".join(b))


# ---- 9. 27B: 狙っていない場面 ------------------------------------------------------------------------------------
def fig_other27(ja):
    t = lambda s: esc(tr(s, ja))
    O = N["m27"]["other"]
    conds = [("No edit", "no_edit|greedy", "base"), ("FiSH", "fish|greedy", "chips"), ("FiSH, shuffled key", "fish_shuffled_key|greedy", "other"), ("System prompt", "system_prompt|greedy", "other")]
    panels = [("Replies that start like the unedited model's (first 30 characters)", lambda o, k: 80 if k == "no_edit|greedy" else sum(o["same_start30"].values()), 80),
              ("Replies in the tone (scored by the model)", lambda o, k: o["model_tone"], 80), ("Correct answers, of 30 arithmetic and fact questions", lambda o, k: o["facts_correct"], 30)]
    W, left, rowh = 760, 190, 24
    h = 30 + len(panels) * (len(conds) * rowh + 44)
    b = [f'<text class="lab" x="20" y="18">{t("27B, 80 unrelated prompts (greedy)")}</text>']
    y = 34
    for title, f, mx in panels:
        sx = lambda v: left + v / mx * (W - left - 60)
        b.append(f'<text class="tick" x="{left}" y="{y + 10}">{t(title)}</text>')
        y += 18
        for lab, k, kind in conds:
            v = f(O[k], k)
            cls = "lab" if kind == "chips" else "lab2"
            b.append(f'<text class="{cls}" x="{left - 10}" y="{y + 13}" text-anchor="end">{t(lab)}</text>' + hbar(left, y, sx(v), kind, f"{lab}: {v} of {mx}") + f'<text class="{cls}" x="{sx(v) + 7}" y="{y + 13}">{v}</text>')
            y += rowh
        y += 26
    return svg(W, h, "On 80 unrelated prompts on the 27B model. Replies starting like the unedited model's: FiSH 70, shuffled key 29, system prompt 0. Replies in tone: 0, 0, 1 and 79. Correct answers of 30: 29, 28, 28 and 25.", "".join(b))


FIGS = [("01_neuron", fig_neuron), ("02_curve", fig_curve), ("03_amount", fig_amount), ("04_tone", fig_tone), ("05_classes", fig_classes), ("06_other", fig_other), ("07_layers", lambda ja: fig_layers(ja)[0]), ("08_models", fig_models), ("09_other27", fig_other27)]
if __name__ == "__main__":
    for name, f in FIGS:
        for ja in (False, True):
            p = OUT / f"{name}.{'ja' if ja else 'en'}.svg"
            p.write_text(f(ja), encoding="utf-8")
            print("wrote", p.name, p.stat().st_size)
    print("search, of 120 replies (in tone and not repeating, repeating):", fig_layers(False)[1])
