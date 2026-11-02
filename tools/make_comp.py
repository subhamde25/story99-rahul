# usage: [RES=4k] python -I tools/make_comp.py  -> film/index.html + build/sfx_cues.json
# One paused GSAP timeline drives everything. Every graphic cue comes from a word in build/words.json, so a re-cut moves the graphics with it.
# Every seam between scenes gets its own transition, caused by something on screen. Every sound may be used at most twice (asserted at the end).
import json, os, random
AROLL = 'assets/aroll4k.mp4' if os.environ.get('RES') == '4k' else 'assets/aroll.mp4'
TL = json.load(open('build/timeline.json')); WORDS = json.load(open('build/words.json'))
TOTAL = TL['total']; VID = sum(s['f'] for s in TL['shots']) / TL['fps']
LINES = {l['id']: l for l in TL['lines']}

# whisper collapses some runs of words onto one instant: spread those runs across the time they really have
by = {}
for w in WORDS: by.setdefault(w['line'], []).append(w)
for lid, ws in by.items():
    i = 0
    while i < len(ws):
        j = i
        while j + 1 < len(ws) and ws[j + 1]['start'] - ws[j]['start'] < 0.04: j += 1
        if j - i >= 2 or (j == len(ws) - 1 and j > i):
            a = ws[i]['start']; b = ws[j + 1]['start'] if j + 1 < len(ws) else LINES[lid]['end'] - 0.1
            lens = [max(2, len(x['text'])) for x in ws[i:j + 1]]; c = a; tot = sum(lens)
            for x, n_ in zip(ws[i:j + 1], lens): x['start'] = round(c, 3); c += (b - a) * n_ / tot
        i = j + 1
for ws in by.values():
    for a, b in zip(ws, ws[1:]):
        if b['start'] < a['start']: b['start'] = a['start']

def T(lid, i=0):
    "start time of word i of a line (negative i counts from the end)"
    return by[lid][i]['start']
def LS(lid): return LINES[lid]['start']
def LE(lid): return LINES[lid]['hold_end']
def B(lid, k):
    "edit time where kept range k of a line starts: the jump cuts a cutaway can hide"
    return LS(lid) + sum(b - a for a, b in LINES[lid]['ranges'][:k])

BLUE, ACC, AMB, INK, DARK, DCARD, TINT = '#006EDA', '#2699FB', '#E0952B', '#16191D', '#1B1B1B', '#27333C', '#EAF3FC'
SOFT_BLUE = '#8FC4F7'
html, js, sfx = [], [], []
def n(v): return round(v, 3)
def to(sel, t, **kw): js.append(f'A({json.dumps(sel)},{json.dumps(kw)},{n(t)});')
def st(sel, **kw): js.append(f'S({json.dumps(sel)},{json.dumps(kw)});')
def setv(sel, t, **kw): js.append(f'tl.set({json.dumps(sel)},{json.dumps(kw)},{n(t)});')
def hit(t, name, gain=-10.0, pan=0.0, pan_to=None):
    sfx.append({'t': n(t), 'file': name, 'gain': gain, 'pan': pan, 'pan_to': pan if pan_to is None else pan_to})
def fade(sel, t, d=0.35, **kw):
    st(sel, opacity=0); to(sel, t, opacity=1, duration=d, ease='power2.out', **kw)
def rise(sel, t, d=0.7, y=26, **kw):
    st(sel, opacity=0, y=y); to(sel, t, opacity=1, y=0, duration=d, ease='expo.out', **kw)
def flip(sel, t, d=0.8, **kw):
    "card swings up from lying flat"
    st(sel, opacity=0, rotationX=-62, y=40, transformPerspective=1200, transformOrigin='50% 100%')
    to(sel, t, opacity=1, rotationX=0, y=0, duration=d, ease='back.out(1.5)', **kw)
def swing(sel, t, d=0.65, dx=-70, **kw):
    "chip arrives sideways with a lean that straightens"
    st(sel, opacity=0, x=dx, skewX=14)
    to(sel, t, opacity=1, x=0, skewX=0, duration=d, ease='expo.out', **kw)
def pop(sel, t, d=0.55, s=0.55, ease='back.out(2.2)', origin='50% 50%'):
    st(sel, opacity=0, scale=s, transformOrigin=origin)
    to(sel, t, opacity=1, scale=1, duration=d, ease=ease)
def draw(sel, t, d=0.6, ease='power2.inOut', **kw):
    st(sel, strokeDasharray=1000, strokeDashoffset=1000, opacity=0); setv(sel, t, opacity=1); to(sel, t, strokeDashoffset=0, duration=d, ease=ease, **kw)
def words(text, cls):
    out = []
    for ln in text.split('\n'):
        out.append(' '.join(f'<span class="mw"><span class="{cls}">{x}</span></span>' for x in ln.split(' ')))
    return '<br>'.join(out)
def head(cls, t):
    "headline words rise out of a mask, leaning in as they land"
    st('.' + cls, yPercent=118, rotation=7, transformOrigin='0% 100%')
    to('.' + cls, t, yPercent=0, rotation=0, duration=0.8, ease='expo.out', stagger=0.05)
def eyebrow(sel, t):
    st(sel, opacity=0, x=-34, letterSpacing='.22em')
    to(sel, t, opacity=1, x=0, letterSpacing='.015em', duration=0.7, ease='expo.out')
def smear(sel, t, d, axis='x'):
    "directional motion blur that peaks mid-move and clears: a stepped SVG blur, so it is exact on every frame"
    a = 'm' + axis
    for f, lv in ((0, 1), (.14, 2), (.3, 3), (.58, 2), (.8, 1)):
        setv(sel, t + f * d, filter=f'url(#{a}{lv})')
    setv(sel, t + d, filter='none')
def shake(sel, t, amp=7, d=0.32, steps=6):
    for i in range(steps):
        k = 1 - i / steps; s_ = (-1) ** i
        to(sel, t + i * d / steps, x=s_ * amp * k, y=-s_ * amp * k * .6, duration=d / steps, ease='sine.inOut')
    to(sel, t + d, x=0, y=0, duration=0.04, ease='none')
def punch(t, s=1.07):
    "the camera kicks in on a word and settles back"
    to('#cam3', t, scale=s, duration=0.1, ease='power3.out'); to('#cam3', t + 0.1, scale=1.012, duration=0.6, ease='power2.inOut')
def enter_zoom(t, s=1.16):
    setv('#cam3', t, scale=s); to('#cam3', t + 0.005, scale=1.012, duration=0.75, ease='expo.out')

def icon(name, size=40, sw=2.0, color='currentColor'):
    P = {
     'person': '<circle cx="12" cy="8" r="4"/><path d="M4 21c0-4.4 3.6-7 8-7s8 2.6 8 7"/>',
     'net': '<circle cx="12" cy="4" r="2"/><circle cx="4" cy="12" r="2"/><circle cx="20" cy="12" r="2"/><circle cx="8" cy="20" r="2"/><circle cx="16" cy="20" r="2"/><path d="M12 6l-7 5M12 6l7 5M5 13.5l3 5M19 13.5l-3 5M10 20h4M12 6l-4 12M12 6l4 12"/>',
     'chart': '<path d="M4 20V10M10 20V5M16 20v-7M22 20H2"/>',
     'edit': '<path d="M4 20h4L19 9l-4-4L4 16v4zM13.5 6.5l4 4"/>',
     'flag': '<path d="M5 22V3M5 4h13l-3 4 3 4H5"/>',
     'alert': '<path d="M12 3L2 21h20L12 3zM12 10v5M12 18v.5"/>',
     'q': '<circle cx="12" cy="12" r="10"/><path d="M9 9.5a3 3 0 1 1 4.5 2.6c-1 .6-1.5 1.2-1.5 2.4M12 17.6v.4"/>',
     'down': '<path d="M17 3h3v11h-3zM17 13l-4 8c-1.6 0-2.5-1-2.5-2.5V15H5a2 2 0 0 1-2-2.3l1-7A2.5 2.5 0 0 1 6.5 3.5H17"/>',
     'up': '<path d="M7 21H4V10h3zM7 11l4-8c1.6 0 2.5 1 2.5 2.5V9H19a2 2 0 0 1 2 2.3l-1 7a2.5 2.5 0 0 1-2.5 2.2H7"/>',
     'doc': '<path d="M6 2h9l5 5v15H6zM14 2v6h6M9 13h8M9 17h8"/>',
     'grad': '<path d="M2 9l10-5 10 5-10 5zM6 11.5V17c2 2 10 2 12 0v-5.5"/>',
     'brief': '<rect x="3" y="7" width="18" height="13" rx="2"/><path d="M9 7V4h6v3M3 13h18"/>',
     'spark': '<path d="M12 2l2.2 6.8L21 11l-6.8 2.2L12 20l-2.2-6.8L3 11l6.8-2.2z"/>',
     'check': '<path d="M4 12.5l5.5 5.5L20 6.5"/>',
     'x': '<path d="M5 5l14 14M19 5L5 19"/>',
     'search': '<circle cx="11" cy="11" r="7"/><path d="M16 16l5 5"/>',
     'target': '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1"/>',
     'cal': '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M3 10h18M8 3v4M16 3v4"/>',
     'road': '<path d="M8 3L4 21M16 3l4 18M12 4v3M12 11v3M12 18v3"/>',
     'store': '<path d="M4 10v11h16V10M2 10l2-7h16l2 7c0 1.5-1.5 2.5-3 2.5S16 11.5 16 10c0 1.5-2 2.5-4 2.5S8 11.5 8 10c0 1.5-1.5 2.5-3 2.5S2 11.5 2 10zM10 21v-5h4v5"/>',
    }[name]
    return f'<svg class="ic" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="{sw}" stroke-linecap="round" stroke-linejoin="round">{P}</svg>'

# ---- slider: the film's spine. Replaces people > changes roles > new capability. One instance per panel; dot positions carry across scenes.
STOPS = ['REPLACES PEOPLE', 'CHANGES ROLES', 'NEW CAPABILITY']
def slider(pid, x, y, w, dark=False, p=0.0):
    col = '#9AA5AE' if dark else '#55606B'; line = '#3A444C' if dark else '#CFDBE6'
    labs = ''.join(f'<div class="sl-lab" id="{pid}-l{i}" style="left:{w * i / 2 if i == 1 else (0 if i == 0 else w)}px;color:{col};transform-origin:left;'
                   + ('text-align:left;' if i == 0 else 'text-align:center;margin-left:-160px;width:320px;' if i == 1 else 'text-align:right;margin-left:-320px;width:320px;') + f'">{STOPS[i]}</div>' for i in range(3))
    ticks = ''.join(f'<div class="sl-tick" style="left:{w * i / 2 - 1}px;background:{line}"></div>' for i in range(3))
    st(f'#{pid}-dot', x=w * p); st(f'#{pid}-fill', scaleX=p, transformOrigin='0% 50%')
    return (f'<div class="sl" id="{pid}" style="left:{x}px;top:{y}px;width:{w}px">{labs}<div class="sl-line" style="background:{line}"></div>'
            f'<div class="sl-fill" id="{pid}-fill"></div>{ticks}<div class="sl-dot" id="{pid}-dot"></div></div>')
def slide_dot(pid, t, w, p, d=0.95):
    to(f'#{pid}-dot', t, x=w * p, duration=d, ease='back.inOut(1.3)'); to(f'#{pid}-fill', t, scaleX=p, duration=d, ease='back.inOut(1.3)')
def sl_active(pid, i, t, dark=False):
    to(f'#{pid}-l{i}', t, color=ACC if dark else BLUE, duration=0.3, ease='power1.out')

# ---- camera states. aroll puts the face at (854, 562) on every shot, so three transforms cover all layouts.
FACE = (854, 562)
def cam_state(kind):
    if kind == 'full': return dict(scale=1, x=0, y=0)
    fx = 430 if kind == 'left' else 1490                            # same size as full frame: the whole head and shoulders stay in the speaker's box
    return dict(scale=1, x=round(fx - FACE[0]), y=0)
