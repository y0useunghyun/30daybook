"""내 방: 객차 남쪽 문 뒤. 들어가면 창문을 마주 봄. 왼쪽(동쪽) 벽에 책상·거울·책장, 오른쪽(서쪽)에 빈 매트리스.
책상엔 모니터 둘·키보드·마우스만. 책장 칸은 사진 그대로. blender -b -P build_myroom.py -- <out> <lightmap_px> <samples>"""
import bpy, bmesh, math, json, os, sys, random
import numpy as np
from mathutils import Vector
argv = sys.argv[sys.argv.index('--') + 1:]
OUT, LM_PX, SAMPLES = argv[0], int(argv[1]), int(argv[2])
TEX = os.path.join(os.path.dirname(os.path.abspath(sys.argv[sys.argv.index('-P') + 1])), 'tex_room')
RX0, RX1, RYN, RYS, H = 7.1, 10.2, -3.35, -7.25, 2.4
HX0, HX1, HZ = 8.2, 9.15, 2.0                     # 문 구멍
WX0, WX1, WZ0, WZ1 = 7.7, 9.2, .1, 2.1            # 창
M = {
 'carpet':  dict(map='carpet', s=(1.0, 1.0), rough=.95, gain=3.6, tint='#d7e4ff'),
 'wall':    dict(color='#f4f3ef', rough=.9, gain=1.75),   # 벽지 질감 없이 흰 벽
 'ceil':    dict(color='#e6e4dc', rough=.9, gain=2.3),
 'skirt':   dict(color='#e3e0d6', rough=.7, gain=1.6),
 'wf':      dict(color='#c6c8c4', rough=.45),
 'dwhite':  dict(color='#ecebe7', rough=.3),
 'whitem':  dict(color='#e9e9e6', rough=.4),
 'mat':     dict(color='#2a2b2d', rough=.8),
 'screen':  dict(color='#0d0e10', rough=.08),
 'bezel':   dict(color='#17181a', rough=.35),
 'kb':      dict(color='#26272a', rough=.5),
 'keys':    dict(map='keys', rough=.55),
 'mouse':   dict(color='#2b2c2f', rough=.35),
 'pc':      dict(color='#17181b', rough=.25),
 'mesh':    dict(color='#1b1c1e', rough=.85),
 'chrome':  dict(color='#5b5d60', rough=.3, metal=.8),
 'navy':    dict(color='#2c3a58', rough=.9),
 'mattress':dict(color='#d9d8d0', rough=.95, gain=1.5),
 'curtain': dict(map='curtain', s=(.55, 1.1), rough=.95, gain=1.5),
 'curtainw':dict(map='curtain_w', s=(.3, .9), rough=.95, gain=1.8),
 'rod':     dict(color='#1a1a1c', rough=.4),
 'peg':     dict(map='peg', s=(.1, .1), rough=.6),
 'tier1':   dict(map='tier1', rough=.9, gain=1.9),
 'tier2':   dict(map='tier2', rough=.9, gain=1.9),
 'tier3':   dict(map='tier3', rough=.9, gain=1.9),
 'blinds':  dict(map='blind_soft', rough=.9, emit=7.0, opacity=.84),
 'gapc':    dict(color='#d3d4d1', rough=.8, unlit=True),
 'plug':    dict(color='#000000', rough=1, unlit=True),
}
exec(open(os.path.join(os.path.dirname(TEX), 'kit.py')).read())
colliders = []
TH = .2
box(RX0 - TH, RX1 + TH, RYS - TH, -3.08, -.2, 0, 'carpet')
box(RX0 - TH, RX1 + TH, RYS - TH, RYN + TH, H, H + .2, 'ceil')
box(RX0 - TH, RX0, RYS - TH, RYN + TH, 0, H, 'wall')
box(RX1, RX1 + TH, RYS - TH, RYN + TH, 0, H, 'wall')
# 북쪽(들어온 쪽) 벽 + 문 구멍, 객차까지 잇는 틈
box(RX0 - TH, HX0, RYN, RYN + TH, 0, H, 'wall'); box(HX1, RX1 + TH, RYN, RYN + TH, 0, H, 'wall'); box(HX0, HX1, RYN, RYN + TH, HZ, H, 'wall')
box(HX0 - .2, HX0, RYN + TH, -3.085, 0, 1.84, 'gapc'); box(HX1, HX1 + .2, RYN + TH, -3.085, 0, 1.84, 'gapc'); box(HX0 - .2, HX1 + .2, RYN + TH, -3.085, 1.84, H, 'gapc')
box(HX0, HX1, RYN - .01, -3.085, -.1, .003, 'gapc')
for a in ((HX0 - .05, HX0), (HX1, HX1 + .05)): box(a[0], a[1], RYN - .015, RYN, 0, HZ, 'skirt')
box(HX0 - .05, HX1 + .05, RYN - .015, RYN, HZ, HZ + .05, 'skirt')
face([(HX1, RYN - .02, 0), (HX0, RYN - .02, 0), (HX0, RYN - .02, HZ), (HX1, RYN - .02, HZ)][::-1] if False else [(HX0, RYN + .1, 0), (HX0, RYN + .1, HZ), (HX1, RYN + .1, HZ), (HX1, RYN + .1, 0)], 'plug', uvs=[(0, 0)] * 4)  # 굽는 동안만 막음
# 남쪽 벽 + 창 구멍
box(RX0 - TH, WX0, RYS - TH, RYS, 0, H, 'wall'); box(WX1, RX1 + TH, RYS - TH, RYS, 0, H, 'wall')
box(WX0, WX1, RYS - TH, RYS, WZ1, H, 'wall'); box(WX0, WX1, RYS - TH, RYS, 0, WZ0, 'wall')
# 창틀
f = .05
yf0, yf1 = RYS - .12, RYS - .04
box(WX0, WX1, yf0, yf1, WZ0, WZ0 + f, 'wf'); box(WX0, WX1, yf0, yf1, WZ1 - f, WZ1, 'wf')
box(WX0, WX0 + f, yf0, yf1, WZ0, WZ1, 'wf'); box(WX1 - f, WX1, yf0, yf1, WZ0, WZ1, 'wf')
mid = (WX0 + WX1) / 2 + .02
box(mid - .035, mid + .035, yf0 - .03, yf1, WZ0, WZ1, 'wf'); box(WX0, mid, yf0, yf1, .6, .64, 'wf')
box(WX0 - .08, WX1 + .08, RYS - .04, RYS + .02, WZ1, WZ1 + .08, 'skirt')
# 굽도리
for a in ((RX0, RX0 + .012, RYS, RYN), (RX1 - .012, RX1, RYS, RYN)): box(a[0], a[1], a[2], a[3], 0, .07, 'skirt')
box(RX0, WX0, RYS, RYS + .012, 0, .07, 'skirt'); box(WX1, RX1, RYS, RYS + .012, 0, .07, 'skirt')
box(RX0, HX0 - .05, RYN - .012, RYN, 0, .07, 'skirt'); box(HX1 + .05, RX1, RYN - .012, RYN, 0, .07, 'skirt')
# 연한 블라인드: 창 전체. 뒤 풍경이 희미하게 비침
face([(WX1 + .02, RYS + .05, WZ0 - .02), (WX0 - .02, RYS + .05, WZ0 - .02), (WX0 - .02, RYS + .05, WZ1 + .02), (WX1 + .02, RYS + .05, WZ1 + .02)], 'blinds', uvs=[(0, 0), (1, 0), (1, 4), (0, 4)])
box(WX0 - .05, WX1 + .05, RYS + .03, RYS + .07, WZ1 + .02, WZ1 + .07, 'whitem')
# 커튼·봉·벽걸이 에어컨 (11번)
def curtain(x0, x1, mat='curtain', y0=RYS + .1, folds=7, amp=.035, z0=.02, z1=2.18):
    n = folds * 6
    prev = None
    for i in range(n + 1):
        x = x0 + (x1 - x0) * i / n; y = y0 + amp * math.sin(i / n * folds * 2 * math.pi)
        if prev:
            u0, u1 = (i - 1) / n * .9, i / n * .9
            face([(x, y, z0), (prev[0], prev[1], z0), (prev[0], prev[1], z1), (x, y, z1)], mat, uvs=[(u1, 0), (u0, 0), (u0, 1), (u1, 1)], smooth=True)
        prev = (x, y)
