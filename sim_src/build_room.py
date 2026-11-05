"""강의실 3D: Blender 안에서 실행. 모든 걸 한 메시로 짓고, Cycles로 빛을 구워 lightmap + glb + env를 내보냄.
blender -b -P build_room.py -- <out> <lightmap_px> <samples>
좌표: x 서→동(동쪽=화이트보드), y 남→북(북쪽=창문), z 위. 단위 m."""
import bpy, bmesh, math, json, os, sys, random
import numpy as np
from mathutils import Vector
argv = sys.argv[sys.argv.index('--') + 1:]
OUT, LM_PX, SAMPLES = argv[0], int(argv[1]), int(argv[2])
TEX = os.path.join(os.path.dirname(os.path.abspath(sys.argv[sys.argv.index('-P') + 1])), 'tex')
random.seed(30)
W, D, H = 9.6, 10.2, 2.75

# ─── 재질: color=sRGB, map=질감, s=(가로m, 세로m) 한 장 크기 (None이면 면에 맞춤), rough/metal은 웹에서도 씀
M = {
 'floor':   dict(map='floor', s=(W, D), rough=.42, gain=.82),
 'block':   dict(map='block', s=(1.2, 1.6), rough=.95, gain=1.5),
 'plaster': dict(map='plaster', s=(7.2, 3.6), rough=.8, gain=1.95, tint='#fffbf2'),
 'ceiling': dict(map='ceiling', s=(1.2, 1.2), rough=1, gain=1.5),
 'table':   dict(map='table', rough=.38, gain=.86),
 'table2':  dict(map='table2', rough=.38, gain=.86),
 'ply':     dict(color='#d6cbaf', rough=.6),
 'edge':    dict(color='#d8d6cc', rough=.5),
 'gframe':  dict(color='#8d9196', rough=.45, metal=.6),
 'kframe':  dict(color='#17181a', rough=.5, metal=.3),
 'wood':    dict(map='wood', rough=.28, gain=.55),
 'kwood':   dict(color='#17171a', rough=.3),
 'chrome':  dict(color='#a4a6a8', rough=.18, metal=1),
 'red':     dict(color='#5e1a20', rough=.42, gain=.8),
 'grey':    dict(color='#9a9da0', rough=.45, metal=.5),
 'skirt':   dict(color='#4d3f38', rough=.5),
 **{f'door{k}': dict(color='#5f936a', rough=.42, unlit=True) for k in 'AB'},
 **{f'handle{k}': dict(color='#b9bcbe', rough=.25, metal=1) for k in 'AB'},
 **{f'doorglass{k}': dict(map='door_glass', rough=.08, unlit=True) for k in 'AB'},
 'dframe':  dict(color='#5a8a60', rough=.45, gain=.7),
 'wframe':  dict(color='#d9dbd8', rough=.4),
 'wdark':   dict(color='#3b4047', rough=.4),
 'wglass':  dict(color='#1b1f24', rough=.08),
 'blind':   dict(map='blind', rough=1),
 'frost':   dict(color='#d6e4e4', rough=.2, emit=2.0),
 'sheer':   dict(color='#d8c9a6', rough=1, emit=.9),
 'board':   dict(color='#a9abb8', rough=.16, gain=.9),
 'steel':   dict(color='#b9bcbe', rough=.25, metal=1),
 'tv':      dict(color='#08090b', rough=.1),
 'white':   dict(color='#e6e6e2', rough=.45, gain=.82),
 'rubber':  dict(color='#111112', rough=.8),
 'led':     dict(color='#ffffff', rough=1, emit=9.0),
 'exit':    dict(map='exit', rough=1, emit=1.6),
 'switches':dict(map='switches', rough=.5),
 'paper':   dict(color='#dcdcd6', rough=.9, unlit=True),
 'extred':  dict(color='#a81a1c', rough=.3),
 'galv':    dict(color='#8f9396', rough=.4, metal=.8),
 'orange':  dict(color='#b5532a', rough=.4),
}
exec(open(os.path.join(os.path.dirname(TEX), 'kit.py')).read())