def cam(kind, t, d=0.6, ease='expo.inOut'): to('#cam', t, duration=d, ease=ease, **cam_state(kind))
def cam_cut(kind, t): to('#cam', t, duration=0.005, ease='none', **cam_state(kind))
def logo(t, state, d=0.5):
    S_ = {'foot': dict(x=0, y=0, scale=1), 'panel': dict(x=-20, y=20, scale=0.82), 'mirror': dict(x=-844, y=20, scale=0.82)}[state]
    to('#logo', t, duration=d, ease='power3.inOut', **S_)
def logo_theme(t, dark, d=0.25):
    to('#logo-d', t, opacity=0 if dark else 1, duration=d, ease='none'); to('#logo-w', t, opacity=1 if dark else 0, duration=d, ease='none')
def wm(t, dark, d=0.25):
    "dark = dark mark, for white panels"
    to('#wm-d', t, opacity=0.5 if dark else 0, duration=d, ease='none'); to('#wm-w', t, opacity=0 if dark else 0.85, duration=d, ease='none')
def name_full(t, on, d=0.25):
    to('#nameband', t, opacity=1 if on else 0, duration=d, ease='none')
def pill(t, on, side='left', d=0.3):
    if on: setv('#pill', t, x=0 if side == 'left' else 1060); to('#pill', t + 0.25, opacity=1, duration=d, ease='power2.out')
    else: to('#pill', t, opacity=0, duration=0.15, ease='none')
def scene(sid, start, dur, inner, cls='', style='', z=10):
    html.append(f'<div id="{sid}" class="clip scene" style="z-index:{z}" data-start="{n(start)}" data-duration="{n(dur)}" data-track-index="5"><div class="slide {cls}" id="{sid}-s" style="{style}">{inner}</div></div>')

# ---- global wipes
BL = 8
blinds_html = '<div id="blinds">' + ''.join(f'<div class="bl" style="left:{i * 240}px;background:{BLUE if i % 2 == 0 else "#0B5FC4"}"></div>' for i in range(BL)) + '</div>'
st('.bl', scaleY=0, transformOrigin='50% 0%')
def blinds(tc, d=0.24, stag=0.028):
    "vertical strips close over the frame at tc, whatever is swapped under them at tc is revealed as they open from the other end"
    span = d + stag * (BL - 1)
    to('.bl', tc - span, scaleY=1, duration=d, ease='power3.inOut', stagger=stag)
    setv('.bl', tc + 0.004, transformOrigin='50% 100%')
    to('.bl', tc + 0.01, scaleY=0, duration=d, ease='power3.inOut', stagger=stag)

# ==================================================================== COLD OPEN
st('#cam', scale=1, x=0, y=0, transformOrigin='0 0')
st('#cam2', scale=1, transformOrigin=f'{FACE[0]}px {FACE[1]}px'); st('#cam3', scale=1.012, transformOrigin=f'{FACE[0]}px {FACE[1]}px')
DRIFT = [('agency', 1, 1.035), ('agents', 1.04, 1.0), ('stigma', 1, 1.03), ('pov', 1, 1.04), ('organ', 1, 1.04), ('corner', 1.03, 1), ('works', 1, 1.04), ('jobloss', 1, 1.03), ('analytics', 1, 1.03), ('notposs', 1.02, 1.04), ('now', 1, 1.06)]
for lid, a, b in DRIFT:
    setv('#cam2', LS(lid), scale=a); to('#cam2', LS(lid) + 0.004, scale=b, duration=LE(lid) - LS(lid) - 0.01, ease='none')
tq = LS('title')
setv('#cam2', LS('everything'), scale=1); to('#cam2', LS('everything') + 0.004, scale=1.07, duration=tq - 0.5 - LS('everything'), ease='none')
to('#cam2', tq - 0.48, scale=1.42, duration=0.5, ease='power3.in')          # the shot accelerates into the title
to('#camwrap', tq - 0.26, filter='blur(16px)', duration=0.28, ease='power2.in')
to('#camwrap', tq + 0.5, filter='blur(0px)', duration=0.01, ease='none')
setv('#cam2', tq + 0.5, scale=1)
hit(tq - 1.5, 'air_suck', -9)

# ==================================================================== TITLE
t0 = tq; tx = LS('stigma') - 0.5
random.seed(11)
nodes = [(random.randint(40, 1880), random.randint(30, 1050)) for _ in range(46)]
def net_svg(idn, stroke, dot):
    edges = []
    for i, (ax, ay) in enumerate(nodes):
        near = sorted(range(len(nodes)), key=lambda j: (nodes[j][0] - ax) ** 2 + (nodes[j][1] - ay) ** 2)[1:3]
        for j in near: edges.append(f'<line x1="{ax}" y1="{ay}" x2="{nodes[j][0]}" y2="{nodes[j][1]}"/>')
    return f'<svg id="{idn}" class="netsvg" width="1920" height="1080" viewBox="0 0 1920 1080"><g stroke="{stroke}" stroke-width="1.2">' + ''.join(edges) + f'</g><g fill="{dot}">' + ''.join(f'<circle cx="{x}" cy="{y}" r="{2 + (i % 3)}"/>' for i, (x, y) in enumerate(nodes)) + '</g></svg>'
scene('title', t0 - 0.16, tx + 0.56 - (t0 - 0.16), f'''{net_svg("t-net", "#DCE6EF", "#CFDCE8")}
<div id="t-ring" class="tring"></div><div id="t-ring2" class="tring"></div>
<div id="t-lockup"><div id="t-icon-wrap"><img id="t-icon" src="assets/logo.svg"></div></div>
<div id="t-name">{words("AI Field Notes", "tw")}</div><div id="t-rule"></div><div id="t-sub">Rahul Thota &nbsp;·&nbsp; CEO, Akaike</div>
<div id="t-dot"></div>''', cls='white', z=20)
st('#title-s', opacity=0); to('#title-s', t0 - 0.14, opacity=1, duration=0.16, ease='power2.in')
st('#t-net', opacity=0, scale=1.3, transformOrigin='44% 37%'); to('#t-net', t0, opacity=0.8, scale=1, duration=1.5, ease='expo.out')
st('#t-icon-wrap', clipPath='inset(-10% 74% -10% -10%)', opacity=0, scale=0.62, transformOrigin='14% 50%')
to('#t-icon-wrap', t0 + 0.02, opacity=1, scale=1, duration=0.75, ease='back.out(2)')
to('#t-icon-wrap', t0 + 0.28, clipPath='inset(-10% -10% -10% -10%)', duration=0.6, ease='power3.inOut')
for r_, dl in (('#t-ring', 0.03), ('#t-ring2', 0.16)):
    st(r_, opacity=0, scale=0.2, transformOrigin='50% 50%'); to(r_, t0 + dl, opacity=0.5, duration=0.06); to(r_, t0 + dl + 0.06, opacity=0, scale=3.4, duration=1.0, ease='expo.out')
head('tw', t0 + 0.62)
st('#t-rule', scaleX=0); to('#t-rule', t0 + 1.02, scaleX=1, duration=0.5, ease='expo.out')
rise('#t-sub', t0 + 1.14, 0.6, y=18)
st('#t-dot', opacity=0, scale=1, transformOrigin='50% 50%'); setv('#t-dot', tx, opacity=1)
to('#t-dot', tx, scale=56, duration=0.5, ease='power3.in')                  # the logo's blue dot becomes the frame
setv('#title-s', tx + 0.5, opacity=0)
st('#flash', opacity=0); setv('#flash', tx + 0.5, opacity=1); to('#flash', tx + 0.505, opacity=0, duration=0.3, ease='power2.out')
enter_zoom(tx + 0.5)
to('#logo', t0 - 0.12, opacity=0, duration=0.1); to('#logo', tx + 0.5, opacity=1, duration=0.15); wm(t0 - 0.12, True, 0.1); wm(tx + 0.5, False, 0.15); name_full(t0 - 0.12, False, 0.1); name_full(tx + 0.5, True, 0.1)
hit(t0 + 0.02, 'subhit', -3); hit(tx - 0.08, 'zoom_fly', -8)

# ==================================================================== FEAR (speaker left): panel whips in from the right
t0 = LS('genpop'); t1 = LE('afraid'); PW = 1060
ROWS, COLS = 5, 20
people = ''
for r in range(ROWS):
    for c in range(COLS):
        cl = 'ppl ds' if (c >= 18 and r <= 1) else 'ppl gp'
        people += f'<g transform="translate({c * 46},{r * 46})"><g class="{cl}"><circle cx="16" cy="9" r="8"/><path d="M1 36c0-11 6-16 15-16s15 5 15 16z"/></g></g>'
fear = f'''
<div class="eyebrow" id="f-eb" style="left:70px;top:112px">Where the fear sits</div>
<div class="h1" style="left:70px;top:152px;font-size:54px">{words("Not the data scientists.\nEveryone else.", "fw")}</div>
<div class="tag" id="f-gp" style="left:70px;top:318px;color:#B8761A">General population</div>
<div class="tag" id="f-ds" style="right:70px;top:318px;color:{BLUE}">Data science community</div>
<svg id="f-grid" width="920" height="236" style="left:70px;top:352px;overflow:visible" viewBox="0 0 920 236">{people}</svg>
<div class="scard" id="f-c1g" style="left:70px;top:640px;width:450px"><div class="sq t">{icon('grad', 40, color=BLUE)}</div><div><div class="sm" style="color:{BLUE}">Group 01</div><div class="ct" style="color:#5C6670">Entering the<br>workforce</div></div></div>
<div class="scard blue" id="f-c1" style="left:70px;top:640px;width:450px"><div class="sq">{icon('grad', 40)}</div><div><div class="sm">Group 01</div><div class="ct">Entering the<br>workforce</div></div></div>
<div class="scard blue" id="f-c2" style="left:540px;top:640px;width:450px"><div class="sq">{icon('brief', 40)}</div><div><div class="sm">Group 02</div><div class="ct">Already inside<br>companies</div></div></div>
<div class="bubble" id="f-q">What is going to happen to us?<i></i></div>
''' + slider('f-sl', 70, 960, 830, p=0.0)
scene('fear', t0 - 0.12, t1 - t0 + 0.2, fear, cls='white dots', style=f'left:860px;width:{PW}px')
st('#fear-s', x=PW); to('#fear-s', t0 - 0.12, x=0, duration=0.62, ease='expo.out'); smear('#fear-s', t0 - 0.12, 0.34)
cam('left', t0 - 0.12, 0.55, 'expo.out'); logo(t0 - 0.12, 'panel'); wm(t0 + 0.1, True); name_full(t0 - 0.12, False); pill(t0, True)
hit(t0 - 0.14, 'silk_swipe', -8, 0.6, 0)
eyebrow('#f-eb', t0 + 0.3); head('fw', t0 + 0.38)
rise('#f-gp', T('genpop', 4), 0.5, y=12)
st('.ppl', fill='#DCE4EB', opacity=0, scale=0.2, transformOrigin='50% 100%')
to('.ppl', t0 + 0.5, opacity=1, scale=1, duration=0.5, ease='back.out(2.4)', stagger=dict(grid=[ROWS, COLS], amount=0.75, **{'from': 'center'}))
tds = T('notds', 5)
to('.ds', tds, fill=BLUE, scale=1.28, duration=0.22, ease='power2.out'); to('.ds', tds + 0.22, scale=1, duration=0.4, ease='back.out(2)'); rise('#f-ds', tds, 0.5, y=12); hit(tds, 'felt_tap', -11)
tf = T('fearfrom', 1)
GS = dict(grid=[ROWS, COLS], amount=0.65, **{'from': 'end'})
to('.gp', tf, fill='#EDB25C', scale=1.24, duration=0.2, ease='power2.out', stagger=GS); to('.gp', tf + 0.2, scale=1, duration=0.3, ease='power2.out', stagger=GS)
hit(tf - 0.1, 'uneasy_swell', -13)
flip('#f-c1', T('workforce', 4)); hit(T('workforce', 4) + 0.02, 'marimba', -13)
to('#f-c1', T('workforce', 12), opacity=0, duration=0.3, ease='none'); fade('#f-c1g', T('workforce', 12), 0.3)
flip('#f-c2', T('workforce', 12)); hit(T('workforce', 12) + 0.02, 'kalimba', -13)
st('#f-q', opacity=0, scale=0.5, rotation=-4, transformOrigin='50% 110%'); to('#f-q', T('afraid', 7) - 0.15, opacity=1, scale=1, rotation=0, duration=0.6, ease='back.out(2.2)'); hit(T('afraid', 7) - 0.15, 'soft_pop', -12)
sl_active('f-sl', 0, t0 + 0.6)
# exit: blinds close over the panel, the POV line is under them when they open
te = LS('pov') - 0.1
blinds(te); hit(te - 0.34, 'shutter_roll', -10)
setv('#fear-s', te, opacity=0); cam_cut('full', te); logo(te, 'foot', 0.3); wm(te, False, 0.05); pill(te - 0.02, False); name_full(te, True, 0.05)

