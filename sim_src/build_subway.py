"""4호선 객차 안. blender -b -P build_subway.py -- <out> <lightmap_px> <samples>
교실과 같은 좌표계: 객차는 교실 남쪽 벽 바로 뒤. 긴 축 = x, 북쪽 문 2개가 교실 문과 맞닿음.
구성: 문 사이 7인석, 양 끝 3인 교통약자석, 좌석 위 선반, 손잡이, 광고 칸(실제 구성). 좌석 색은 추정."""
import bpy, bmesh, math, json, os, sys, random
import numpy as np
from mathutils import Vector
argv = sys.argv[sys.argv.index('--') + 1:]
OUT, LM_PX, SAMPLES = argv[0], int(argv[1]), int(argv[2])
TEX = os.path.join(os.path.dirname(os.path.abspath(sys.argv[sys.argv.index('-P') + 1])), 'tex_subway')
random.seed(4)
X0, X1, YN, YS = -2.35, 15.3, -.3, -3.05       # 안쪽 면
YC = (YN + YS) / 2
ZC, ZW = 2.14, 1.92                             # 천장 가운데, 벽이 굽기 시작하는 높이
DC = (-.125, 4.275, 8.675, 13.075)              # 문 중심 (교실 문 A=4.275, B=8.675)
DW, DH = .64, 1.84                              # 문 반폭, 높이
M = {
 'sfloor':  dict(map='sfloor', s=(1.6, 1.6), rough=.72, gain=1.35),
 'bluefloor': dict(color='#3f7fbe', rough=.5, gain=.62),
 'fw':      dict(color='#efefec', rough=.72, gain=1.0),
 'ceil':    dict(color='#f2f2ef', rough=.8, gain=1.75),
 'cpanel':  dict(color='#d9dadb', rough=.8, gain=2.0),
 'bluestripe': dict(color='#2d76b8', rough=.7, gain=2.0),
 'panel':   dict(color='#cfd0ce', rough=.4, gain=.72),
 'bellow':  dict(color='#74767a', rough=.85, gain=2.4),
 'bellow2': dict(color='#54565a', rough=.85, gain=2.4),
 'shell':   dict(color='#d6d7d4', rough=.8, unlit=True),
 'steel':   dict(color='#c6c8c9', rough=.36, metal=.25, gain=.85),
 'pole':    dict(color='#e8e9ea', rough=.14, metal=1),
 'rubber':  dict(color='#1c1d1f', rough=.75),
 'grey':    dict(color='#55585c', rough=.75),
 'seatw':   dict(color='#e6e6e3', rough=.32, gain=.62),
 'seatp':   dict(color='#efbfcd', rough=.32, gain=.62),
 'strap':   dict(color='#8b8e90', rough=.45),
 'ledc':    dict(color='#ffffff', rough=1, emit=7.0),
 'tunnel':  dict(color='#6f7276', rough=.05, unlit=True),   # 창밖: 움직이지 않는 회색 통로
 'gang':    dict(map='gang', rough=.1, unlit=True),
 'gangW':   dict(map='gang', rough=.1, unlit=True),
 'lcd':     dict(color='#101012', rough=.2, unlit=True),
 'extred':  dict(color='#b3201f', rough=.3),
 'route':   dict(map='route', rough=.5, gain=.75),
 'ads':     dict(map='ads', rough=.45, gain=.72),
 'priority':dict(map='priority', rough=.5),
 'caution': dict(map='caution', rough=.5),
 'sill':    dict(color='#cfd1d2', rough=.5),
 'alu':     dict(color='#a7aaad', rough=.35, metal=.9),
 **{f'leaf{k}': dict(color='#c6c8c9', rough=.36, metal=.25, gain=.85) for k in ('AL', 'AR', 'BL', 'BR', 'CL', 'CR')},
 **{f'glass{k}': dict(color='#6f7276', rough=.1, unlit=True) for k in ('AL', 'AR', 'BL', 'BR', 'CL', 'CR')},
}
exec(open(os.path.join(os.path.dirname(TEX), 'kit.py')).read())
colliders = []
def wquad(x0, x1, z0, z1, mat, north, uvs=None):
    """벽면 사각형. 안쪽(객차 쪽)을 봄"""
    y = YN if north else YS
    p = [(x1, y, z0), (x0, y, z0), (x0, y, z1), (x1, y, z1)] if not north else [(x0, y, z0), (x1, y, z0), (x1, y, z1), (x0, y, z1)]
    if not north: uvs = uvs
    face(p, mat, uvs=uvs or [(0, 0), (1, 0), (1, 1), (0, 1)])