# ─── 방 껍데기: 벽 안쪽 면이 치수 기준, 바깥으로 두께 .25
TH = .25
box(-TH, W + TH, -TH, D + TH, -.2, 0, 'floor')
box(-TH, W + TH, -TH, D + TH, H, H + .2, 'ceiling')
box(-TH, 0, -TH, D + TH, 0, H, 'plaster')                 # 서: 크림 긴 벽
box(W, W + TH, -TH, D + TH, 0, H, 'plaster')              # 동: 화이트보드 벽
DOOR_H = 2.25
DOORS = [{'id': 'A', 'x0': 3.8, 'x1': 4.75}, {'id': 'B', 'x0': 8.2, 'x1': 9.15}]  # 문 뒤는 객차로 이어짐
for a_, b_ in ((-TH, 3.8), (4.75, 8.2), (9.15, W + TH)): box(a_, b_, -TH, 0, 0, H, 'block')  # 남: 벽돌, 문 자리는 뚫음
for d_ in DOORS: box(d_['x0'], d_['x1'], -TH, 0, DOOR_H, H, 'block')
# 남쪽 돌출: 동쪽 혹, 벽돌 피어(낙서 있던 곳), 크림 기둥
box(9.35, W, 0, 1.0, 0, H, 'plaster')
box(6.1, 7.3, 0, .3, 0, H, 'block')
box(5.35, 6.1, 0, .45, 0, H, 'plaster')
# 북쪽: 창 뚫기. (x0, x1)
WINS = [(2.42, 4.02), (5.5, 7.0), (7.75, 8.55)]
SHEER = (.75, 1.68)
sill, head = .28, 2.2
xs = [0] + [v for w in [SHEER] + WINS for v in w] + [W]
box(0, W, D, D + TH, head, H, 'plaster')
box(0, W, D, D + TH, 0, sill, 'plaster')
for a, b in zip(xs[0::2], xs[1::2]): box(a, b, D, D + TH, sill, head, 'plaster')
box(4.37, 5.37, D - .4, D, 0, H, 'plaster')                # 북쪽 기둥
box(9.25, W, D - .35, D, 0, H, 'plaster')
# 커튼 내린 칸: 뒤에서 빛이 비침
box(*SHEER, D + .12, D + .2, sill, head, 'sheer')
box(SHEER[0] - .1, SHEER[1] + .1, D - .06, D - .01, .15, H - .02, 'blind')
for x0, x1 in WINS:
    box(x0, x1, D + .12, D + .2, sill, .9, 'frost')       # 불투명 아래 유리
    fr = .035
    for z0, z1 in ((sill, sill + fr), (.9, .95), (1.24, 1.3), (head - fr, head)):
        box(x0, x1, D + .03, D + .12, z0, z1, 'wframe')
    box(x0, x0 + fr, D + .03, D + .12, sill, head, 'wframe'); box(x1 - fr, x1, D + .03, D + .12, sill, head, 'wframe')
    mid = (x0 + x1) / 2
    if x1 - x0 > 1: box(mid - .03, mid + .03, D + .03, D + .12, .9, head, 'wframe')
    for k in (x0 + .25, mid + .25 if x1 - x0 > 1 else None):
        if k: box(k, k + .1, D + .02, D + .04, 1.2, 1.215, 'rubber')  # 손잡이
    box(x0 - .1, x1 + .1, D - .06, D - .01, head - .05, H - .02, 'blind')