curtain(7.28, 7.92); curtain(9.0, 9.5)
sweep([(7.18, RYS + .1, 2.21), (9.56, RYS + .1, 2.21)], .013, 'rod', 8)
box(9.56, RX1, RYS, RYS + .22, 2.02, 2.32, 'whitem'); box(9.6, RX1 - .02, RYS + .215, RYS + .222, 2.03, 2.07, 'wf')
sweep(smooth_path([(9.8, RYS + .05, 2.02), (9.82, RYS + .05, 1.8), (9.9, RYS + .05, 1.6)], 4), .018, 'whitem', 8)
# 책상: 동쪽 벽. 남쪽 끝에 검은 매트 (9번)
DZ = .74; DX0, DY0, DY1 = 9.5, -7.1, -5.55
box(DX0, RX1, DY0, DY1, DZ - .03, DZ, 'dwhite')
face([(DX0 + .002, DY0 + .01, DZ + .001), (RX1 - .05, DY0 + .01, DZ + .001), (RX1 - .05, -6.45, DZ + .001), (DX0 + .002, -6.45, DZ + .001)], 'mat', uvs=[(0, 0)] * 4)
for y in (DY0 + .1, DY1 - .1):
    box(9.62, 10.1, y - .03, y + .03, 0, .03, 'whitem'); box(9.82, 9.9, y - .04, y + .04, 0, DZ - .03, 'whitem')