# ==================================================================== LOOP (full white): a ring opens out of the word "loop"
t0 = LS('role'); t1 = LE('improve'); IR = (1700, 720)
RET = 'M1590 700 V790 Q1590 826 1554 826 H366 Q330 826 330 790 V712'
FULLP = 'M540 575 H750 L1170 575 H1380 L1590 575 L1590 790 Q1590 826 1554 826 H366 Q330 826 330 790 L330 575 L540 575'
bars = ''.join(f'<div class="minibar" id="l-b{i}" style="left:{28 + i * 62}px;height:{h}px"></div>' for i, h in enumerate([34, 52, 66, 84, 100, 118]))
rows = ''.join(f'<div class="lrow" id="l-r{i}" style="top:{94 + i * 40}px"><div class="lln" style="width:{w}px"></div><div class="lst" id="l-s{i}">{icon("check", 22, 3, color=c)}</div></div>' for i, (w, c) in enumerate([(250, BLUE), (210, BLUE), (280, AMB)]))
loop = f'''
<div class="eyebrow" id="l-eb" style="left:100px;top:96px">My point of view</div>
<div class="h1" style="left:100px;top:138px;font-size:68px" id="l-h">{words("Still in the loop.\nIn a different role.", "lw")}</div>
<div id="l-cam" class="camlayer">
<svg class="ov" width="1920" height="1080" viewBox="0 0 1920 1080"><g fill="none" stroke="{BLUE}" stroke-width="4" stroke-linecap="round" stroke-linejoin="round">
<path class="dr" id="l-a1" pathLength="1000" d="M540 575 H748"/><path class="dr" id="l-a2" pathLength="1000" d="M1170 575 H1378"/><path class="dr" id="l-a3" pathLength="1000" d="{RET}"/>
<path id="l-h1" d="M734 563 L750 575 L734 587"/><path id="l-h2" d="M1364 563 L1380 575 L1364 587"/><path id="l-h3" d="M318 722 L330 704 L342 722"/></g></svg>
<div class="travel" id="l-dot" style="offset-path:path('{FULLP}')"></div>
<div class="lcard" id="l-A" style="left:120px;top:450px"><div class="lhead"><span class="sq2">{icon('net', 34, color=BLUE)}</span>AI outputs</div>{rows}</div>
<div class="lcard hum" id="l-B" style="left:750px;top:450px"><div id="l-Bc"><div class="lhead"><span class="sq2 w">{icon('person', 34, color='#fff')}</span>Human</div>
  <div class="hl1" id="l-B1">Reviews the output</div><div class="hl1" id="l-B2" style="top:150px">{icon('edit', 26, color='#fff')}<span style="margin-left:12px">Corrective feedback</span></div></div></div>
<div class="lcard" id="l-C" style="left:1380px;top:450px"><div class="lhead"><span class="sq2">{icon('chart', 34, color=BLUE)}</span>Algorithm</div><div class="barwrap">{bars}</div></div>
<div class="tag" id="l-ret" style="left:0;width:1920px;text-align:center;top:846px;color:{BLUE}">Keeps improving</div>
</div>
''' + slider('l-sl', 100, 960, 1660, p=0.0)
CUT1 = B('organ', 3) - 1.93
scene('loop', t0 - 0.42, CUT1 + 0.02 - (t0 - 0.42), loop, cls='white dots', z=11)
html.append(f'<div id="iris-wrap" class="clip" style="position:absolute;inset:0;z-index:12;overflow:hidden" data-start="{n(t0 - 0.42)}" data-duration="0.8" data-track-index="6"><div id="iris" style="left:{IR[0] - 50}px;top:{IR[1] - 50}px"></div></div>')
st('#loop-s', clipPath=f'circle(0px at {IR[0]}px {IR[1]}px)'); to('#loop-s', t0 - 0.4, clipPath=f'circle(2300px at {IR[0]}px {IR[1]}px)', duration=0.72, ease='power3.inOut')
st('#iris', scale=0, opacity=1, transformOrigin='50% 50%'); to('#iris', t0 - 0.4, scale=46, duration=0.72, ease='power3.inOut')
logo(t0 - 0.1, 'panel'); wm(t0, True); name_full(t0 - 0.1, False)
hit(t0 - 0.42, 'sonar_bloom', -9, 0.5, 0)
eyebrow('#l-eb', t0 + 0.1); head('lw', t0 + 0.18)
def lcam(t, cx, cy, s=1.3, d=0.75, sx=960, sy=640, ease='expo.inOut', sel='#l-cam'):
    to(sel, t, x=sx - s * cx, y=sy - s * cy, scale=s, duration=d, ease=ease)
st('#l-cam', x=960 - 1.3 * 960, y=640 - 1.3 * 575, scale=1.3, transformOrigin='0 0')
flip('#l-B', T('role', 2)); hit(T('role', 2) + 0.02, 'felt_tap', -12)
sl_active('l-sl', 0, t0); slide_dot('l-sl', T('role', 2), 1660, 0.5); hit(T('role', 2) - 0.05, 'slider_glide', -14)
to('#l-sl-l0', T('role', 2) + 0.2, color='#55606B', duration=0.3); sl_active('l-sl', 1, T('role', 2) + 0.6)
tl_a = T('outputs', 4)
lcam(tl_a - 0.2, 330, 575); flip('#l-A', tl_a); hit(tl_a, 'kalimba', -13, -0.5)
for i in range(3):
    fade(f'#l-r{i}', tl_a + 0.25 + 0.1 * i, 0.25)
    st(f'#l-s{i}', opacity=0, scale=0.3, transformOrigin='50% 50%')
    to(f'#l-s{i}', T('outputs', 8) + 0.05 + 0.14 * i, opacity=1, scale=1, duration=0.35, ease='back.out(3)')
fade('#l-B1', tl_a + 0.2, 0.3)
tfb = T('feedback', 0)
lcam(tfb - 0.1, 960, 575); draw('#l-a1', tfb, 0.5); st('#l-h1', opacity=0); to('#l-h1', tfb + 0.42, opacity=1, duration=0.08); hit(tfb, 'line_glide', -17, -0.4, 0)
pop('#l-B2', T('feedback', 1), 0.5, 0.8); hit(T('feedback', 1), 'blip_two', -13)
st('#l-B', boxShadow='0 18px 40px rgba(0,110,218,0)'); to('#l-B', T('feedback', 1), boxShadow='0 22px 54px rgba(0,110,218,.45)', duration=0.4)
tim = T('improve', 0)
lcam(tim - 0.15, 1590, 575); draw('#l-a2', tim, 0.5); st('#l-h2', opacity=0); to('#l-h2', tim + 0.42, opacity=1, duration=0.08)
flip('#l-C', tim - 0.05)
for i in range(6):
    st(f'#l-b{i}', scaleY=0.08, transformOrigin='50% 100%', backgroundColor='#C8D9EA')
    to(f'#l-b{i}', T('improve', 1) + 0.1 * i, scaleY=1, backgroundColor=BLUE, duration=0.6, ease='back.out(2.6)')
hit(T('improve', 1), 'marimba', -13, 0.5)
tpo = T('improve', 2) - 0.3
lcam(tpo, 960, 540, 1, 0.95, 960, 540, 'expo.inOut'); draw('#l-a3', tpo + 0.1, 0.8); st('#l-h3', opacity=0); to('#l-h3', tpo + 0.82, opacity=1, duration=0.08); rise('#l-ret', tpo + 0.45, 0.5, y=12); hit(tpo + 0.1, 'pen_sweep', -15, 0.5, -0.5)
st('#l-dot', opacity=0, offsetDistance='0%')
to('#l-dot', tfb, opacity=1, duration=0.1); to('#l-dot', tfb, offsetDistance='14%', duration=0.5, ease='power2.inOut')
to('#l-dot', tim, offsetDistance='40%', duration=0.6, ease='power2.inOut'); to('#l-dot', tpo + 0.1, offsetDistance='100%', duration=1.0, ease='power2.inOut')
# exit: the camera dives into the blue Human card until its colour is the frame
te = CUT1
to('#l-Bc', te - 0.42, opacity=0, duration=0.12); to('#l-h', te - 0.4, opacity=0, y=-30, duration=0.22, ease='power2.in'); to('#l-eb', te - 0.4, opacity=0, duration=0.18); to('#l-sl', te - 0.4, opacity=0, duration=0.18)
to('#l-B', te - 0.42, boxShadow='0 0 0 rgba(0,110,218,0)', borderRadius='0px', duration=0.2)
lcam(te - 0.4, 960, 575, 11, 0.4, 960, 540, 'power3.in')
setv('#loop-s', te, opacity=0)
st('#flash2', opacity=0); setv('#flash2', te, opacity=1); to('#flash2', te + 0.005, opacity=0, duration=0.28, ease='power2.out')
enter_zoom(te); logo(te - 0.1, 'foot', 0.3); wm(te, False, 0.1); name_full(te, True, 0.1)
hit(te - 0.4, 'low_flyby', -8)