# 바닥·천장 곡선: 벽 윗선→가운데
box(X0 - .1, X1 + .1, YS - .1, YN + .02, -.1, 0, 'sfloor')
face([(X0, YC - .5, .002), (X1, YC - .5, .002), (X1, YC + .5, .002), (X0, YC + .5, .002)], 'bluefloor')
def arc(north):
    y = YN if north else YS; s = -1 if north else 1
    prof = [(y, ZW), (y + s * .06, ZW + .08), (y + s * .18, ZW + .15), (y + s * .38, ZC - .02), (y + s * .62, ZC)]
    for a, b in zip(prof, prof[1:]):
        pts = [(X0, a[0], a[1]), (X1, a[0], a[1]), (X1, b[0], b[1]), (X0, b[0], b[1])]
        face(pts if north else pts[::-1], 'ceil', uvs=[(0, 0), (1, 0), (1, 1), (0, 1)], smooth=True)
    return prof
pn = arc(True); ps = arc(False)
face([(X0, pn[-1][0], ZC), (X0, ps[-1][0], ZC), (X1, ps[-1][0], ZC), (X1, pn[-1][0], ZC)][::-1], 'ceil')
# 벽: 문 칸 / 창 칸
TUNNEL_TILE = 8.0
def round_corners(x0, x1, z0, z1, r, y, mat, facing_south):
    # 사각 창 위에 모서리 조각을 덮어 둥글게
    for cx, cz, sx, sz in ((x0, z0, 1, 1), (x1, z0, -1, 1), (x1, z1, -1, -1), (x0, z1, 1, -1)):
        pts = [(cx, y, cz)] + [(cx + sx * r * (1 - math.sin(a / 6 * math.pi / 2)), y, cz + sz * r * (1 - math.cos(a / 6 * math.pi / 2))) for a in range(7)]
        n = (Vector(pts[1]) - Vector(pts[0])).cross(Vector(pts[2]) - Vector(pts[0]))
        if (n.y < 0) != facing_south: pts = pts[::-1]
        face(pts, mat, uvs=[(0, 0)] * len(pts))
def window(x0, x1, north, z0=.9, z1=1.66):
    y = YN if north else YS; o = .012 if north else -.012
    tun = lambda x: x / TUNNEL_TILE
    p = [(x0, y + o, z0), (x1, y + o, z0), (x1, y + o, z1), (x0, y + o, z1)]
    if north: face(p, 'tunnel', uvs=[(tun(x0), 0), (tun(x1), 0), (tun(x1), 1), (tun(x0), 1)])
    else: face(p[::-1], 'tunnel', uvs=[(tun(x0), 1), (tun(x1), 1), (tun(x1), 0), (tun(x0), 0)])
    round_corners(x0, x1, z0, z1, .09, y + o * .4, 'fw', north)
def wall_section(x0, x1, nwin, north):
    """x0~x1 벽 + 창 nwin개"""
    gap = .16; w = (x1 - x0 - gap * (nwin + 1)) / nwin
    wquad(x0, x1, 0, .9, 'fw', north); wquad(x0, x1, 1.66, ZW, 'fw', north)
    x = x0 + gap; last = x0
    for _ in range(nwin):
        wquad(last, x, .9, 1.66, 'fw', north)
        window(x, x + w, north)
        last = x + w; x += w + gap
    wquad(last, x1, .9, 1.66, 'fw', north)
for north in (True, False):
    edges = [X0] + [v for c in DC for v in (c - DW - .06, c + DW + .06)] + [X1]
    for i in range(0, len(edges), 2):
        wall_section(edges[i], edges[i + 1], 1 if i in (0, len(edges) - 2) else 2, north)