box(9.84, 9.88, DY0 + .1, DY1 - .1, DZ - .1, DZ - .03, 'whitem')
colliders.append([DX0, DY0, RX1, DY1])
box(9.6, 10.12, -7.05, -6.68, 0, .46, 'pc')
face([(9.599, -6.68, .03), (9.599, -6.68, .44), (9.599, -7.05, .44), (9.599, -7.05, .03)][::-1] if False else [(9.599, -6.68, .03), (9.599, -7.05, .03), (9.599, -7.05, .44), (9.599, -6.68, .44)], 'bezel', uvs=[(0, 0)] * 4)
# 모니터 둘 (LG: 검은 받침 / 오른쪽 위, 흰 턱 모니터: 왼쪽 앞)
def monitor(x, y, rot, w, h, zc, chin):
    T = place(x, y, rot)
    d = .022
    box(0, d, -w / 2, w / 2, zc - h / 2, zc + h / 2, 'bezel', T=T)
    b = .006
    face([T((-.001, w / 2 - b, zc - h / 2 + b * 3)), T((-.001, -w / 2 + b, zc - h / 2 + b * 3)), T((-.001, -w / 2 + b, zc + h / 2 - b)), T((-.001, w / 2 - b, zc + h / 2 - b))], 'screen', uvs=[(0, 0)] * 4)
    if chin: box(-.001, d, -w / 2, w / 2, zc - h / 2 - .022, zc - h / 2 + .012, 'whitem', T=T)
    box(.03, .06, -.03, .03, DZ, zc, chin and 'whitem' or 'bezel', T=T)
    box(-.05, .13, -.12, .12, DZ, DZ + .012, chin and 'whitem' or 'bezel', T=T)
monitor(9.98, -6.55, .05, .72, .41, 1.2, False)
monitor(9.95, -5.88, .26, .69, .39, 1.06, True)   # 왼쪽: 앉은 자리 쪽으로 살짝
# 키보드·마우스
kx0, kx1, ky0, ky1 = 9.58, 9.73, -6.63, -6.2; kz = DZ + .018
box(kx0, kx1, ky0, ky1, DZ, kz, 'kb')
face([(kx0, ky0, kz + .001), (kx1, ky0, kz + .001), (kx1, ky1, kz + .001), (kx0, ky1, kz + .001)], 'keys', uvs=[(1, 0), (1, 1), (0, 1), (0, 0)])
extrude_x([(-6.76 + .033 * math.cos(a / 8 * math.pi), DZ + .002 + .036 * math.sin(a / 8 * math.pi)) for a in range(8, -1, -1)], 9.58, 9.69, 'mouse', us=.2)
# 의자: 그물 등판, 다섯 발 (11번, 옷 없이)
cx, cy = 8.98, -6.38
for a in range(5):
    t = a / 5 * 6.283 + .3
    sweep([(cx, cy, .1), (cx + .29 * math.cos(t), cy + .29 * math.sin(t), .07)], .018, 'rod', 6)
    sweep([(cx + .29 * math.cos(t), cy + .29 * math.sin(t), .04), (cx + .29 * math.cos(t), cy + .29 * math.sin(t), .0)], .025, 'rod', 8)