# 굽도리
SK = .1
for a in ((0, 9.35, 0, .012), (0, 6.1, .45, .462), (6.1, 7.3, .3, .312), (7.3, 9.35, 0, .012)): pass
def skirt(x0, x1, y0, y1): box(x0, x1, y0, y1, 0, SK, 'skirt')
skirt(0, .012, 0, D); skirt(W - .012, W, 1, D - .35); skirt(9.338, 9.35, 0, 1); skirt(9.35, W, .988, 1)
skirt(0, 3.8, 0, .012); skirt(4.75, 5.35, 0, .012); skirt(5.35, 6.1, .45, .462); skirt(5.338, 5.35, 0, .45); skirt(6.1, 6.112, .3, .45)
skirt(6.112, 7.3, .3, .312); skirt(7.3, 7.312, 0, .3); skirt(7.312, 8.2, 0, .012); skirt(9.15, 9.35, 0, .012)
# ─── 초록 문 2개
def door(x0, x1, k):
    h = DOOR_H
    box(x0 - .05, x0, 0, .03, 0, h + .05, 'dframe'); box(x1, x1 + .05, 0, .03, 0, h + .05, 'dframe'); box(x0 - .05, x1 + .05, 0, .03, h, h + .05, 'dframe')
    box(x0, x1, 0, .015, 0, h, f'door{k}')
    gz0, gz1 = 1.28, 1.5; gx0, gx1 = x0 + .06, x1 - .06
    box(gx0 - .012, gx1 + .012, 0, .018, gz0 - .012, gz1 + .012, f'door{k}')
    face([(gx1, .019, gz0), (gx0, .019, gz0), (gx0, .019, gz1), (gx1, .019, gz1)], f'doorglass{k}', uvs=[(0, 0), (1, 0), (1, 1), (0, 1)])
    # 레버 손잡이 (x0 쪽)
    hx = x0 + .09
    sweep([(hx, .015, 1.0), (hx, .05, 1.0)], .028, f'handle{k}', 12)
    sweep([(hx, .05, 1.0), (hx, .065, 1.0), (hx + .12, .065, .995)], .009, f'handle{k}', 8)
door(3.8, 4.75, 'A'); door(8.2, 9.15, 'B')
# 비상구 등: 문1 위
ex, ez = 8.68, 2.5
box(ex - .1, ex + .1, 0, .06, ez - .08, ez + .17, 'white')
face([(ex + .085, .061, ez - .065), (ex - .085, .061, ez - .065), (ex - .085, .061, ez + .155), (ex + .085, .061, ez + .155)], 'exit')
# 남벽 높은 창 3개 (복도쪽)
for cx in (3.05, 1.95, .9):
    box(cx - .27, cx + .27, 0, .004, 1.85, 2.39, 'wdark')
    box(cx - .22, cx + .22, 0, .009, 1.9, 2.34, 'wglass')
    box(cx - .03, cx + .03, 0, .02, 1.9, 2.34, 'wdark'); box(cx - .08, cx - .02, 0, .05, 2.08, 2.2, 'rubber')
# 스위치·온도조절기 사진 한 장
face([(3.65, .006, 1.17), (3.2, .006, 1.17), (3.2, .006, 1.45), (3.65, .006, 1.45)], 'switches', uvs=[(0, 0), (1, 0), (1, 1), (0, 1)])
for sx in (7.65, 7.42): box(sx, sx + .09, 0, .012, 1.15, 1.31, 'white')
# 기둥 표지판: 비밀번호가 보이지 않게 빈 판으로
box(5.65, 5.83, .45, .456, 1.78, 1.92, 'white')
# ─── 화이트보드 벽
BY0, BY1, BZ0, BZ1 = 2.95, 8.95, .98, 2.2
face([(W - .012, BY1, BZ0), (W - .012, BY0, BZ0), (W - .012, BY0, BZ1), (W - .012, BY1, BZ1)], 'board')
for a in ((BZ0 - .035, BZ0), (BZ1, BZ1 + .03)): box(W - .03, W, BY0 - .03, BY1 + .03, *a, 'steel')
for a in ((BY0 - .03, BY0), (BY1, BY1 + .03)): box(W - .03, W, *a, BZ0, BZ1, 'steel')
box(W - .08, W - .012, BY0, BY1, BZ0 - .05, BZ0 - .035, 'steel')   # 받침
box(W - .05, W - .02, 5.6, 5.72, BZ0 - .035, BZ0 - .01, 'orange')   # 지우개
box(W - .14, W, 4.2, 7.6, 2.42, 2.5, 'wframe')                     # 말린 스크린
# TV 두 대
def tv(yc, w, h, zc, frame):
    d = .07; x = W - .32
    box(x, x + d, yc - w / 2, yc + w / 2, zc - h / 2, zc + h / 2, frame)
    b = .02 if frame == 'white' else .006
    face([(x - .001, yc - w / 2 + b, zc - h / 2 + b * 1.5), (x - .001, yc - w / 2 + b, zc + h / 2 - b), (x - .001, yc + w / 2 - b, zc + h / 2 - b), (x - .001, yc + w / 2 - b, zc - h / 2 + b * 1.5)], 'tv')