# ==================================================================== SENSE (full dark): a slanted blue blade cuts to the dark world
t0 = LS('world'); t1 = LS('provides')
ch = [('Events', 'flag', 470), ('Disruptions', 'alert', 576), ('Things never modelled', 'q', 682)]
chips = ''.join(f'<div class="dchip" id="s-c{i}" style="top:{y}px">{icon(ic, 30, color=SOFT_BLUE)}<span>{tx_}</span></div>' for i, (tx_, ic, y) in enumerate(ch))
lines = ''.join(f'<path class="dr" id="s-l{i}" pathLength="1000" stroke="#5A6B78" d="M500 {y + 36} H1296"/>' for i, (_, _, y) in enumerate(ch))
xs = ''.join(f'<div class="xm" id="s-x{i}" style="top:{y + 14}px">{icon("x", 26, 3.2, color=AMB)}</div>' for i, (_, _, y) in enumerate(ch))
cl = ''.join(f'<path class="dr" id="s-h{i}" pathLength="1000" stroke="{ACC}" d="M500 {y + 36} C 640 {y + 36}, 700 610, 830 610"/>' for i, (_, _, y) in enumerate(ch))
pk = ''.join(f'<div class="pkt" id="s-p{i}" style="offset-path:path(\'M970 610 H1380\')"></div>' for i in range(3))
sense = f'''
<div class="eyebrow" id="s-eb" style="left:100px;top:96px;color:{ACC}">What the model can't see</div>
<div class="h1 lt" style="left:100px;top:138px;font-size:68px">{words("The world changes.\nThe model hasn't seen it.", "sw")}</div>
<div id="s-cam" class="camlayer">
<div class="tag" id="s-rw" style="left:100px;top:428px;color:#9AA5AE">Real world</div>
<svg class="ov" width="1920" height="1080" viewBox="0 0 1920 1080"><g fill="none" stroke-width="3.5" stroke-linecap="round">{lines}{cl}
<path class="dr" id="s-out" pathLength="1000" stroke="{ACC}" stroke-width="5" d="M970 610 H1380"/></g>
<line id="s-wall" x1="1320" y1="440" x2="1320" y2="780" stroke="{AMB}" stroke-width="3" stroke-dasharray="10 10"/></svg>
{chips}{xs}{pk}
<div class="tag" id="s-nm" style="left:1180px;width:280px;text-align:center;top:398px;color:{AMB}">Not modelled</div>
<div id="s-model" class="dmodel">{icon('net', 66, 1.6, color='#fff')}<div>AI model</div></div>
<div id="s-rd0" class="ring" style="left:230px;top:540px"></div><div id="s-rd1" class="ring" style="left:230px;top:540px"></div><div id="s-rd2" class="ring" style="left:230px;top:540px"></div>
<div id="s-ring1" class="ring"></div><div id="s-ring2" class="ring"></div>
<div id="s-hum" class="hnode">{icon('person', 64, 2, color=BLUE)}</div>
<div class="tag" id="s-hl" style="left:780px;width:240px;text-align:center;top:692px;color:#fff;background:#1B1B1B;padding:3px 0;border-radius:6px">Human context</div>
<div class="tag" id="s-ol" style="left:1040px;width:260px;text-align:center;top:566px;color:#BFE0FF">Context</div>
</div>
''' + slider('s-sl', 100, 960, 1660, dark=True, p=0.5)
scene('sense', t0 - 0.35, t1 + 0.32 - (t0 - 0.35), sense, cls='dark dots-d', z=13)
html.append(f'<div id="band-wrap" class="clip" style="position:absolute;inset:0;z-index:14;overflow:hidden" data-start="{n(t0 - 0.35)}" data-duration="0.8" data-track-index="6"><div id="s-band"></div></div>')
st('#sense-s', clipPath='polygon(130% 0%,160% 0%,160% 100%,105% 100%)'); to('#sense-s', t0 - 0.32, clipPath='polygon(-30% 0%,160% 0%,160% 100%,-55% 100%)', duration=0.68, ease='power3.inOut')
st('#s-band', x=2500); to('#s-band', t0 - 0.32, x=-600, duration=0.68, ease='power3.inOut')
logo(t0 - 0.05, 'panel'); logo_theme(t0 + 0.05, True); name_full(t0, False); hit(t0 - 0.36, 'dark_sweep', -9, 0.6, -0.4)
eyebrow('#s-eb', t0 + 0.12); head('sw', t0 + 0.2); sl_active('s-sl', 1, t0, dark=True)
st('#s-cam', x=0, y=0, scale=1, transformOrigin='0 0')
rise('#s-model', t0 + 0.4, y=30); fade('#s-rw', T('world', 2), 0.3)
for i in range(3):
    tr_ = T('world', 2) + i * 0.42
    st(f'#s-rd{i}', opacity=0, scale=0.25, transformOrigin='50% 50%'); to(f'#s-rd{i}', tr_, opacity=0.7, duration=0.1); to(f'#s-rd{i}', tr_ + 0.1, opacity=0, scale=2.6, duration=1.15, ease='power2.out')
lcam(T('events', 0) - 0.25, 300, 610, 1.24, 0.8, 460, 660, sel='#s-cam')
for i, lid in enumerate(['events', 'disrupt', 'things']):
    ti = T(lid, 1)
    swing(f'#s-c{i}', ti); draw(f'#s-l{i}', ti + 0.12, 0.85, ease='power2.out')
hit(T('events', 1), 'wood_knock', -13, -0.5); hit(T('disrupt', 1), 'wood_knock', -15, -0.4)
tw_ = T('things', 5) - 0.35
lcam(tw_, 1250, 610, 1.24, 0.8, 1000, 660, sel='#s-cam')
st('#s-wall', scaleY=0, transformOrigin='50% 0%'); to('#s-wall', T('things', 6) - 0.45, scaleY=1, duration=0.5, ease='expo.out'); fade('#s-nm', T('things', 7) - 0.3, 0.3)
tm = T('things', 8) - 0.2
for i in range(3):
    st(f'#s-x{i}', opacity=0, scale=0.3, transformOrigin='50% 50%')
    to(f'#s-x{i}', tm + i * 0.13, opacity=1, scale=1, duration=0.32, ease='back.out(3)')
hit(tm, 'latch', -9, 0.3); hit(tm + 0.26, 'latch', -13, 0.3); shake('#s-model', tm, 6, 0.3)
tc = T('context', 3)
lcam(tc - 0.42, 960, 540, 1, 0.8, 960, 540, sel='#s-cam')
pop('#s-hum', tc, 0.6, 0.3, 'back.out(2.2)'); hit(tc, 'warm_shimmer', -13)
for r_, dl in (('#s-ring1', 0.12), ('#s-ring2', 0.42)):
    st(r_, opacity=0, scale=1, transformOrigin='50% 50%'); to(r_, tc + dl, opacity=0.6, duration=0.08); to(r_, tc + dl + 0.08, opacity=0, scale=2.3, duration=0.9, ease='power2.out')
fade('#s-hl', tc + 0.2, 0.3)
for i in range(3):
    to(f'#s-l{i}', tc + 0.05, opacity=0.14, duration=0.35); draw(f'#s-h{i}', tc + 0.15 + i * 0.09, 0.5, ease='power2.out')
tout = T('context', 5)
draw('#s-out', tout, 0.5); fade('#s-ol', tout + 0.2, 0.3); hit(tout, 'line_glide', -17, 0, 0.5)
for i in range(3):
    st(f'#s-p{i}', opacity=0, offsetDistance='0%')
    to(f'#s-p{i}', tout + 0.4 + i * 0.24, opacity=1, duration=0.05)
    to(f'#s-p{i}', tout + 0.4 + i * 0.24, offsetDistance='100%', duration=0.72, ease='none', repeat=2)
    to(f'#s-x{i}', tout + 0.3, opacity=0, duration=0.25)
to('#s-wall', tout + 0.3, opacity=0.25, duration=0.3); to('#s-nm', tout + 0.3, opacity=0, duration=0.25)
st('#s-model', boxShadow='0 0 0 rgba(38,153,251,0)'); to('#s-model', tout + 0.45, boxShadow='0 0 80px rgba(38,153,251,.7)', duration=0.5)
# exit: the dark world collapses into the human node, because the human is what carries the context out
setv('#sense-s', t1 - 0.36, clipPath='circle(2400px at 900px 610px)')
to('#sense-s', t1 - 0.355, clipPath='circle(0px at 900px 610px)', duration=0.66, ease='power3.inOut'); hit(t1 - 0.4, 'glass_bloom', -13)

# ==================================================================== RECO (speaker right)
t0 = LS('provides'); t1 = LE('reasons')
rs = [('Local festival moved dates', 'cal'), ('Road closure near the store', 'road'), ('New competitor next door', 'store')]
rrows = ''.join(f'<div class="rrow" id="r-r{i}" style="top:{626 + i * 82}px">{icon(ic, 32, color="#B8761A")}<span>{tx_}</span></div>' for i, (tx_, ic) in enumerate(rs))
reco = f'''
<div class="eyebrow" id="r-eb" style="left:70px;top:112px">How the context gets in</div>
<div class="h1" style="left:70px;top:152px;font-size:54px">{words("Not just a thumbs-down.\nA reason.", "rw")}</div>
<div class="ui" id="r-card"><div class="sm" style="color:{BLUE}">AI recommendation</div><div class="rt">Increase stock at Store 12</div>
<div class="tbtn" id="r-up" style="right:112px">{icon('up', 30, color='#7A8791')}</div><div class="tbtn" id="r-dn" style="right:30px">{icon('down', 30, color='#7A8791')}</div>
<div class="tbtn on" id="r-dn2" style="right:30px">{icon('down', 30, color='#fff')}</div></div>
<div class="tag" id="r-bc" style="left:70px;top:582px;color:#B8761A">Not useful, because</div>{rrows}
<div class="illus" id="r-il" style="left:70px;top:882px">Illustrative</div>
''' + slider('r-sl', 70, 960, 920, p=0.5)
scene('reco', t0 - 0.5, t1 - t0 + 0.62, reco, cls='white dots', style='left:0;width:1060px', z=12)
cam_cut('right', t0 - 0.5); setv('#cam2', t0 - 0.5, scale=1)
logo(t0 - 0.1, 'mirror', 0.45); logo_theme(t0 - 0.05, False); wm(t0, False); pill(t0, True, 'right')
eyebrow('#r-eb', t0 + 0.1); head('rw', t0 + 0.18); sl_active('r-sl', 1, t0)
flip('#r-card', t0 + 0.5); hit(t0 + 0.5, 'deep_press', -9)
st('#r-dn2', opacity=0, scale=0.5, rotation=-18, transformOrigin='50% 50%'); to('#r-dn2', T('reco', 7), opacity=1, scale=1, rotation=0, duration=0.42, ease='back.out(3)'); hit(T('reco', 7), 'deep_press', -7)
to('#r-card', T('reco', 7), borderColor=AMB, duration=0.3); shake('#r-card', T('reco', 7), 5, 0.26)
rise('#r-bc', T('reasons', 0) - 0.05, 0.45, y=12)
for i, tt in enumerate([T('reasons', 0) + 0.1, T('reasons', 2) - 0.1, T('reasons', 3) + 0.05]):
    swing(f'#r-r{i}', tt, 0.55, dx=-50)
hit(T('reasons', 0) + 0.1, 'blip_two', -15, -0.4)
fade('#r-il', T('reasons', 3) + 0.2, 0.3)
# exit: fast whip left with motion blur
te = LS('corner')
to('#reco-s', te - 0.3, x=-1060, duration=0.48, ease='power4.in'); smear('#reco-s', te - 0.18, 0.3); cam('full', te - 0.28, 0.55); logo(te - 0.28, 'foot', 0.55); pill(te - 0.3, False); name_full(te, True); hit(te - 0.3, 'snap_whip', -8, 0, -0.7)
setv('#cam2', te - 0.3, scale=1.03)