sweep([(cx, cy, .1), (cx, cy, .44)], .022, 'chrome', 8)
sweep([(cx, cy, .44), (cx, cy, .5)], .25, 'mesh', 20)
T = place(cx, cy, 0)
extrude_x([(y_, z_) for y_, z_ in ((-.2, .56), (-.17, .95), (-.1, 1.06), (.1, 1.06), (.17, .95), (.2, .56))], -.27, -.245, 'mesh', T=T, us=.3)
for s_ in (-1, 1):
    sweep(smooth_path([(-.2, s_ * .25, .52), (-.18, s_ * .28, .68), (.0, s_ * .28, .7), (.14, s_ * .26, .68)], 4), .014, 'rod', 7, T=T)
colliders.append([cx - .28, cy - .28, cx + .28, cy + .28])
# 침대: 비움. 낮은 틀 + 맨 매트리스
BX1, BY0, BY1 = 8.2, -7.05, -5.05
box(RX0, BX1, BY0, BY1, 0, .26, 'navy')
pr = [(BY0 + .03, .26), (BY0 + .0, .29), (BY0, .42), (BY0 + .03, .45), (BY1 - .03, .45), (BY1, .42), (BY1, .29), (BY1 - .03, .26)]
# x 방향으로 뽑는 단면 (y, z)
extrude_x(pr[::-1] if False else pr, RX0 + .01, BX1 - .01, 'mattress', us=.6)
colliders.append([RX0, BY0, BX1, BY1])
# 책장: 동쪽 벽 북쪽. 칸마다 사진 그대로, 위에서 1·2·3칸 (10번)
SY0, SY1, SX0 = -4.75, -3.95, 9.9
Z_ = (.12, .52, .92, 1.32, 1.78)
for z in Z_:
    box(SX0, RX1, SY0, SY1, z - .025, z, 'whitem')
    face([(SX0 + .001, SY0 + .005, z + .0005), (RX1 - .01, SY0 + .005, z + .0005), (RX1 - .01, SY1 - .005, z + .0005), (SX0 + .001, SY1 - .005, z + .0005)], 'peg', uvs=[(0, 0), (3, 0), (3, 8), (0, 8)])
for x, y in ((SX0, SY0), (SX0, SY1), (RX1 - .03, SY0), (RX1 - .03, SY1)): box(x - .012, x + .012, y - .012, y + .012, 0, 1.92, 'whitem')
for tier, z0, z1 in (('tier1', 1.32, 1.78), ('tier2', .92, 1.32), ('tier3', .52, .92)):
    x = 10.02
    face([(x, SY1, z0), (x, SY0, z0), (x, SY0, z1), (x, SY1, z1)], tier, uvs=[(0, 0), (1, 0), (1, 1), (0, 1)])
    # 사진 판 뒤·옆은 벽
for a, b in ((SY0, SY1),):
    sweep([(SX0, a, .12), (RX1 - .01, a, .9)], .004, 'whitem', 5); sweep([(SX0, b, .12), (RX1 - .01, b, .9)], .004, 'whitem', 5)
colliders.append([SX0 - .02, SY0 - .02, RX1, SY1 + .02])
# 문 쪽 흰 커튼 (10번 왼쪽)
def wcurtain():
    n = 30; x_ = RX1 - .05; prev = None
    for i in range(n + 1):
        y = -3.42 - .48 * i / n; x = x_ + .03 * math.sin(i / n * 5 * 6.283)
        if prev:
            face([(prev[0], prev[1], .02), (x, y, .02), (x, y, 2.18), (prev[0], prev[1], 2.18)], 'curtainw', uvs=[((i - 1) / n, 0), (i / n, 0), (i / n, 1), ((i - 1) / n, 1)], smooth=True)
        prev = (x, y)
wcurtain()
colliders += [[RX0 - 1, RYS - 1, RX0, RYN + 1], [RX1, RYS - 1, RX1 + 1, RYN + 1], [RX0 - 1, RYS - 1, RX1 + 1, RYS], [RX0 - 1, RYN, HX0, -3.05], [HX1, RYN, RX1 + 1, -3.05]]
finish(((RX0 + RX1) / 2, (RYN + RYS) / 2, 1.2), 7.0, {'colliders': [[round(v, 3) for v in c] for c in colliders], 'bounds': [RX0, RYS, RX1, RYN],
    'window': [WX0, WX1, RYS], 'door': [HX0, HX1], 'desk': {'x': 9.64, 'y': -5.88, 'z': DZ + .002}})