tv(7.15, 1.75, 1.02, 1.56, 'white')
box(W - .3, W - .12, 6.98, 7.32, 0, 1.05, 'white'); box(W - .55, W - .04, 6.75, 7.55, 0, .07, 'white')
tv(4.25, 1.95, 1.12, 1.55, 'tv')
box(W - .26, W - .12, 4.02, 4.48, 0, 1.0, 'kframe'); box(W - .28, W - .1, 3.97, 4.02, 0, 1.0, 'white'); box(W - .28, W - .1, 4.48, 4.53, 0, 1.0, 'white')
box(W - .62, W - .04, 3.75, 4.75, .03, .1, 'white')
for dy in (3.82, 4.68):
    sweep([(W - .5, dy, .03), (W - .5, dy, .0)], .03, 'rubber', 8)
sweep(smooth_path([(W - .25, 3.45, 1.0), (W - .02, 3.25, .55), (W - .01, 3.05, .34)], 6), .004, 'rubber', 5)
box(W - .012, W, 3.0, 3.08, .28, .4, 'white')                     # 콘센트
# ─── 천장 설비
COLS = (1.45, 4.05, 6.55, 8.75); ROWS = (1.4, 4.1, 6.8, 9.2)
for cx in COLS:
    for cy in ROWS:
        box(cx - .165, cx + .165, cy - .615, cy + .615, H - .018, H, 'white')
        face([(cx - .15, cy + .6, H - .019), (cx + .15, cy + .6, H - .019), (cx + .15, cy - .6, H - .019), (cx - .15, cy - .6, H - .019)], 'led')
def cassette(cx, cy):
    s = .47; box(cx - s, cx + s, cy - s, cy + s, H - .04, H, 'white')
    for dx, dy, l, w in ((0, -.36, .34, .045), (0, .36, .34, .045), (-.36, 0, .045, .34), (.36, 0, .045, .34)):
        box(cx + dx - l, cx + dx + l, cy + dy - w, cy + dy + w, H - .043, H - .04, 'rubber')
    for i in range(-5, 6): box(cx - .27, cx + .27, cy + i * .05 - .009, cy + i * .05 + .009, H - .05, H - .04, 'wframe')
cassette(5.5, 7.6); cassette(7.6, 3.1)
def projector(cx, cy):
    sweep([(cx, cy, H), (cx, cy, H - .28)], .025, 'kframe', 8)
    box(cx - .18, cx + .18, cy - .16, cy + .16, H - .42, H - .28, 'white')
    sweep([(cx, cy - .16, H - .35), (cx, cy - .19, H - .35)], .04, 'rubber', 12)
projector(5.9, 6.6)
s = .3; box(6.1 - s, 6.1 + s, 3.0 - s, 3.0 + s, H - .006, H, 'wframe'); box(6.1 - s + .02, 6.1 + s - .02, 3 - s + .02, 3 + s - .02, H - .008, H - .006, 'ceiling')
for sx, sy in ((3.0, 5.4), (7.8, 5.4), (2.5, 2.2)): sweep([(sx, sy, H), (sx, sy, H - .012)], .09, 'wframe', 16)

# ─── 책상
TH_Z = .82
def frame(x, y, w, l, mat, T=None):
    """w: x폭, l: y길이. 네 다리 + 위 띠 + 아래 띠"""
    a = .02
    x0, x1, y0, y1 = x - w / 2 + .02, x + w / 2 - .02, y - l / 2 + .02, y + l / 2 - .02
    for px, py in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)):
        box(px - a, px + a, py - a, py + a, 0, TH_Z - .03, mat)
    box(x0, x1, y0 - a, y0 + a, TH_Z - .07, TH_Z - .03, mat); box(x0, x1, y1 - a, y1 + a, TH_Z - .07, TH_Z - .03, mat)
    box(x0 - a, x0 + a, y0, y1, TH_Z - .07, TH_Z - .03, mat); box(x1 - a, x1 + a, y0, y1, TH_Z - .07, TH_Z - .03, mat)
    box(x0, x1, y0 - a, y0 + a, 0, .03, mat); box(x0, x1, y1 - a, y1 + a, 0, .03, mat)
    box(x1 - a, x1 + a, y0, y1, 0, .03, mat)