# ==================================================================== SCALE (speaker left): panel rises from below
t0 = LS('waylook'); t1 = LE('scale')
CH = dict(x=120, y=330, w=830, h=510)
def cx(u): return CH['x'] + u * CH['w']
def cy(v): return CH['y'] + CH['h'] - v * CH['h']
dem = f'M{cx(0)} {cy(.1)} C {cx(.3)} {cy(.2)}, {cx(.6)} {cy(.42)}, {cx(1)} {cy(.95)}'
capc = f'M{cx(0)} {cy(.12)} C {cx(.25)} {cy(.2)}, {cx(.6)} {cy(.3)}, {cx(1)} {cy(.34)}'
ai = f'M{cx(.34)} {cy(.235)} C {cx(.5)} {cy(.3)}, {cx(.75)} {cy(.52)}, {cx(1)} {cy(.9)}'
scale_ = f'''
<div class="eyebrow" id="c-eb" style="left:70px;top:112px">The job-loss question</div>
<div class="h1" style="left:70px;top:152px;font-size:54px">{words("Growth is the objective.", "cw")}</div>
<div id="c-cam" class="camlayer" style="width:1060px">
<svg class="ov" width="1060" height="1080" viewBox="0 0 1060 1080"><g fill="none" stroke-linecap="round">
<path id="c-ax" pathLength="1000" class="dr" stroke="#C9D5E0" stroke-width="2" d="M{cx(0)} {cy(1)} V{cy(0)} H{cx(1)}"/>
<path id="c-dem" pathLength="1000" class="dr" stroke="{INK}" stroke-width="5" d="{dem}"/>
<path id="c-cap" pathLength="1000" class="dr" stroke="{AMB}" stroke-width="4" d="{capc}"/>
<path id="c-ai" pathLength="1000" class="dr" stroke="{BLUE}" stroke-width="6" d="{ai}"/></g>
<line id="c-gap" x1="{cx(.985)}" y1="{cy(.9)}" x2="{cx(.985)}" y2="{cy(.37)}" stroke="{AMB}" stroke-width="2" stroke-dasharray="6 6"/></svg>
<div class="headdot" id="c-d1" style="background:{INK};offset-path:path('{dem}')"></div>
<div class="headdot" id="c-d2" style="background:{BLUE};offset-path:path('{ai}')"></div>
<div class="tag" style="left:70px;top:292px;color:#55606B" id="c-yl">Work to be done</div><div class="tag" style="right:120px;top:{cy(0) + 12}px;color:#55606B" id="c-xl">Time</div>
<div class="tag" id="c-l1" style="left:{cx(.36)}px;top:{cy(.66)}px;color:{INK}">The business, scaling</div>
<div class="tag" id="c-l2" style="left:{cx(.52)}px;top:{cy(.25)}px;color:#B8761A">What people alone can carry</div>
<div class="tag" id="c-l3" style="left:{cx(.74)}px;top:{cy(.5)}px;color:{BLUE};background:#fff;padding:2px 8px;border-radius:6px">With AI</div>
<div class="illus" id="c-il" style="left:120px;top:{cy(0) + 14}px">Illustrative</div>
</div>
''' + slider('c-sl', 70, 960, 830, p=0.5)
scene('scale', t0 - 0.12, LS('shifting') - t0 + 0.5, scale_, cls='white dots', style=f'left:860px;width:{PW}px')
st('#scale-s', clipPath='inset(0px 0px 0px 1060px)'); to('#scale-s', t0 - 0.12, clipPath='inset(0px 0px 0px 0px)', duration=0.62, ease='power3.inOut')
html.append(f'<div id="c-edgew" class="clip" style="position:absolute;inset:0;z-index:11;overflow:hidden" data-start="{n(t0 - 0.12)}" data-duration="0.8" data-track-index="6"><div id="c-edge"></div></div>')
st('#c-edge', x=0); to('#c-edge', t0 - 0.12, x=-1060, duration=0.62, ease='power3.inOut'); to('#c-edge', t0 + 0.42, opacity=0, duration=0.12)
cam('left', t0 - 0.12, 0.62, 'power3.inOut'); logo(t0 - 0.05, 'panel'); wm(t0 + 0.1, True); name_full(t0 - 0.12, False); pill(t0, True); hit(t0 - 0.14, 'slider_glide', -10, 0.4, 0)
setv('#cam2', t0 - 0.12, scale=1)
eyebrow('#c-eb', t0 + 0.3); head('cw', t0 + 0.38); sl_active('c-sl', 1, t0)
draw('#c-ax', t0 + 0.42, 0.6); fade('#c-yl', t0 + 0.5); fade('#c-xl', t0 + 0.6); fade('#c-il', t0 + 0.7)
st('#c-cam', scale=0.97, transformOrigin='80% 40%'); to('#c-cam', t0 + 0.4, scale=1.04, duration=t1 - t0 - 0.4, ease='none')
td = T('waylook', 9)
draw('#c-dem', td, 1.6, ease='power1.inOut'); fade('#c-l1', td + 1.0); hit(td, 'pen_sweep', -16, -0.3, 0.4)
st('#c-d1', opacity=0, offsetDistance='0%'); to('#c-d1', td, opacity=1, duration=0.08); to('#c-d1', td, offsetDistance='100%', duration=1.6, ease='power1.inOut'); to('#c-d1', td + 1.65, opacity=0, duration=0.2)
draw('#c-cap', T('objective', 0), 1.0, ease='power1.inOut'); fade('#c-l2', T('objective', 2))
st('#c-gap', scaleY=0, transformOrigin='50% 100%'); to('#c-gap', T('objective', 4), scaleY=1, duration=0.4, ease='expo.out'); hit(T('objective', 4), 'tom_thud', -11)
tai = T('scale', 0)
draw('#c-ai', tai, 1.2, ease='power2.inOut'); fade('#c-l3', T('scale', 2)); to('#c-gap', T('scale', 2), opacity=0, duration=0.4); hit(tai, 'rise_sweep', -17, -0.2, 0.4)
st('#c-d2', opacity=0, offsetDistance='0%'); to('#c-d2', tai, opacity=1, duration=0.08); to('#c-d2', tai, offsetDistance='100%', duration=1.2, ease='power2.inOut'); to('#c-d2', tai + 1.25, opacity=0, duration=0.2)

# ==================================================================== SHIFT (full white): pushes the split up and out of frame
t0 = LS('shifting'); t1 = LE('strategic')
TW, TH = 346, 96
pos_l = [(140, 470), (510, 470), (140, 586), (510, 586)]
pos_r = [(1060, 470), (1430, 470), (1060, 586), (1430, 586)]
tasks = ['Pull the numbers', 'Build the report', 'Chase the updates', 'Repeat tomorrow']
tiles = ''.join(f'<div class="tile" id="h-t{i}" style="left:{pos_l[i][0]}px;top:{pos_l[i][1]}px">{icon("check", 24, 2.6, color="#7A8791")}<span>{tasks[i]}</span></div>' for i in range(4))
shift = f'''
<div class="eyebrow" id="h-eb" style="left:100px;top:96px">What the job becomes</div>
<div class="h1" style="left:100px;top:138px;font-size:68px" id="h-h">{words("Same person.\nDifferent day.", "hw")}</div>
<div class="board" id="h-bl" style="left:100px;width:800px"><div class="bh">{icon('person', 34, color=INK)}<span>People</span></div></div>
<div class="board" id="h-br" style="left:1020px;width:800px"><div class="bh">{icon('net', 34, color=BLUE)}<span style="color:{BLUE}">AI</span></div></div>
{tiles}
<div class="tile2" id="h-n1" style="left:140px;top:470px">{icon('search', 30, 2.4, color=BLUE)}<span>Check what AI is doing</span></div>
<div class="tile2 strat" id="h-n2" style="left:140px;top:586px"><div id="h-n2c" style="display:flex;align-items:center;gap:16px">{icon('target', 32, 2.2, color='#fff')}<span>Set the strategy</span></div></div>
<div class="illus" id="h-il" style="left:100px;top:846px">Illustrative</div>
''' + slider('h-sl', 100, 960, 1660, p=0.5)
scene('shift', t0 - 0.32, LS('analytics') + 0.02 - (t0 - 0.32), shift, cls='white dots', z=11)
st('#shift-s', y=1080); to('#shift-s', t0 - 0.32, y=0, duration=0.62, ease='power3.inOut'); smear('#shift-s', t0 - 0.2, 0.36, 'y')
to('#scale-s', t0 - 0.32, y=-420, duration=0.62, ease='power3.inOut'); to('#cam', t0 - 0.32, y=cam_state('left')['y'] - 420, duration=0.62, ease='power3.inOut')
logo(t0 - 0.1, 'panel', 0.1); pill(t0 - 0.32, False); hit(t0 - 0.34, 'rise_sweep', -14, 0, 0)
eyebrow('#h-eb', t0 + 0.05); head('hw', t0 + 0.1); sl_active('h-sl', 1, t0); fade('#h-il', t0 + 0.8)
for sel_, dx_, dl in (('#h-bl', -40, 0.1), ('#h-br', 40, 0.2)): swing(sel_, t0 + dl, 0.7, dx=dx_)
for i in range(4): pop(f'#h-t{i}', t0 + 0.45 + i * 0.13, 0.5, 0.7)
tmv = T('making', 2)
for i in range(4):
    dx_ = pos_r[i][0] - pos_l[i][0]; ti = tmv + i * 0.13
    to(f'#h-t{i}', ti, x=dx_, duration=0.8, ease='power3.inOut'); to(f'#h-t{i}', ti, backgroundColor=TINT, borderColor=SOFT_BLUE, duration=0.5, ease='none')
    to(f'#h-t{i}', ti, y=-62, rotation=-5, scale=1.08, duration=0.4, ease='power2.out'); to(f'#h-t{i}', ti + 0.4, y=0, rotation=0, scale=1, duration=0.42, ease='back.out(1.8)')
hit(tmv, 'silk_swipe', -12, -0.5, 0.6)
flip('#h-n1', tmv + 0.95)
st('#h-n2', opacity=0, scale=0.7, transformOrigin='50% 50%'); to('#h-n2', T('strategic', 7) - 0.15, opacity=1, scale=1, duration=0.65, ease='back.out(2.4)'); hit(T('strategic', 7) - 0.15, 'warm_shimmer', -13)
# exit: the blue strategy tile grows until it is the frame, then slides off the footage
te = LS('analytics')
to('#h-n2c', te - 0.6, opacity=0, duration=0.14); to('#h-n2', te - 0.55, scale=17, borderRadius='0px', duration=0.55, ease='power3.in')
setv('#shift-s', te, opacity=0); cam_cut('full', te - 0.6); setv('#scale-s', te - 0.6, y=0)
st('#flash3', x=1920); setv('#flash3', te, x=0); to('#flash3', te + 0.005, x=1920, duration=0.5, ease='expo.inOut')
logo(te, 'foot', 0.4); wm(te, False, 0.1); name_full(te, True, 0.1); hit(te - 0.55, 'bass_bloom', -7)

# ==================================================================== ASK (speaker left): the panel swings open like a page
t0 = LS('stake'); t1 = LE('senior')
ppl = [('Senior manager', 'brief', 70, 'a-p0'), ('Analyst', 'chart', 376, 'a-p1'), ('Intern', 'grad', 588, 'a-p2')]
pchips = ''.join(f'<div class="pchip" id="{i}" style="left:{x}px">{icon(ic, 28, color="#55606B")}<span>{t}</span></div>' for t, ic, x, i in ppl)
pon = ''.join(f'<div class="pchip on" id="{i}o" style="left:{x}px">{icon(ic, 28, color="#fff")}<span>{t}</span></div>' for t, ic, x, i in ppl[1:])
mini = ''.join(f'<div class="minibar" id="a-b{i}" style="left:{i * 44}px;height:{h}px;width:30px"></div>' for i, h in enumerate([36, 62, 48, 80, 104]))
ask = f'''
<div class="eyebrow" id="a-eb" style="left:70px;top:112px">What wasn't possible before</div>
<div class="h1" style="left:70px;top:152px;font-size:54px">{words("Ask it the way you'd\nask an intern.", "aw")}</div>
<div class="ui" id="a-rep" style="top:310px;height:176px"><div style="display:flex;gap:18px;align-items:center"><span class="sq2">{icon('doc', 34, color=BLUE)}</span><div><div class="sm" style="color:{BLUE}">Insightful report</div><div class="skel" style="width:300px;margin-top:14px"></div><div class="skel" style="width:230px;margin-top:12px"></div></div></div>
<div style="position:absolute;right:40px;bottom:26px;width:220px;height:110px">{mini}</div></div>
<div class="inp" id="a-inp">{icon('spark', 30, 2, color=BLUE)}<span class="plc" id="a-plc">Just ask, in plain English</span></div>
<div class="tag" id="a-tl" style="left:70px;top:654px;color:#55606B">The way you'd tell</div>
<div id="a-row" style="position:absolute;left:0;top:692px;width:1060px;height:80px">{pchips}{pon}<svg id="a-strike-w" class="ov" width="360" height="80" style="left:70px;top:0"><path id="a-strike" class="dr" pathLength="1000" d="M8 37 H280" stroke="{AMB}" stroke-width="4" fill="none" stroke-linecap="round"/></svg></div>
''' + slider('a-sl', 70, 960, 830, p=0.5)
scene('ask', t0 - 0.16, LS('why1') - t0 + 0.5, ask, cls='white dots', style=f'left:860px;width:{PW}px')
st('#ask-s', rotationY=-92, transformPerspective=1500, transformOrigin='100% 50%'); to('#ask-s', t0 - 0.16, rotationY=0, duration=0.8, ease='expo.out')
cam('left', t0 - 0.16, 0.6, 'expo.out'); setv('#cam2', t0 - 0.16, scale=1); logo(t0 - 0.1, 'panel'); wm(t0 + 0.1, True); name_full(t0 - 0.16, False); pill(t0, True); hit(t0 - 0.18, 'page_turn', -6, 0.6, 0.1)
eyebrow('#a-eb', t0 + 0.25); head('aw', t0 + 0.32); sl_active('a-sl', 1, t0)
slide_dot('a-sl', t0 + 0.55, 830, 1.0, 1.1); to('#a-sl-l1', t0 + 0.8, color='#55606B', duration=0.3); sl_active('a-sl', 2, t0 + 1.25); hit(t0 + 0.55, 'sonar_bloom', -14, -0.3, 0.5)
flip('#a-rep', T('stake', 3) - 0.1); hit(T('stake', 3) - 0.1, 'page_turn', -9)
for i in range(5):
    st(f'#a-b{i}', scaleY=0.06, transformOrigin='50% 100%', backgroundColor=BLUE)
    to(f'#a-b{i}', T('stake', 4) + i * 0.07, scaleY=1, duration=0.6, ease='back.out(2.8)')
