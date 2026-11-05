"""강의실 사진 → 3D 질감. 좌표는 사진을 긴 변 2000px로 봤을 때 기준.
와이파이 표지판(3번 기둥, 7번 화이트보드 오른쪽 위)과 사람(4번 문 창)은 절대 잘라 쓰지 않는다."""
import cv2, numpy as np, os, sys
PHOTOS, OUT = sys.argv[1], sys.argv[2]
rng = np.random.default_rng(30)
imgs = {}
def photo(i):
    if i not in imgs:
        im = cv2.imread(f"{PHOTOS}/{i}.jpg"); imgs[i] = (im, im.shape[1] / (2000 if im.shape[1] > im.shape[0] else 1500))
    return imgs[i]
def rect(i, quad, w, h):
    im, k = photo(i)
    M = cv2.getPerspectiveTransform(np.float32(quad) * k, np.float32([[0, 0], [w, 0], [w, h], [0, h]]))
    return cv2.warpPerspective(im, M, (w, h), flags=cv2.INTER_AREA)
def crop(i, x0, y0, x1, y1, w=None, h=None):
    return rect(i, [[x0, y0], [x1, y0], [x1, y1], [x0, y1]], w or int(x1 - x0), h or int(y1 - y0))
def save(n, im, q=88): cv2.imwrite(f"{OUT}/{n}.jpg", np.clip(im, 0, 255).astype(np.uint8), [cv2.IMWRITE_JPEG_QUALITY, q])
def flatten(im, sigma, keep=.25):
    """사진에 찍힌 조명 차이를 지움 (빛은 Blender가 다시 계산). keep만큼 얼룩 남김"""
    f = im.astype(np.float32) + 1
    low = cv2.GaussianBlur(f, (0, 0), sigma)
    return f / low * (low.mean((0, 1)) * (1 - keep) + low * keep)
def seam(im, frac=.04):
    """가장자리를 반대편과 섞어 이음매 없앰"""
    h, w = im.shape[:2]; f = im.astype(np.float32); n = int(w * frac); m = int(h * frac)
    o = f.copy()
    for j in range(n):
        a = .5 * (1 - j / n); o[:, j] = f[:, j] * (1 - a) + f[:, -1 - j] * a; o[:, -1 - j] = f[:, -1 - j] * (1 - a) + f[:, j] * a
    f = o.copy()
    for j in range(m):
        a = .5 * (1 - j / m); o[j] = f[j] * (1 - a) + f[-1 - j] * a; o[-1 - j] = f[-1 - j] * (1 - a) + f[j] * a
    return o