colliders = []
def table(x, y, w=.8, l=1.2, frame_mat='gframe', tex='table'):
    frame(x, y, w, l, frame_mat)
    # 윗면 사진 맞춤: 방향·좌우를 책상마다 바꿔 같은 자국이 안 보이게
    k = random.choice([(0, 0, 1, 1), (1, 1, 0, 0), (1, 0, 0, 1), (0, 1, 1, 0)])
    u0, v0, u1, v1 = k
    box(x - w / 2, x + w / 2, y - l / 2, y + l / 2, TH_Z - .03, TH_Z, 'edge')
    x0, x1, y0, y1 = x - w / 2, x + w / 2, y - l / 2, y + l / 2
    face([(x0, y0, TH_Z + .001), (x1, y0, TH_Z + .001), (x1, y1, TH_Z + .001), (x0, y1, TH_Z + .001)], tex, uvs=[(u0, v0), (u1, v0), (u1, v1), (u0, v1)])
    colliders.append([x0, y0, x1, y1])
def curved_table(x, y):
    """합판 곡선 책상 (1번 사진 위쪽)"""
    w, l = .82, .9; n = 24; zt, zb = TH_Z, TH_Z - .035
    north = [(x - w / 2 + w * i / n, y + l / 2) for i in range(n + 1)]  # 북쪽 변: 곧음
    south = [(x - w / 2 + w * i / n, y - l / 2 - .12 * math.sin(i / n * math.pi) ** .6) for i in range(n + 1)]  # 남쪽 변: 볼록
    uv = lambda p: ((p[0] - (x - w / 2)) / w, (p[1] - (y - l / 2 - .12)) / (l + .12))
    tv = {p: bm.verts.new((*p, zt)) for p in south + north}
    for i in range(n):
        a_, b_, c_, d_ = south[i], south[i + 1], north[i + 1], north[i]
        q = (a_, b_, c_, d_)
        f = bm.faces.new([tv[p] for p in q]); f.material_index = idx['table2']
        for loop_, p in zip(f.loops, q): loop_[uvl].uv = uv(p)
        face([(*p, zb) for p in q[::-1]], 'edge', uvs=[(0, 0)] * 4)
        for p, r in ((a_, b_), (c_, d_)):
            face([(*p, zb), (*r, zb), (*r, zt), (*p, zt)], 'ply', uvs=[(0, 0), (1, 0), (1, 1), (0, 1)], smooth=True)
    for p, r in ((south[n], north[n]), (north[0], south[0])):
        face([(*p, zb), (*r, zb), (*r, zt), (*p, zt)], 'ply', uvs=[(0, 0), (1, 0), (1, 1), (0, 1)])
    for dx, dy in ((-.3, -.32), (.3, -.32), (-.3, .32), (.3, .32)):
        sweep([(x + dx, y + dy, 0), (x + dx, y + dy, zb)], .022, 'grey', 10)
    colliders.append([x - w / 2, y - l / 2 - .12, x + w / 2, y + l / 2])