# 문: 틀 + 문짝 2장. 교실과 맞닿은 북쪽 두 곳은 재질을 따로 둬 웹에서 밀어 엶
def door_at(c, north, key=None):
    y = YN if north else YS; d = .03 if north else -.03
    lo, hi = min(y, y + d * 2), max(y, y + d * 2)
    for a in ((c - DW - .06, c - DW), (c + DW, c + DW + .06)):
        wquad(a[0], a[1], 0, ZW, 'fw', north)
    wquad(c - DW, c + DW, DH, ZW, 'fw', north)
    box(c - DW, c + DW, min(y, y + (.02 if north else -.02)), max(y, y + (.02 if north else -.02)), -.001, .006, 'sill')
    ly0, ly1 = (y + .018, y + .032) if north else (y - .032, y - .018)  # 창 판(.012)보다 뒤: 밀려 들어가면 가려짐
    for side, name in ((-1, 'L'), (1, 'R')):
        mat = f'leaf{key}{name}' if key else 'steel'; gl = f'glass{key}{name}' if key else 'tunnel'
        lx0, lx1 = (c - DW, c - .004) if side < 0 else (c + .004, c + DW)
        wx0, wx1, wz0, wz1 = lx0 + .14, lx1 - .14, .92, 1.66
        for a in ((lx0, lx1, 0, wz0), (lx0, lx1, wz1, DH), (lx0, wx0, wz0, wz1), (wx1, lx1, wz0, wz1)):
            box(a[0], a[1], ly0, ly1, a[2], a[3], mat)
        fy = (ly0 - .001) if north else (ly1 + .001)
        pts = [(wx0, fy, wz0), (wx1, fy, wz0), (wx1, fy, wz1), (wx0, fy, wz1)]
        uvs = [(wx0 / TUNNEL_TILE, 0), (wx1 / TUNNEL_TILE, 0), (wx1 / TUNNEL_TILE, 1), (wx0 / TUNNEL_TILE, 1)] if not key else [(0, 0)] * 4
        face(pts if north else pts[::-1], gl, uvs=uvs if north else uvs[::-1])
        round_corners(wx0, wx1, wz0, wz1, .07, fy + (-.0006 if north else .0006), mat, north)
        # 기대지 마세요 스티커
        cx = (lx0 + lx1) / 2; zz = 1.0 if False else .72
        cfy = (ly0 - .002) if north else (ly1 + .002)
        s = .085
        stp = [(cx - s, cfy, zz - s), (cx + s, cfy, zz - s), (cx + s, cfy, zz + s), (cx - s, cfy, zz + s)]
        cm = f'leaf{key}{name}' if False else 'caution'
        if not key: face(stp if north else stp[::-1], cm, uvs=[(0, 0), (1, 0), (1, 1), (0, 1)] if north else [(1, 1), (0, 1), (0, 0), (1, 0)])
    # 위 전광판 자리
    py = y + (-.004 if north else .004)
    w = .42; zz0, zz1 = 1.87 - .02, 1.915
    # 전광판: 문 위 벽에서 살짝 나옴
    box(c - w, c + w, min(y, y + (-.05 if north else .05)), max(y, y + (-.05 if north else .05)), zz0 - .008, zz1 + .008, 'rubber')
    fy = y + (-.051 if north else .051)
    pts = [(c - w + .01, fy, zz0), (c + w - .01, fy, zz0), (c + w - .01, fy, zz1), (c - w + .01, fy, zz1)]
    face(pts if north else pts[::-1], 'lcd', uvs=[(0, 0), (1, 0), (1, 1), (0, 1)] if north else [(1, 1), (0, 1), (0, 0), (1, 0)])
for c in DC:
    door_at(c, True, 'A' if c == 4.275 else 'B' if c == 8.675 else None)
    door_at(c, False, 'C' if c == 8.675 else None)   # 교실 B문 맞은편 = 내 방으로