def patches(srcs, W, H, size, n, tone=None):
    """사진 조각을 부드러운 가장자리로 무작위로 덮어 반복 없는 큰 판을 만듦"""
    out = np.zeros((H, W, 3), np.float32); wt = np.zeros((H, W, 1), np.float32)
    s = int(size); xx, yy = np.meshgrid(np.linspace(-1, 1, s), np.linspace(-1, 1, s))
    mask = np.clip(1.25 - np.maximum(abs(xx), abs(yy)) * 1.25, 0, 1)[..., None] ** 1 * 4
    for _ in range(n):
        src = srcs[rng.integers(len(srcs))]; h, w = src.shape[:2]
        k = s / min(h, w) * rng.uniform(1.02, 1.4)
        p = cv2.resize(src, None, fx=k, fy=k, interpolation=cv2.INTER_LINEAR)
        y = rng.integers(0, p.shape[0] - s + 1); x = rng.integers(0, p.shape[1] - s + 1); p = p[y:y + s, x:x + s]
        if rng.random() < .5: p = p[:, ::-1]
        if rng.random() < .5: p = p[::-1]
        X = rng.integers(-s // 2, W - s // 2); Y = rng.integers(-s // 2, H - s // 2)
        x0, y0, x1, y1 = max(X, 0), max(Y, 0), min(X + s, W), min(Y + s, H)
        m = mask[y0 - Y:y1 - Y, x0 - X:x1 - X]
        out[y0:y1, x0:x1] += p[y0 - Y:y1 - Y, x0 - X:x1 - X] * m; wt[y0:y1, x0:x1] += m
    return out / np.maximum(wt, 1e-3)

# ── 벽돌(3번): 줄눈이 맞는 3칸 × 8단 = 1.2m × 1.6m 한 판
b = rect(3, [[243, 200], [972, 168], [972, 1227], [318, 1175]], 960, 1280)
mask = np.zeros(b.shape[:2], np.uint8)
save("block", seam(flatten(b, 260, .55), .012), 84)

# ── 책상 윗면(1번): 긁힌 자국 + 얼룩
t = rect(1, [[468, 446], [1216, 516], [1490, 1772], [476, 1852]], 800, 1200)
save("table", flatten(t, 220, .35), 86)
t2 = rect(1, [[566, 6], [1098, 0], [1216, 440], [520, 372]], 800, 600)  # 얼룩진 곡선 책상
save("table2", flatten(t2, 200, .35), 86)

# ── 바닥: 사진의 색·얼룩 정도에 맞춰 그림 (사진 조각은 경계가 무늬로 남음). 교실 전체 한 장
noise = lambda sig: (lambda n: n / n.std())(cv2.GaussianBlur(rng.normal(0, 1, (2048, 2048)).astype(np.float32), (0, 0), sig))
low = sum(noise(sig) * amp for sig, amp in ((1.2, .22), (5, .25), (18, .4), (60, .7), (200, 1), (420, .9)))
low = (low - low.mean()) / low.std()
floor = np.array([136., 143., 146.], np.float32)[None, None] * (1 + .05 * low[..., None])
for _ in range(240):  # 끌린 자국·긁힘
    x, y = rng.integers(0, 2048, 2); a_ = rng.uniform(0, np.pi); L_ = rng.uniform(30, 260)
    layer = np.zeros((2048, 2048), np.float32); cv2.line(layer, (int(x), int(y)), (int(x + np.cos(a_) * L_), int(y + np.sin(a_) * L_)), 1, 1, cv2.LINE_AA)
    floor += cv2.GaussianBlur(layer, (0, 0), rng.uniform(.6, 1.8))[..., None] * rng.uniform(-30, 14)
save("floor", floor, 84)

# ── 크림색 벽·기둥(3번 기둥 와이파이 아래쪽만, 2번 오른쪽 벽)
w1 = crop(3, 1010, 540, 1590, 1450, 800, 1250)   # y≥540: 표지판(y≈390~495) 안 들어감
w2 = crop(2, 1240, 330, 1950, 880, 1000, 780)
w3 = crop(6, 150, 200, 1000, 720, 1200, 730)
ws = [flatten(x, 130, .6) for x in (w1, w2, w3)]
target = np.mean([x.mean((0, 1)) for x in ws], 0)
ws = [x * target / x.mean((0, 1)) for x in ws]
save("plaster", patches(ws, 2048, 1024, 420, 300), 80)

# ── 천장: 사진의 흰 텍스 + 어두운 짧은 틈. 1.2m 타일 (사진 조각은 경계가 보여서 직접 그림)
tile = np.full((1024, 1024, 3), (214., 219., 220.), np.float32)
gr = cv2.GaussianBlur(rng.normal(0, 1, (1024, 1024)).astype(np.float32), (0, 0), 1.2); tile += (gr / gr.std() * 3.5)[..., None]
L = np.zeros((1024, 1024), np.float32)
for _ in range(2600):
    x, y = rng.integers(0, 1024, 2); a = rng.uniform(0, np.pi); n = rng.uniform(3, 15)
    for ox in (-1024, 0, 1024):
        for oy in (-1024, 0, 1024):
            if 0 <= x + ox < 1024 and 0 <= y + oy < 1024 or True:
                cv2.line(L, (int(x + ox), int(y + oy)), (int(x + ox + np.cos(a) * n), int(y + oy + np.sin(a) * n)), float(rng.uniform(.35, 1)), 1 + int(rng.random() < .3), cv2.LINE_AA) if abs(ox) + abs(oy) == 0 or x < 20 or y < 20 or x > 1004 or y > 1004 else None
tile = tile * (1 - .62 * cv2.GaussianBlur(L, (0, 0), .7)[..., None])
for k in (0, 512): tile[k:k + 2] *= .86; tile[:, k:k + 2] *= .86  # 600mm 줄눈
save("ceiling", tile, 78)

# ── 합판 의자(4번 좌판): 결이 보이는 진한 갈색, 미러 타일
w = rect(4, [[556, 1272], [730, 1243], [742, 1296], [596, 1340]], 640, 320)
g = cv2.cvtColor(w, cv2.COLOR_BGR2GRAY); dots = cv2.dilate((g > 120).astype(np.uint8), np.ones((9, 9), np.uint8))
w = cv2.inpaint(w, dots, 7, cv2.INPAINT_TELEA)
save("wood", cv2.resize(flatten(w, 90, .35), (512, 768), interpolation=cv2.INTER_CUBIC), 86)

# ── 커튼(블라인드): 5번
save("blind", flatten(crop(5, 880, 512, 985, 588, 512, 372), 80, .4), 85)
# ── 창밖: 5번 위쪽 창 판을 이어 붙임(창틀 가로대는 메꿈) — 건물 밖 큰 판에 걸어 시차가 생기게
panes = [crop(5, 884, 600, 978, 716, 470, 620), crop(5, 1004, 600, 1092, 716, 440, 620),
         crop(5, 1340, 578, 1432, 728, 460, 620), crop(5, 1458, 578, 1548, 728, 450, 620), crop(5, 1684, 594, 1766, 730, 410, 620)]
view = np.hstack([panes[4][:, ::-1], panes[0], panes[1], panes[2], panes[3], panes[4]])
# 위로는 하늘, 아래로는 나무를 이어 판을 세로로 늘림 (창 가까이 가서 위아래를 봐도 끊기지 않게)
sky = cv2.GaussianBlur(cv2.resize(view[:8], (view.shape[1], 300)), (0, 0), 30)
save("outside", np.vstack([sky, view, view[::-1][:300]]), 84)
# ── 작은 것들
save("door_glass", crop(2, 2, 548, 400, 648, 800, 200), 85)
save("switches", crop(2, 548, 712, 692, 802, 432, 270), 88)
save("exit", rect(4, [[1036, 195], [1062.5, 183.6], [1063, 236], [1036, 247]], 120, 240), 90)
print("textures ok", sorted(os.listdir(OUT)))