# ─── 의자
def profile(points, n=20):
    p = smooth_path(points, max(2, n // (len(points) - 1) + 1)); return p
PAG = [(.215, .425), (.19, .435), (.10, .415), (0, .405), (-.10, .41), (-.17, .44), (-.205, .50), (-.21, .56), (-.225, .64), (-.255, .72), (-.285, .79)]
ARM = [(.22, .44), (.15, .452), (0, .445), (-.15, .45), (-.205, .49), (-.225, .58), (-.25, .68), (-.27, .78), (-.29, .84)]
def pag_w(t):
    k = [(0, .19), (.1, .2), (.42, .205), (.56, .175), (.66, .118), (.74, .135), (.86, .172), (1, .178)]
    for (a, va), (b, vb) in zip(k, k[1:]):
        if t <= b:
            s = (t - a) / (b - a); s = s * s * (3 - 2 * s); return va + (vb - va) * s
    return k[-1][1]
def arm_w(t): return .2 if t < .4 else .185
def shell(prof, wf, mat, T, thick=.012, cols=14, seatdish=.015, backdish=.03):
    pts = prof; N = len(pts); top = []; bot = []
    for i, p in enumerate(pts):
        t = i / (N - 1)
        d = (pts[min(i + 1, N - 1)] - pts[max(i - 1, 0)]).normalized()
        nrm = Vector((d.z, 0, -d.x))  # 앉는 면 쪽(+z/+x)
        w = wf(t)
        if t < .06: w *= math.sqrt(max(1 - ((.06 - t) / .06) ** 2 * .5, 0))
        if t > .86: w *= math.sqrt(max(1 - ((t - .86) / .14) ** 2 * .6, 0))
        c = seatdish * (1 - min(1, t / .5) ** 3) + backdish * max(0, min(1, (t - .62) / .2)) ** 2
        rt, rb = [], []
        for j in range(cols + 1):
            v = -1 + 2 * j / cols
            q = p + Vector((0, v * w, 0)) + nrm * c * v * v
            rt.append(T(tuple(q))); rb.append(T(tuple(q - nrm * thick)))
        top.append(rt); bot.append(rb)
    vt = [[bm.verts.new(q) for q in r] for r in top]; vb = [[bm.verts.new(q) for q in r] for r in bot]
    def quad(a, b, c, d, uva=None):
        f = bm.faces.new((a, b, c, d)); f.material_index = idx[mat]; f.smooth = True
        if uva:
            for l, uv in zip(f.loops, uva): l[uvl].uv = uv
    for i in range(N - 1):
        for j in range(cols):
            u0, u1, v0, v1 = j / cols, (j + 1) / cols, i / (N - 1), (i + 1) / (N - 1)
            quad(vt[i][j], vt[i][j + 1], vt[i + 1][j + 1], vt[i + 1][j], [(u0, v0), (u1, v0), (u1, v1), (u0, v1)])
            quad(vb[i][j + 1], vb[i][j], vb[i + 1][j], vb[i + 1][j + 1], [(u1, v0), (u0, v0), (u0, v1), (u1, v1)])
    for i in range(N - 1):
        quad(vt[i][0], vt[i + 1][0], vb[i + 1][0], vb[i][0], [(0, 0), (.02, 0), (.02, .02), (0, .02)])
        quad(vt[i + 1][cols], vt[i][cols], vb[i][cols], vb[i + 1][cols], [(0, 0), (.02, 0), (.02, .02), (0, .02)])
    for j in range(cols):
        quad(vt[0][j + 1], vt[0][j], vb[0][j], vb[0][j + 1], [(0, 0), (.02, 0), (.02, .02), (0, .02)])
        quad(vt[N - 1][j], vt[N - 1][j + 1], vb[N - 1][j + 1], vb[N - 1][j], [(0, 0), (.02, 0), (.02, .02), (0, .02)])
PAG_P = profile([Vector((a, 0, b)) for a, b in PAG], 40); ARM_P = profile([Vector((a, 0, b)) for a, b in ARM], 16)
def chair(x, y, rot, black=False, tag=True, paper=False):
    T = place(x, y, rot)
    shell(PAG_P, pag_w, 'kwood' if black else 'wood', T)
    # 크롬 썰매 다리: 좌우 한 벌씩, 뒤에서 앞으로 이어짐
    for s in (-1, 1):
        path = smooth_path([(.10, s * .10, .405), (.14, s * .15, .34), (.235, s * .21, .05), (.215, s * .215, .012), (.08, s * .215, .01), (-.2, s * .215, .01), (-.235, s * .21, .05), (-.16, s * .14, .33), (-.12, s * .10, .40)], 4)
        sweep(path, .0095, 'chrome', 7, T=T)
        for fx in (.14, -.17): box(fx - .022, fx + .022, s * .215 - .012, s * .215 + .012, 0, .006, 'white', T=T)
    if tag and not black and random.random() < .8:
        box(-.255, -.25, -.05, .05, .655, .69, 'paper', T=T)
    if paper: box(-.13, .13, -.1, .14, .442, .443, 'paper', T=T)
    colliders.append([x - .2, y - .2, x + .2, y + .2])
def armchair(x, y, rot):
    T = place(x, y, rot)
    shell(ARM_P, arm_w, 'red', T, thick=.016, seatdish=.012, backdish=.035)
    for sx, sy in ((.18, .2), (.18, -.2), (-.19, .2), (-.19, -.2)):
        sweep(smooth_path([(sx * .7, sy * .7, .44), (sx, sy, .22), (sx * 1.05, sy * 1.05, .03)], 4), .013, 'grey', 7, T=T)
        sweep([(sx * 1.05, sy * 1.05, .05), (sx * 1.05, sy * 1.05, 0)], .017, 'rubber', 8, T=T)
    for s in (-1, 1):
        sweep(smooth_path([(-.24, s * .19, .62), (-.12, s * .235, .655), (.08, s * .235, .64), (.17, s * .22, .46)], 5), .014, 'grey', 7, T=T)
    colliders.append([x - .25, y - .25, x + .25, y + .25])

jit = lambda a=.12: random.uniform(-a, a)
EAST = 0
def row(x, ys, black=(), chair_on=True, tex='table', frame_mat='gframe'):
    for k, y in enumerate(ys):
        table(x, y, frame_mat=frame_mat, tex=tex)
        if chair_on: chair(x - .55 + jit(.03), y + jit(.08), EAST + jit(), black=k in black)
# R1 서쪽 벽 줄 (6번): 의자 등이 벽을 봄
row(1.15, (2.05, 3.27), black=())
row(1.15, (4.75, 5.97, 7.19, 8.41), black=(3,))
# R2
table(3.4, 1.72, frame_mat='kframe')                 # 검은 다리 (1·8번 맨 앞)
chair(2.85, 1.72, .25, tag=False)
curved_table(3.4, 2.92)
armchair(2.8, 2.9, 0)
table(3.4, 4.25, l=1.6); chair(2.85, 4.3, jit())
row(3.4, (6.1, 7.3, 8.5), black=(1,))
# R3
row(5.7, (2.1, 3.32, 4.54), black=())
row(5.7, (6.4, 7.62, 8.84), black=(0, 2))
# R4 앞줄: 접이식 긴 책상 3 + 책상 1, 뒤쪽 창가 2
for y in (3.1, 4.6, 6.1):
    x = 7.75
    box(x - .3, x + .3, y - .74, y + .74, .76, .79, 'edge', top=None)
    face([(x - .3, y - .74, .791), (x + .3, y - .74, .791), (x + .3, y + .74, .791), (x - .3, y + .74, .791)], 'table')
    box(x + .05, x + .07, y - .68, y + .68, .35, .72, 'wdark')
    for s in (-1, 1):
        box(x + .03, x + .09, y + s * .66 - .025, y + s * .66 + .025, 0, .76, 'kframe'); box(x - .28, x + .28, y + s * .66 - .025, y + s * .66 + .025, 0, .03, 'kframe')
    colliders.append([x - .3, y - .74, x + .3, y + .74])
chair(7.15, 2.95, jit()); chair(7.15, 4.65, jit(), black=True); chair(7.15, 6.05, jit())
row(7.85, (7.75, 8.97), black=(0, 1))
box(7.55, 8.05, 8.8, 9.1, TH_Z + .001, TH_Z + .002, 'paper')
# 작은 선생님 책상 + 뒤 의자 둘
x, y = 8.55, 5.65
box(x - .25, x + .25, y - .55, y + .55, .68, .71, 'edge'); face([(x - .25, y - .55, .711), (x + .25, y - .55, .711), (x + .25, y + .55, .711), (x - .25, y + .55, .711)], 'table')
for s in (-1, 1): box(x - .23, x + .23, y + s * .5 - .02, y + s * .5 + .02, 0, .68, 'grey')
sweep([(x - .05, y + .1, .722), (x + .08, y + .05, .722)], .009, 'rubber', 6)
colliders.append([x - .25, y - .55, x + .25, y + .55])
chair(9.05, 5.15, math.pi + .2, tag=False); chair(9.05, 6.2, math.pi - .15, tag=False)
# 낱개 의자·소품
chair(8.6, 1.75, 2.6)                            # 7번 오른쪽 혼자 있는 의자
chair(3.5, .45, 2.5, tag=False)                  # 4번 갈색 의자
chair(5.0, .75, 2.2, black=True, tag=False, paper=True)  # 4번 종이 놓인 검은 의자
chair(1.5, .55, 1.2, black=True, tag=False)      # 2번 구석 검은 의자
armchair(1.1, 1.1, 1.57); armchair(.75, 1.15, 1.57 + .05)
armchair(.45, 7.0, -.5) if False else None
# 흰 스툴 (2번)
sx, sy = .62, .3
sweep([(sx, sy, .4), (sx, sy, .43)], .17, 'white', 20)
for a in (.8, 2.37, 3.94, 5.5):
    sweep(smooth_path([(sx + math.cos(a) * .12, sy + math.sin(a) * .12, .41), (sx + math.cos(a) * .16, sy + math.sin(a) * .16, .32), (sx + math.cos(a) * .17, sy + math.sin(a) * .17, 0)], 4), .013, 'white', 7)
colliders.append([sx - .19, sy - .19, sx + .19, sy + .19])
# 소화기 (2번)
sweep([(.2, .22, .0), (.2, .22, .44)], .075, 'extred', 14); sweep([(.2, .22, .44), (.2, .22, .52)], .022, 'rubber', 8)
# 플립차트 (창가 오른쪽)
fx, fy = 8.75, 9.45
face([(fx - .4, fy, .75), (fx + .4, fy + .2, .75), (fx + .4, fy + .2, 1.5), (fx - .4, fy, 1.5)], 'paper', uvs=[(0, 0)] * 4)
for dx in (-.35, .35): sweep([(fx + dx, fy + .1, 0), (fx + dx, fy + .1, .78)], .012, 'grey', 7)
colliders.append([fx - .45, fy - .1, fx + .45, fy + .3])
# 바닥 배선관 + 박스 (1·8번)
PIPES = [[(2.35, .7), (2.35, 9.7)], [(4.6, 1.0), (4.6, 9.6)], [(2.35, 5.1), (4.6, 5.1)], [(.1, 9.3), (2.35, 9.3)]]
for p in PIPES:
    a, b = p; sweep([(a[0], a[1], .013), (b[0], b[1], .013)], .011, 'galv', 8)
for bx, by in ((2.35, 2.45), (2.35, 5.1), (4.6, 5.1), (4.6, 2.9), (2.35, 7.8), (4.6, 7.9)):
    box(bx - .05, bx + .05, by - .07, by + .07, 0, .07, 'galv')
# 흰 전선 + 멀티탭 (8번)
box(4.45, 4.55, 1.25, 1.42, .0, .04, 'white')
cord = smooth_path([(4.5, 1.42, .03), (4.1, 1.75, .006), (3.65, 1.3, .006), (3.95, .9, .006), (3.3, 1.05, .006), (3.05, 1.6, .25), (3.0, 1.95, .46)], 8)
sweep(cord, .004, 'white', 5)
box(2.9, 3.1, 1.95, 2.0, .45, .49, 'white')

colliders += [[-3, -.3, 3.8, 0], [4.75, -.3, 8.2, 0], [9.15, -.3, 16, 0], [-1, D, W + 1, D + 1], [-1, -.3, 0, D + 1], [W, -.3, W + 1, D + 1],
              [9.35, 0, W, 1], [6.1, 0, 7.3, .3], [5.35, 0, 6.1, .45], [4.37, D - .4, 5.37, D], [9.25, D - .35, W, D],
              [W - .62, 3.75, W, 4.75], [W - .55, 6.75, W, 7.55], [.1, .1, .3, .35]]

finish((W / 2, D / 2, 1.0), 3.2, {'size': [W, D, H], 'colliders': [[round(v, 3) for v in c] for c in colliders], 'doors': DOORS})