# 교실 문 구멍 둘레를 덮는 차체 (교실 쪽에서 보이는 부분)
for c in (4.275, 8.675):
    box(c - DW - .1, c - .475, -.27, -.25, 0, 2.3, 'shell'); box(c + .475, c + DW + .1, -.27, -.25, 0, 2.3, 'shell')
    box(c - DW - .1, c + DW + .1, -.295, -.25, DH, 2.3, 'shell')
# 양 끝 벽 + 연결 문
for x, s in ((X0, 1), (X1, -1)):
    pts = lambda a, b, z0, z1: [(x, a, z0), (x, b, z0), (x, b, z1), (x, a, z1)]
    wide = (YC - .5, YC + .5)
    for a, b in ((YS, wide[0]), (wide[1], YN)):
        p = pts(a, b, 0, ZC + .01); face(p if s > 0 else p[::-1], 'fw')
    p = pts(*wide, 1.9, ZC + .01); face(p if s > 0 else p[::-1], 'fw')
    if s > 0:  # 맨 뒤 칸에서만 보일 막음 그림(웹에서 칸별로 켜고 끔). 그 외엔 앞 칸으로 뚫림
        gx = x + s * .002
        gp = [(gx, wide[0], 0), (gx, wide[1], 0), (gx, wide[1], 1.9), (gx, wide[0], 1.9)]
        face(gp, 'gangW', uvs=[(0, 0), (1, 0), (1, 1), (0, 1)])
    for yy in wide:
        box(*sorted((x, x + s * .05)), yy - .03, yy + .03, 0, 1.93, 'steel')
    box(*sorted((x, x + s * .05)), wide[0] - .03, wide[1] + .03, 1.9, 1.96, 'steel')
    bx = x + s * .06
    pp = [(bx, YC - .28, 1.97), (bx, YC + .28, 1.97), (bx, YC + .28, 2.07), (bx, YC - .28, 2.07)]
    box(*sorted((x, x + s * .05)), YC - .3, YC + .3, 1.96, 2.08, 'rubber')
    face(pp if s > 0 else pp[::-1], 'lcd', uvs=[(0, 0), (1, 0), (1, 1), (0, 1)] if s > 0 else [(1, 1), (0, 1), (0, 0), (1, 0)])
    sweep([(x + s * .09, wide[0] - .22, 0), (x + s * .09, wide[0] - .22, .52)], .07, 'extred', 14)
    if s > 0: colliders += [[x - .02, YS - 1, x, wide[0]], [x - .02, wide[1], x, YN + 1]]
# 연결 통로: 주름 벽 + 철판 바닥. 눈높이에 종이를 붙임(웹). 끝은 다음 칸
VL, VW = 1.05, .5                                # 길이, 반폭
VX1 = X1 + VL
box(X1 - .02, VX1 + .05, YC - VW - .1, YC + VW + .1, -.1, 0, 'alu')
for k, yw in ((1, YC + VW), (-1, YC - VW)):
    p = [(X1, yw, 0), (VX1, yw, 0), (VX1, yw, 1.96), (X1, yw, 1.96)]
    face(p if k > 0 else p[::-1], 'bellow', uvs=[(0, 0)] * 4)
    for j in range(15):                          # 주름
        rx = X1 + .03 + j * VL / 15
        box(rx, rx + .028, *sorted((yw, yw - k * .022)), 0, 1.96, 'bellow2')