tin = T('purely', 4) - 0.1
st('#a-inp', opacity=0, scaleX=0.08, transformOrigin='0% 50%'); to('#a-inp', tin, opacity=1, duration=0.08); to('#a-inp', tin, scaleX=1, duration=0.7, ease='expo.out'); hit(tin, 'soft_pop', -13)
st('#a-plc', clipPath='inset(0 100% 0 0)'); to('#a-plc', tin + 0.3, clipPath='inset(0 0% 0 0)', duration=0.9, ease='none')
fade('#a-tl', T('intern', 0), 0.3)
for pid, tt in (('a-p0', T('intern', 0)), ('a-p1', T('intern', 0) + 0.1), ('a-p2', T('intern', 0) + 0.2)): pop(f'#{pid}', tt, 0.5, 0.6)
for pid, tt in (('a-p1o', T('intern', 4)), ('a-p2o', T('intern', 7))):
    pop(f'#{pid}', tt, 0.4, 0.8)
    to(f'#{pid[:-1]}', tt + 0.22, opacity=0, duration=0.01)
draw('#a-strike', T('senior', 0) + 0.15, 0.4, ease='power3.out'); to('#a-p0', T('senior', 0) + 0.2, opacity=0.45, duration=0.3); hit(T('senior', 0) + 0.15, 'tom_thud', -15)

# ==================================================================== QUESTION (full dark): the input pill opens into the whole frame
t0 = LS('why1'); t1 = LE('action')
Q1 = 'Why are certain marketing campaigns not working?'
Q2 = 'Why is revenue dropping in this region? What can we do about it?'
def chars(s, cl): return ''.join(f'<span class="ch {cl}">{c if c != " " else "&nbsp;"}<i></i></span>' for c in s)
regs = [('North', 74, False), ('East', 62, False), ('West', 26, True), ('South', 58, False)]
rbars = ''.join(f'<div class="rg"><div class="rgv"><div class="rgb" id="q-rb{i}" style="height:{h * 1.6}px;background:{AMB if lo else BLUE}"></div></div><span style="color:{"#B8761A" if lo else "#55606B"};font-weight:{700 if lo else 500}">{nm}</span></div>' for i, (nm, h, lo) in enumerate(regs))
pq = ''.join(f'<div class="pkt" id="q-k{i}" style="offset-path:path(\'M1220 620 H1296\')"></div>' for i in range(2))
qq = f'''
<div class="eyebrow" id="q-eb" style="left:100px;top:96px;color:{ACC}">The questions leaders ask</div>
<div id="q-cam" class="camlayer">
<svg class="ov" width="1920" height="1080" viewBox="0 0 1920 1080"><g fill="none" stroke-linecap="round" stroke-width="4">
<path id="q-l0" class="dr" pathLength="1000" stroke="#5A6B78" d="M600 560 C 650 560, 650 620, 700 620"/><path id="q-l0b" class="dr" pathLength="1000" stroke="#5A6B78" d="M600 680 C 650 680, 650 620, 700 620"/>
<path id="q-l1" class="dr" pathLength="1000" stroke="{ACC}" d="M600 560 C 650 560, 650 620, 700 620"/><path id="q-l1b" class="dr" pathLength="1000" stroke="{ACC}" d="M600 680 C 650 680, 650 620, 700 620"/>
<path id="q-l2" class="dr" pathLength="1000" stroke="{ACC}" d="M1220 620 H1296"/></g></svg>
<div class="dchip q" id="q-c0" style="top:510px">{icon('q', 32, color=SOFT_BLUE)}<span>Campaigns not working</span></div>
<div class="dchip q" id="q-c1" style="top:630px">{icon('q', 32, color=SOFT_BLUE)}<span>Revenue dropping</span></div>
<div class="void" id="q-void"><div class="tag" style="color:{AMB};position:static;font-size:24px">No system in place</div>
<div class="vl" id="q-v0">{icon('x', 24, 3, color=AMB)}<span>Application</span></div><div class="vl" id="q-v1">{icon('x', 24, 3, color=AMB)}<span>System</span></div><div class="vl" id="q-v2">{icon('x', 24, 3, color=AMB)}<span>Solution</span></div></div>
<div class="dmodel big" id="q-sys">{icon('net', 74, 1.6, color='#fff')}<div>AI system</div><div class="sub">Answers automatically</div></div>
<div class="ans" id="q-ans"><div class="sm" style="color:{BLUE}">Insight</div><div class="at">West is where the drop is</div>
<div class="rgs">{rbars}</div>
<div class="act" id="q-act"><span id="q-actt">Take action</span></div><div class="act done" id="q-done">{icon('check', 26, 3, color='#fff')}<span>Action taken</span></div><div id="q-rip"></div></div>
<div class="illus" id="q-il" style="left:1304px;top:880px;color:#9AA5AE">Illustrative</div>
{pq}
</div>
<div id="q-glow"></div><div class="prompt" id="q-p">{icon('spark', 34, 2, color=ACC)}<div class="ptext" id="q-t1">{chars(Q1, 'c1')}</div><div class="ptext" id="q-t2">{chars(Q2, 'c2')}</div></div>
''' + slider('q-sl', 100, 960, 1660, dark=True, p=1.0)
scene('question', t0 - 0.45, LS('now') + 0.14 - (t0 - 0.45), qq, cls='dark dots-d', z=14)
st('#question-s', clipPath='inset(520px 70px 468px 930px round 46px)'); to('#question-s', t0 - 0.42, clipPath='inset(0px 0px 0px 0px round 0px)', duration=0.68, ease='power3.inOut')
pill(t0 - 0.45, False); logo_theme(t0 - 0.15, True); wm(t0 - 0.15, False); hit(t0 - 0.46, 'data_morph', -9, 0.4, 0)
eyebrow('#q-eb', t0 + 0.05); sl_active('q-sl', 2, t0, dark=True)
st('#q-glow', opacity=0, scale=0.6, transformOrigin='50% 50%'); to('#q-glow', t0, opacity=1, scale=1, duration=1.2, ease='expo.out')
st('#q-p', y=250, opacity=0, scale=0.9, transformOrigin='50% 50%'); to('#q-p', t0 - 0.12, opacity=1, scale=1, duration=0.55, ease='back.out(1.8)')
js.append(f"typeIn('.c1',{n(T('why1', 0))},{n(T('why1', -1) + 0.3 - T('why1', 0))});")
to('#q-t1', T('why2', 0) - 0.18, opacity=0, y=-26, filter='blur(6px)', duration=0.16, ease='power2.in')
js.append(f"typeIn('.c2',{n(T('why2', 0))},{n(T('what2', -1) + 0.3 - T('why2', 0))});")
hit(T('why1', 0), 'typing', -17); hit(T('why2', 0), 'typing', -18)
tn = T('nosystem', 2)
to('#q-glow', tn - 0.85, opacity=0, duration=0.4); to('#q-p', tn - 0.85, y=0, duration=0.65, ease='expo.inOut'); hit(tn - 0.85, 'low_flyby', -13, 0, 0)
swing('#q-c0', tn - 0.45, 0.6); swing('#q-c1', tn - 0.32, 0.6)
draw('#q-l0', tn - 0.2, 0.3); draw('#q-l0b', tn - 0.2, 0.3)
st('#q-void', opacity=0, scale=0.86, transformOrigin='50% 50%'); to('#q-void', tn - 0.1, opacity=1, scale=1, duration=0.5, ease='back.out(1.8)'); hit(tn - 0.1, 'dark_sweep', -14)
for i, tt in enumerate([T('nosystem', 3), T('nosystem', 6), T('nosystem', 9)]): swing(f'#q-v{i}', tt, 0.4, dx=-24)
ta = T('answer', 2)
st('#q-cam', x=0, y=0, scale=1, transformOrigin='0 0')
to('#q-void', ta - 0.1, opacity=0, scale=1.1, duration=0.25)
flip('#q-sys', ta - 0.1, 0.7); hit(ta - 0.1, 'bass_bloom', -11); draw('#q-l1', ta - 0.1, 0.35); draw('#q-l1b', ta - 0.1, 0.35)
st('#q-sys', boxShadow='0 0 0 rgba(38,153,251,0)'); to('#q-sys', ta + 0.2, boxShadow='0 0 80px rgba(38,153,251,.6)', duration=0.6)
tans = T('answer', 3)
draw('#q-l2', tans, 0.35)
st('#q-ans', opacity=0, x=90, rotationY=-50, transformPerspective=1300, transformOrigin='100% 50%'); to('#q-ans', tans + 0.2, opacity=1, x=0, rotationY=0, duration=0.85, ease='expo.out'); hit(tans + 0.2, 'data_morph', -11, 0.5, 0.3)
for i in range(4):
    st(f'#q-rb{i}', scaleY=0.05, transformOrigin='50% 100%'); to(f'#q-rb{i}', T('answer', 4) + 0.1 + i * 0.1, scaleY=1, duration=0.7, ease='back.out(2.4)')
for i in range(2):
    st(f'#q-k{i}', opacity=0, offsetDistance='0%'); to(f'#q-k{i}', tans + 0.4 + i * 0.2, opacity=1, duration=0.05); to(f'#q-k{i}', tans + 0.4 + i * 0.2, offsetDistance='100%', duration=0.4, ease='none', repeat=5)
to('#q-cam', T('answer', 5), x=-160, y=-34, scale=1.09, duration=1.5, ease='power2.inOut')
fade('#q-il', T('answer', 6), 0.3); pop('#q-act', T('answer', 7), 0.5, 0.8)
tk = T('action', 3)
to('#q-cam', tk - 0.5, x=-470, y=-210, scale=1.3, duration=0.6, ease='expo.inOut')
to('#q-act', tk - 0.08, scale=0.93, duration=0.08, ease='power2.in'); to('#q-act', tk, scale=1, duration=0.3, ease='back.out(3)')
pop('#q-done', tk + 0.01, 0.35, 0.92)
st('#q-rip', opacity=0, scale=0.1, transformOrigin='50% 50%'); to('#q-rip', tk, opacity=0.5, duration=0.05); to('#q-rip', tk + 0.05, opacity=0, scale=1, duration=0.6, ease='expo.out'); hit(tk, 'chime', -8)
# exit: the whole dark world tilts away and falls back
te = LS('now')
cam_cut('full', te - 0.8); setv('#scale-s', te - 0.8, y=0)
to('#question-s', te - 0.42, scale=0.68, y=170, rotationX=30, opacity=0, transformPerspective=1500, transformOrigin='50% 100%', duration=0.46, ease='power3.in'); hit(te - 0.44, 'reverse_snap', -10)
logo(te - 0.32, 'foot', 0.45); logo_theme(te - 0.05, False); name_full(te, True)

# ==================================================================== END CARD: a slanted blue flood
t0 = LS('end')
scene('end', t0 - 0.22, TOTAL - t0 + 0.22, f'''{net_svg("e-net", "rgba(255,255,255,.13)", "rgba(255,255,255,.22)")}<div id="e-ring" class="ering"></div><img id="e-logo" src="assets/logo_allwhite.svg"><div id="e-tag">{words("Making AI Work for Enterprise", "ew")}</div><div id="e-url">akaike.ai</div>''', cls='endc', z=20)
st('#end-s', clipPath='polygon(-40% 0%,-30% 0%,-60% 100%,-70% 100%)'); to('#end-s', t0 - 0.2, clipPath='polygon(-40% 0%,135% 0%,105% 100%,-70% 100%)', duration=0.66, ease='power3.inOut')
to('#logo', t0 + 0.05, opacity=0, duration=0.2); to('#nameband', t0 - 0.2, opacity=0, duration=0.2)
st('#e-net', opacity=0, scale=1.25, transformOrigin='50% 40%'); to('#e-net', t0 + 0.1, opacity=1, scale=1, duration=1.6, ease='expo.out')
st('#e-logo', opacity=0, scale=0.55, transformOrigin='50% 50%'); to('#e-logo', t0 + 0.26, opacity=1, scale=1, duration=0.9, ease='back.out(1.9)')
st('#e-ring', opacity=0, scale=0.2, transformOrigin='50% 50%'); to('#e-ring', t0 + 0.26, opacity=0.5, duration=0.06); to('#e-ring', t0 + 0.32, opacity=0, scale=3, duration=1.1, ease='expo.out')
head('ew', t0 + 0.72); rise('#e-url', t0 + 1.1, 0.6, y=16)
hit(t0 + 0.24, 'subhit', -4); hit(t0 - 0.24, 'flood_shimmer', -11)

# ==================================================================== CUTAWAYS: the others listening, mouths covered, only Rahul's voice plays. Each one hides real jump cuts.
import subprocess
LEN = [float(subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v', '-show_entries', 'stream=duration', '-of', 'csv=p=0', f'film/assets/cut{k}.mp4'], capture_output=True, text=True).stdout.split()[0]) - 0.02 for k in range(4)]
PLAN = [(B('pov', 2) - 0.5, 0, 1), (CUT1, 1, 1), (B('jobloss', 1) - 0.58, 2, 1), (B('works', 2) - 0.6, 3, 2)]
for ts, k, who in PLAN:
    html.append(f'<div class="cutw" id="cw{k}"><video id="cut{k}" class="clip cutv" data-start="{n(ts)}" data-duration="{LEN[k]}" data-track-index="2" muted playsinline src="assets/cut{k}.mp4"></video></div>')
    st(f'#cw{k}', scale=1.05, transformOrigin='50% 40%'); setv(f'#cw{k}', ts, scale=1.05); to(f'#cw{k}', ts + 0.005, scale=1, duration=LEN[k], ease='power1.out')
    setv('#nm0', ts, opacity=0); setv(f'#nm{who}', ts, opacity=1); setv(f'#nm{who}', ts + LEN[k], opacity=0); setv('#nm0', ts + LEN[k], opacity=1)

# ==================================================================== CAPTIONS: only on full-frame lines, as in the reference. Key chunks go solid blue and kick the camera.
CAP = {'agency': 'Am I going|to lose|my agency?', 'agents': 'Because now|AI agents|come into|the picture.', 'everything': "They'll be|able to do|everything.",
       'stigma': 'At least|in US,|there is|a lot of stigma|around AI.', 'pov': "My point|of view there,|I don't think|humans will be|out of the loop.",
       'organ': 'You could|also think|of humans|as a sense organ|for AI,', 'corner': 'So human|needs to be|in place|to catch those|corner cases',
       'works': 'and make sure|that AI works|really well.', 'jobloss': 'In terms of|job loss|happening,', 'analytics': 'If we look|at the world|of analytics,', 'notposs': 'what was|not possible|before is', 'now': 'Now it is|possible.'}
HOT = {('agency', 2), ('everything', 2), ('stigma', 3), ('pov', 4), ('organ', 3), ('corner', 4), ('jobloss', 1), ('notposs', 1), ('now', 1)}
KICK = {('agency', 2): 1.05, ('everything', 2): 1.09, ('pov', 4): 1.07, ('organ', 3): 1.08, ('now', 1): 1.09}
ci = 0
for lid, spec in CAP.items():
    ws = by[lid]; k = 0; chunks = spec.split('|'); line_end = LE(lid)
    if lid in ('agency', 'agents'): line_end = LS('agents' if lid == 'agency' else 'everything')
    idx = []
    for c in chunks:
        m = len(c.split()); idx.append((k, k + m)); k += m
    assert k == len(ws), (lid, k, len(ws))
    for j, (a, b) in enumerate(idx):
        st_ = ws[a]['start'] - 0.04; en = ws[idx[j + 1][0]]['start'] - 0.04 if j + 1 < len(idx) else line_end
        cid = f'k{ci}'; ci += 1; hot = (lid, j) in HOT; base = '#BFE0FF' if hot else '#fff'; act = '#fff' if hot else ACC
        spans = ' '.join(f'<span id="{cid}w{q}" class="cw2" style="color:{base}">{ws[a + q]["text"]}</span>' for q in range(b - a))
        html.append(f'<div class="clip capw" id="{cid}" data-start="{n(st_)}" data-duration="{n(en - st_)}" data-track-index="4"><div class="capbox{" hot" if hot else ""}" id="{cid}b">{spans}</div></div>')
        if hot:
            st(f'#{cid}b', opacity=0, scale=0.62, rotation=-3, transformOrigin='50% 60%')
            to(f'#{cid}b', st_, opacity=1, scale=1, rotation=0, duration=0.34, ease='back.out(3)')
        else:
            st(f'#{cid}b', opacity=0, y=12, scale=0.9, transformOrigin='50% 60%')
            to(f'#{cid}b', st_, opacity=1, y=0, scale=1, duration=0.2, ease='back.out(2.2)')
        if (lid, j) in KICK: punch(ws[a]['start'], KICK[(lid, j)])
        for q in range(b - a):
            ti = ws[a + q]['start']
            setv(f'#{cid}w{q}', ti, color=act)
            if q + 1 < b - a: setv(f'#{cid}w{q}', ws[a + q + 1]['start'], color=base)
shake('#cam3', T('everything', -1), 6, 0.3)

CSS = f'''
*{{margin:0;padding:0;box-sizing:border-box}}
html,body{{width:1920px;height:1080px;overflow:hidden;background:#000;font-family:Inter,sans-serif;-webkit-font-smoothing:antialiased}}
#root{{position:relative;width:1920px;height:1080px;overflow:hidden;background:#000}}
#camwrap{{position:absolute;inset:0;overflow:hidden;z-index:1;background:#fff}}
#cam,#cam2,#cam3{{position:absolute;left:0;top:0;width:1920px;height:1080px}}
#aroll{{position:absolute;inset:0;width:1920px;height:1080px;object-fit:cover}}
.cutw{{position:absolute;inset:0;z-index:3;overflow:hidden}} .cutv{{position:absolute;inset:0;width:1920px;height:1080px;object-fit:cover}}
#nameband{{position:absolute;left:0;right:0;bottom:0;height:120px;background:linear-gradient(to top,rgba(0,0,0,.5),rgba(0,0,0,0));z-index:4}}
#nameband span{{position:absolute;left:36px;bottom:24px;color:#fff;font:500 28px "Open Sans",Inter,sans-serif;text-shadow:0 1px 3px rgba(0,0,0,.4)}}
#pill{{position:absolute;left:24px;top:986px;height:58px;padding:0 24px;background:#fff;border-radius:10px;display:flex;align-items:center;font:500 26px Inter;color:#16191D;z-index:4;opacity:0}}
.scene{{position:absolute;inset:0;overflow:hidden;pointer-events:none}}
.slide{{position:absolute;left:0;top:0;width:1920px;height:1080px;overflow:hidden}}
.camlayer{{position:absolute;left:0;top:0;width:1920px;height:1080px}}
.white{{background:#fff;color:{INK}}} .dark{{background:{DARK};color:#fff}}
.dots{{background-image:radial-gradient(#E9EEF3 1.5px,transparent 1.5px);background-size:32px 32px}}
.dots-d{{background-image:radial-gradient(#26292C 1.5px,transparent 1.5px);background-size:32px 32px}}
.eyebrow{{position:absolute;font:700 23px Inter;letter-spacing:.015em;text-transform:uppercase;color:{BLUE};white-space:nowrap}}
.h1{{position:absolute;font:700 62px/1.13 Inter;letter-spacing:-.018em;color:{INK};white-space:nowrap}} .h1.lt{{color:#fff}}
.mw{{display:inline-block;overflow:hidden;vertical-align:bottom;padding:0 .03em .15em 0;margin-bottom:-.15em}}
.fw,.lw,.sw,.rw,.cw,.hw,.aw,.tw,.ew{{display:inline-block}}
.tag{{position:absolute;font:600 20px Inter;letter-spacing:.03em;text-transform:uppercase;white-space:nowrap}}
.illus{{position:absolute;font:400 19px Inter;color:#6A7681}}
.ov{{position:absolute;left:0;top:0;overflow:visible}}
.ic{{display:block;flex:none}}
.netsvg{{position:absolute;left:0;top:0}}
/* wipes */
#blinds{{position:absolute;inset:0;z-index:25;pointer-events:none}} .bl{{position:absolute;top:0;width:241px;height:1080px}}
#flash{{position:absolute;inset:0;background:{ACC};z-index:24;opacity:0}} #flash2{{position:absolute;inset:0;background:{BLUE};z-index:24;opacity:0}}
#flash3{{position:absolute;inset:0;background:{BLUE};z-index:24}}
#c-edge{{position:absolute;left:1914px;top:0;width:6px;height:1080px;background:{ACC}}}
#iris{{position:absolute;width:100px;height:100px;border-radius:50%;border:2px solid {ACC};box-shadow:0 0 0 .6px {ACC}}}
#s-band{{position:absolute;left:-120px;top:-60px;width:150px;height:1200px;background:{ACC};transform-origin:50% 50%;margin-left:0;border-radius:0}}
/* slider */
.sl{{position:absolute;height:64px}}
.sl-lab{{position:absolute;top:0;font:600 19px Inter;letter-spacing:.02em;white-space:nowrap}}
.sl-line{{position:absolute;left:0;right:0;top:46px;height:3px;border-radius:2px}}
.sl-fill{{position:absolute;left:0;right:0;top:45px;height:5px;border-radius:3px;background:{BLUE}}}
.dark .sl-fill{{background:{ACC}}}
.sl-tick{{position:absolute;top:40px;width:2px;height:15px}}
.sl-dot{{position:absolute;left:-10px;top:37.5px;width:20px;height:20px;border-radius:50%;background:{BLUE};box-shadow:0 0 0 5px rgba(0,110,218,.16)}}
.dark .sl-dot{{background:{ACC};box-shadow:0 0 0 5px rgba(38,153,251,.2)}}
/* title */
#t-lockup{{position:absolute;left:0;width:1920px;top:318px;display:flex;justify-content:center}}
#t-icon-wrap{{width:560px}} #t-icon{{display:block;width:560px}}
#t-name{{position:absolute;left:0;width:1920px;top:496px;text-align:center;font:700 84px Inter;letter-spacing:-.012em;color:{ACC}}}
#t-rule{{position:absolute;left:928px;top:612px;width:64px;height:6px;background:{ACC};border-radius:3px}}
#t-sub{{position:absolute;left:0;width:1920px;top:640px;text-align:center;font:500 28px Inter;color:#6A7681}}
#t-dot{{position:absolute;left:804px;top:375px;width:50px;height:50px;border-radius:50%;background:{ACC}}}
.tring{{position:absolute;left:660px;top:190px;width:340px;height:340px;border-radius:50%;border:3px solid {ACC}}}
/* fear */
#f-grid{{position:absolute}}
.scard{{position:absolute;height:176px;border-radius:18px;display:flex;align-items:center;gap:20px;padding:0 26px;background:transparent}}
.scard.blue{{background:{BLUE};color:#fff}}
.scard .sq{{width:66px;height:66px;border-radius:14px;background:rgba(255,255,255,.2);display:flex;align-items:center;justify-content:center;color:#fff;flex:none}}
.scard .sq.t{{background:{TINT}}}
.sm{{font:600 20px Inter;letter-spacing:.02em;text-transform:uppercase}}
.ct{{font:700 35px/1.16 Inter;margin-top:8px}}
.bubble{{position:absolute;left:186px;top:410px;background:{INK};color:#fff;font:600 37px Inter;padding:24px 38px;border-radius:18px;white-space:nowrap;box-shadow:0 18px 44px rgba(10,20,30,.35)}}
.bubble i{{position:absolute;left:50%;bottom:-14px;width:30px;height:30px;margin-left:-15px;background:{INK};transform:rotate(45deg);border-radius:4px}}
/* loop */
.lcard{{position:absolute;width:420px;height:250px;border-radius:20px;background:#fff;border:2px solid #D5E2EE;box-shadow:0 14px 34px rgba(16,40,70,.08)}}
.lcard.hum{{background:{BLUE};border-color:{BLUE};color:#fff}}
.lhead{{position:absolute;left:24px;top:22px;display:flex;align-items:center;gap:16px;font:700 31px Inter}}
.sq2{{width:58px;height:58px;border-radius:13px;background:{TINT};display:inline-flex;align-items:center;justify-content:center;flex:none}} .sq2.w{{background:rgba(255,255,255,.2)}}
.lrow{{position:absolute;left:28px;right:28px;height:26px}} .lln{{height:14px;margin-top:6px;background:#E3EAF1;border-radius:7px}}
.lst{{position:absolute;right:0;top:2px}}
.hl1{{position:absolute;left:28px;top:104px;font:500 28px Inter;display:flex;align-items:center;white-space:nowrap}}
.barwrap{{position:absolute;left:0;right:0;top:96px;height:130px}}
.minibar{{position:absolute;bottom:0;width:46px;border-radius:6px 6px 0 0;background:{BLUE}}}
.travel{{position:absolute;left:0;top:0;width:22px;height:22px;border-radius:50%;background:{ACC};box-shadow:0 0 0 6px rgba(38,153,251,.22),0 0 18px rgba(38,153,251,.8)}}
.pkt{{position:absolute;left:0;top:0;width:14px;height:14px;border-radius:50%;background:#BFE0FF;box-shadow:0 0 14px 3px rgba(38,153,251,.9)}}
.headdot{{position:absolute;left:0;top:0;width:18px;height:18px;border-radius:50%;box-shadow:0 0 0 6px rgba(0,110,218,.14)}}
/* sense */
.dchip{{position:absolute;left:100px;width:400px;height:74px;background:{DCARD};border-radius:13px;display:flex;align-items:center;gap:16px;padding:0 22px;font:600 28px Inter;color:#E7EDF3;white-space:nowrap}}
.xm{{position:absolute;left:1303px;width:34px;height:44px;display:flex;align-items:center;justify-content:center;background:{DARK}}}
.dmodel{{position:absolute;left:1380px;top:470px;width:420px;height:280px;background:{BLUE};border-radius:22px;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:16px;font:700 34px Inter;color:#fff;text-transform:uppercase;letter-spacing:.02em}}
.dmodel .sub{{font:500 24px Inter;text-transform:none;letter-spacing:0;opacity:.85}}
.dmodel.big{{left:700px;top:462px;width:520px;height:316px}}
.hnode{{position:absolute;left:830px;top:540px;width:140px;height:140px;border-radius:50%;background:#fff;display:flex;align-items:center;justify-content:center}}
.ring{{position:absolute;left:830px;top:540px;width:140px;height:140px;border-radius:50%;border:3px solid {ACC}}}
/* reco */
.ui{{position:absolute;left:70px;top:318px;width:920px;height:232px;padding:28px 32px;background:#fff;border:2px solid #D5E2EE;border-radius:18px;box-shadow:0 14px 34px rgba(16,40,70,.08)}}
#r-card{{height:176px}}
.rt{{font:700 38px Inter;margin-top:14px;white-space:nowrap}}
.tbtn{{position:absolute;bottom:26px;width:66px;height:66px;border-radius:50%;border:2px solid #D5E2EE;background:#fff;display:flex;align-items:center;justify-content:center}}
.tbtn.on{{background:{AMB};border-color:{AMB}}}
.rrow{{position:absolute;left:70px;width:920px;height:70px;border-radius:13px;background:#FFF5E6;display:flex;align-items:center;gap:16px;padding:0 24px;font:500 31px Inter;color:#6B4A12;white-space:nowrap}}
/* shift */
.board{{position:absolute;top:366px;height:464px;background:#F3F7FB;border:2px solid #E2EAF2;border-radius:20px}}
.bh{{position:absolute;left:32px;top:26px;display:flex;align-items:center;gap:14px;font:700 34px Inter}}
.tile{{position:absolute;width:{TW}px;height:{TH}px;background:#fff;border:2px solid #D5E2EE;border-radius:13px;display:flex;align-items:center;gap:12px;padding:0 18px;font:600 25px Inter;white-space:nowrap;color:{INK}}}
.tile2{{position:absolute;width:716px;height:96px;background:#fff;border:2px solid {SOFT_BLUE};border-radius:14px;display:flex;align-items:center;gap:16px;padding:0 24px;font:700 32px Inter;white-space:nowrap}}
.tile2.strat{{background:{BLUE};border-color:{BLUE};color:#fff;height:128px;font-size:40px;z-index:5}}
/* ask */
.skel{{height:14px;background:#E3EAF1;border-radius:7px}}
.inp{{position:absolute;left:70px;top:520px;width:920px;height:92px;border:2px solid {SOFT_BLUE};border-radius:46px;background:#fff;display:flex;align-items:center;gap:18px;padding:0 34px;font:500 31px Inter;color:#55606B;white-space:nowrap;box-shadow:0 10px 26px rgba(0,110,218,.12)}}
.pchip{{position:absolute;top:0;height:74px;border-radius:37px;border:2px solid #D5E2EE;background:#fff;display:flex;align-items:center;gap:12px;padding:0 26px;font:600 27px Inter;color:#3A444C;white-space:nowrap}}
.pchip.on{{background:{BLUE};border-color:{BLUE};color:#fff}}
/* question */
.prompt{{position:absolute;left:100px;top:146px;width:1720px;height:132px;background:{DCARD};border-radius:20px;padding:0 40px 0 118px;box-shadow:0 18px 50px rgba(0,0,0,.35)}}
.prompt>svg{{position:absolute;left:44px;top:49px}}
.ptext{{position:absolute;left:112px;right:50px;top:40px;font:600 46px/1.2 Inter;color:#fff}}
.ch{{position:relative;opacity:0;display:inline-block}} .ch i{{position:absolute;right:-5px;top:4px;bottom:4px;width:4px;background:{ACC};opacity:0}}
.void{{position:absolute;left:700px;top:462px;width:520px;height:316px;border:3px dashed {AMB};border-radius:22px;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:22px}}
.vl{{display:flex;align-items:center;gap:14px;font:500 34px Inter;color:#C6CDD3}}
.ans{{position:absolute;left:1296px;top:368px;width:524px;height:504px;background:#fff;border-radius:20px;padding:26px 30px;color:{INK};box-shadow:0 22px 60px rgba(0,0,0,.45)}}
.at{{font:700 31px Inter;margin-top:8px;white-space:nowrap}}
.rgs{{position:absolute;left:30px;right:30px;top:110px;height:190px;display:flex;justify-content:space-between;align-items:flex-end}}
.rg{{display:flex;flex-direction:column;align-items:center;gap:8px;font:500 21px Inter}}
.rgb{{width:76px;border-radius:7px 7px 0 0}}
.dchip.q{{height:100px;width:500px;font-size:30px}}
.act{{position:absolute;left:30px;right:30px;bottom:30px;height:90px;border-radius:16px;background:{BLUE};color:#fff;font:700 32px Inter;display:flex;align-items:center;justify-content:center;gap:14px}}
.act.done{{background:#0B8A5A}}
#q-rip{{position:absolute;left:12px;top:220px;width:500px;height:500px;border-radius:50%;background:radial-gradient(rgba(11,138,90,.55),rgba(11,138,90,0) 70%)}}
#q-glow{{position:absolute;left:60px;top:150px;width:1800px;height:620px;background:radial-gradient(closest-side,rgba(38,153,251,.3),rgba(38,153,251,0))}}
/* end */
.endc{{background:linear-gradient(135deg,#2A92F5 0%,#0F6FE0 55%,#0A5ACB 100%)}}
#e-logo{{position:absolute;left:560px;top:344px;width:800px}}
.ering{{position:absolute;left:730px;top:220px;width:460px;height:460px;border-radius:50%;border:4px solid #fff}}
#e-tag{{position:absolute;left:0;width:1920px;top:596px;text-align:center;font:500 42px Inter;color:#EAF4FF}}
#e-url{{position:absolute;left:0;width:1920px;top:940px;text-align:center;font:600 32px Inter;color:#fff}}
/* captions: the reference's dark box and word highlight; key chunks in solid blue */
.capw{{position:absolute;left:1210px;top:650px;width:690px;height:140px;display:flex;justify-content:center;align-items:center;z-index:6}}
.capbox{{background:rgba(38,36,33,.88);border-radius:14px;padding:18px 28px;font:500 54px Inter;color:#fff;white-space:nowrap;letter-spacing:-.005em;box-shadow:0 10px 26px rgba(0,0,0,.18)}}
.capbox.hot{{background:{BLUE};font-weight:600;box-shadow:0 12px 34px rgba(0,110,218,.45)}}
.cw2{{display:inline-block}}
#logo{{position:absolute;right:36px;top:30px;width:320px;height:82px;z-index:30;transform-origin:100% 0}}
#logo img{{position:absolute;right:0;top:0;width:320px;height:auto}}
#wm-d,#wm-w{{position:absolute;right:38px;bottom:30px;height:50px;width:auto;z-index:31}}
'''
FILTERS = '<svg width="0" height="0" style="position:absolute"><defs>' + ''.join(
    f'<filter id="m{a}{i}" x="-20%" y="-20%" width="140%" height="140%"><feGaussianBlur stdDeviation="{(str(v) + " 0") if a == "x" else ("0 " + str(v))}"/></filter>'
    for a in 'xy' for i, v in ((1, 8), (2, 18), (3, 30))) + '</defs></svg>'
page = f'''<!doctype html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=1920, height=1080">
<script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
<style>{CSS}</style></head><body>
<div id="root" data-composition-id="main" data-start="0" data-duration="{n(TOTAL)}" data-width="1920" data-height="1080">
{FILTERS}
<div id="camwrap"><div id="cam"><div id="cam2"><div id="cam3"><video id="aroll" class="clip" data-start="0" data-duration="{n(VID)}" data-track-index="0" muted playsinline src="{AROLL}"></video></div></div></div></div>
<audio id="mix" class="clip" data-start="0" data-duration="{n(TOTAL)}" data-track-index="1" src="assets/mix.wav"></audio>
<div id="nameband"><span id="nm0">Rahul Thota</span><span id="nm1" style="opacity:0">Amrit Vatsa</span><span id="nm2" style="opacity:0">Anshuman Agrawal</span></div><div id="pill">Rahul Thota</div>
{chr(10).join(html)}
<div id="flash"></div><div id="flash2"></div><div id="flash3"></div>
{blinds_html}
<div id="logo"><img id="logo-d" src="assets/logo.svg"><img id="logo-w" src="assets/logo_white.svg" style="opacity:0"></div>
<img id="wm-w" src="assets/sd_white.png" style="opacity:.85"><img id="wm-d" src="assets/sd_dark.png" style="opacity:0">
</div>
<script>
window.__timelines = window.__timelines || {{}};
const tl = gsap.timeline({{paused:true}});
const S=(s,v)=>gsap.set(s,v), A=(s,v,t)=>tl.to(s,v,t);
function typeIn(sel,t0,dur){{const e=[...document.querySelectorAll(sel)];const dt=dur/e.length;
 e.forEach((c,i)=>{{const t=t0+i*dt,car=c.querySelector('i');tl.set(c,{{opacity:1}},t);tl.set(car,{{opacity:1}},t);if(i<e.length-1)tl.set(car,{{opacity:0}},t+dt);}});}}
gsap.set('#s-band',{{skewX:-16}});
{chr(10).join(js)}
tl.set({{}},{{}},{n(TOTAL)});
window.__timelines["main"] = tl;
</script></body></html>'''
open('film/index.html', 'w', encoding='utf-8').write(page)
json.dump(sfx, open('build/sfx_cues.json', 'w'), indent=0)
json.dump({lid: [dict(x) for x in ws] for lid, ws in by.items()}, open('build/words_fixed.json', 'w'), indent=0)
uses = {}
for h in sfx: uses[h['file']] = uses.get(h['file'], 0) + 1
over = {k: v for k, v in uses.items() if v > 2}
assert not over, f'sound used more than twice: {over}'
print('total', TOTAL, 'aroll', AROLL, 'tweens', len(js), '| sfx cues', len(sfx), 'unique', len(uses), '| caption chunks', ci, '| cutaways', [(round(a, 2), k) for a, k, _ in PLAN])
print('unused sounds:', sorted(set(os.path.basename(p)[:-4] for p in __import__('glob').glob('build/audio/fx3/*.wav')) - set(uses)))