face([(VX1, YC - VW, 1.96), (X1, YC - VW, 1.96), (X1, YC + VW, 1.96), (VX1, YC + VW, 1.96)], 'bellow')
face([(X1 + .8, YC - .08, 1.955), (X1 + .25, YC - .08, 1.955), (X1 + .25, YC + .08, 1.955), (X1 + .8, YC + .08, 1.955)], 'ledc')
gp = [(VX1, YC + VW, 0), (VX1, YC - VW, 0), (VX1, YC - VW, 1.96), (VX1, YC + VW, 1.96)]
face(gp, 'gang', uvs=[(0, 0), (1, 0), (1, 1), (0, 1)])
colliders += [[X1, YS - 1, VX1, YC - VW], [X1, YC + VW, VX1, YN + 1]]
# 좌석
SEAT_Z, DEPTH = .43, .47
# 등받이~앉는 면을 한 판으로 (벽에서 나온 거리, 앉는 면 기준 높이)
PL = [(.015, .5), (.05, .515), (.08, .48), (.095, .12), (.125, .07), (.43, .055), (.47, .035), (.474, .0), (.44, -.022), (.1, -.025), (.015, .02)]
def seats(xa, xb, n, north, mat):
    s = -1 if north else 1; y = YN if north else YS
    w = (xb - xa) / n
    for i in range(n):
        x0 = xa + i * w + .001; x1 = xa + (i + 1) * w - .001
        extrude_x([(y + s * a, SEAT_Z + b) for a, b in (PL[::-1] if north else PL)], x0, x1, mat)
    box(xa, xb, *sorted((y, y + s * .4)), .17, SEAT_Z - .01, 'fw')       # 좌석 아래: 흰 판
    box(xa, xb, *sorted((y, y + s * .385)), .0, .17, 'steel')            # 그 아래: 타공 철판
    for x in (xa, xb):
        box(x - .012, x + .012, *sorted((y, y + s * .5)), .12, 1.08, 'panel')   # 칸막이
        ring = [(x + (.014 if x == xb else -.014), y + s * (.25 + .085 * math.cos(a / 16 * 6.283)), .68 + .085 * math.sin(a / 16 * 6.283)) for a in range(17)]
        sweep(ring, .012, 'steel', 6, cap=False)
        # 바닥에서 올라와 선반으로 휘어 들어가는 큰 봉
        path = smooth_path([(x, y + s * .63, 0), (x, y + s * .63, .4), (x, y + s * .62, 1.05), (x, y + s * .54, 1.5), (x, y + s * .34, 1.8), (x, y + s * .08, 1.9)], 8)
        sweep(path, .017, 'pole', 10)
        sweep([(x, y + s * .02, 1.1), (x, y + s * .625, 1.1)], .013, 'pole', 8)     # 가로 봉
        arm = smooth_path([(x, y + s * .05, .72), (x, y + s * .3, .72), (x, y + s * .45, .66), (x, y + s * .49, .54)], 5)
        sweep(arm, .012, 'pole', 8)
        colliders.append([x - .07, min(y + s * .5, y + s * .68), x + .07, max(y + s * .5, y + s * .68)])
    colliders.append([xa, min(y, y + s * .5), xb, max(y, y + s * .5)])
    # 선반: 은색 봉을 촘촘히
    for j in range(9):
        k = .03 + j * .04
        sweep([(xa + .02, y + s * k, 1.77 + .004 * j), (xb - .02, y + s * k, 1.77 + .004 * j)], .005, 'pole', 5)
    # 손잡이: 삼각형
    ry = y + s * .74; rz = 1.98
    sweep([(xa, ry, rz), (xb, ry, rz)], .012, 'pole', 8)
    for rx in (xa + .02, xb - .02): sweep([(rx, ry, rz), (rx, ry, ZC)], .012, 'pole', 8)
    cnt = max(3, int((xb - xa) / .3))
    for j in range(cnt):
        hx = xa + (xb - xa) * (j + .5) / cnt
        box(hx - .014, hx + .014, ry - .004, ry + .004, 1.8, rz, 'strap')
        tri = [(hx, ry, 1.8), (hx + .05, ry, 1.68), (hx + .056, ry, 1.655), (hx + .03, ry, 1.645), (hx - .03, ry, 1.645), (hx - .056, ry, 1.655), (hx - .05, ry, 1.68), (hx, ry, 1.8)]
        sweep(tri, .009, 'strap', 6, cap=False)
    # 광고 칸 (벽 곡선 부분): 이 책의 지면들. 칸마다 듬성듬성
    cards = max(1, int((xb - xa) / 1.05))
    for j in range(cards):
        c0 = xa + (xb - xa) * (j + .5) / cards
        ax0, ax1 = c0 - .3, c0 + .3
        k = random.randrange(8); u0, v0 = (k % 4) / 4, 1 - (k // 4 + 1) / 2; u1, v1 = u0 + .25, v0 + .5
        y0, z0 = y + s * .006, ZW - .16; y1, z1 = y + s * .13, ZW + .13
        pts = [(ax0, y0, z0), (ax1, y0, z0), (ax1, y1, z1), (ax0, y1, z1)]
        face(pts if north else pts[::-1], 'ads', uvs=[(u0, v0), (u1, v0), (u1, v1), (u0, v1)] if north else [(u1, v1), (u0, v1), (u0, v0), (u1, v0)])
    if mat == 'seatp':
        mx = (xa + xb) / 2; py = y + s * .004; pts = [(mx - .2, py, 1.7), (mx + .2, py, 1.7), (mx + .2, py, 1.8), (mx - .2, py, 1.8)]
        face(pts if north else pts[::-1], 'priority', uvs=[(0, 0), (1, 0), (1, 1), (0, 1)] if north else [(1, 1), (0, 1), (0, 0), (1, 0)])
ranges = [(X0 + .03, DC[0] - DW - .08, 3, 'seatp')] + [(DC[i] + DW + .08, DC[i + 1] - DW - .08, 7, 'seatw') for i in range(3)] + [(DC[3] + DW + .08, X1 - .03, 3, 'seatp')]
for north in (True, False):
    for a, b, n, mat in ranges: seats(a, b, n, north, mat)
# 문 위 노선도: 천장 곡선면에
for c in DC:
    for north in (True, False):
        y = YN if north else YS; s = -1 if north else 1
        y0, z0 = y + s * .02, ZW + .02; y1, z1 = y + s * .16, ZW + .14
        w = .62
        pts = [(c - w, y0, z0), (c + w, y0, z0), (c + w, y1, z1), (c - w, y1, z1)]
        face(pts if north else pts[::-1], 'route', uvs=[(0, 0), (1, 0), (1, 1), (0, 1)] if north else [(1, 1), (0, 1), (0, 0), (1, 0)])
# 천장: 가운데 판 양옆으로 파란 줄, 그 바깥으로 LED 줄
Z_ = ZC - .002
face([(X1, YC + .38, Z_), (X1, YC - .38, Z_), (X0, YC - .38, Z_), (X0, YC + .38, Z_)], 'cpanel')
for k in (-1, 1):
    y0, y1 = sorted((YC + k * .38, YC + k * .45))
    face([(X1, y1, Z_), (X1, y0, Z_), (X0, y0, Z_), (X0, y1, Z_)], 'bluestripe')
    y0, y1 = sorted((YC + k * .47, YC + k * .55))
    face([(X1, y1, Z_ - .003), (X1, y0, Z_ - .003), (X0, y0, Z_ - .003), (X0, y1, Z_ - .003)], 'ledc')
for k in range(9):
    x = X0 + 1 + k * 1.98
    box(x - .2, x + .2, YC - .17, YC + .17, ZC - .012, ZC - .002, 'fw')
    for j in range(-5, 6): box(x - .18, x + .18, YC + j * .027 - .009, YC + j * .027 + .009, ZC - .016, ZC - .012, 'rubber')
    if k % 3 == 1: sweep([(x + .9, YC, ZC - .002), (x + .9, YC, ZC - .05)], lambda i: .05, 'fw', 14)
colliders += [[X0, YS - .3, 8.2, YS], [9.15, YS - .3, X1, YS], [X0, YN, 3.8, YN + .05], [4.75, YN, 8.2, YN + .05], [9.15, YN, X1, YN + .05]]
finish((6.5, YC, 1.3), 0.0, {'colliders': [[round(v, 3) for v in c] for c in colliders], 'tunnelTile': TUNNEL_TILE, 'gangway': {'x0': X1, 'x1': VX1, 'yc': YC, 'halfW': VW}, 'carPitch': round(VX1 - X0, 3), 'southDoor': {'x0': 8.2, 'x1': 9.15}, 'carX0': X0, 'carYN': YN, 'carYS': YS})
