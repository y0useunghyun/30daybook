"""내 방 질감: 사진(9·10·11번) → 벽지·커튼·책장 칸·포스터·창밖. 빨래·옷·잡동사니가 찍힌 곳은 안 씀. 사용: make_room_textures.py <사진폴더> <출력>"""
import cv2, numpy as np, sys
from PIL import Image, ImageDraw
P, OUT = sys.argv[1], sys.argv[2]
rng = np.random.default_rng(11)
imgs = {}
def photo(i):
    if i not in imgs:
        im = cv2.imread(f'{P}/{i}.jpg'); imgs[i] = (im, im.shape[1] / 2000)
    return imgs[i]
def rect(i, q, w, h):
    im, k = photo(i)
    return cv2.warpPerspective(im, cv2.getPerspectiveTransform(np.float32(q) * k, np.float32([[0, 0], [w, 0], [w, h], [0, h]])), (w, h), flags=cv2.INTER_AREA)
def save(n, im, q=86): cv2.imwrite(f'{OUT}/{n}.jpg', np.clip(im, 0, 255).astype(np.uint8), [cv2.IMWRITE_JPEG_QUALITY, q])
def flatten(im, sigma, keep=.3):
    f = im.astype(np.float32) + 1; low = cv2.GaussianBlur(f, (0, 0), sigma)
    return f / low * (low.mean((0, 1)) * (1 - keep) + low * keep)
noise = lambda sz, sig: (lambda n: n / n.std())(cv2.GaussianBlur(rng.normal(0, 1, sz).astype(np.float32), (0, 0), sig))
# 책장 칸: 사진 그대로 (위→아래)
save('tier1', rect(10, [[178, 36], [1070, 30], [1042, 462], [282, 486]], 1200, 600), 88)
save('tier2', rect(10, [[286, 492], [1040, 468], [1030, 772], [358, 852]], 1200, 500), 88)
t3 = rect(10, [[362, 862], [1030, 792], [1020, 1020], [420, 1040]], 1200, 400)
t3[318:, :210] = (205, 208, 208)  # 앞에 걸친 의자 천 가림
save('tier3', t3, 88)
# 커튼: 줄무늬
save('curtain', flatten(rect(9, [[1700, 60], [1960, 60], [1990, 660], [1640, 660]], 512, 900), 200, .4), 86)
save('curtain_w', flatten(rect(10, [[20, 120], [200, 120], [215, 860], [40, 860]], 300, 900), 200, .4), 82)
# 창밖: 빨래 없는 왼쪽 판 + 오른쪽 건물
a = rect(11, [[692, 500], [944, 500], [944, 790], [692, 790]], 510, 580)
b = rect(11, [[1186, 540], [1378, 540], [1378, 770], [1186, 770]], 390, 580)
save('view', cv2.GaussianBlur(np.hstack([a, b]), (0, 0), 16), 80)  # 블라인드 뒤라 색만 필요. 사는 곳이 드러나지 않게 뭉갬
# 창 블라인드: 연한 가로 살
bl = np.full((512, 256, 3), (232, 240, 243), np.float32)
for y in range(0, 512, 16): bl[y:y + 2] *= .86; bl[y + 2:y + 5] *= 1.02
save('blind_soft', bl + (noise((512, 256), 1) * 1.5)[..., None], 86)
# 카펫: 13번 사진의 타일 카펫 + 50cm 줄눈
c = flatten(rect(13, [[1300, 1190], [1960, 1190], [1960, 1490], [1300, 1490]], 1024, 1024), 110, .1).astype(np.float32)
n_ = 90; o = c.copy()
for j in range(n_):  # 가장자리를 반대편과 섞어 이음매 없이
    a_ = .5 * (1 - j / n_); o[:, j] = c[:, j] * (1 - a_) + c[:, -1 - j] * a_; o[:, -1 - j] = c[:, -1 - j] * (1 - a_) + c[:, j] * a_
c = o.copy()
for j in range(n_):
    a_ = .5 * (1 - j / n_); o[j] = c[j] * (1 - a_) + c[-1 - j] * a_; o[-1 - j] = c[-1 - j] * (1 - a_) + c[j] * a_
c = o
for k in (0, 512): c[k:k + 3] *= .72; c[:, k:k + 3] *= .72  # 50cm 카펫 줄눈
save('carpet', c, 82)
# 책장 선반: 흰 타공판
s = np.full((256, 256, 3), 238, np.uint8)
for y in range(16, 256, 32):
    for x in range(16 + (y // 32 % 2) * 16, 256, 32): cv2.circle(s, (x, y), 6, (70, 70, 70), -1, cv2.LINE_AA)
save('peg', s, 86)
# 키보드
im = Image.new('RGB', (1024, 320), (32, 33, 36)); d = ImageDraw.Draw(im)
rows = [(13, 0), (14, 0), (13, 24), (12, 34), (11, 54)]
for r, (n, off) in enumerate(rows):
    kw = (760 - off) / n
    for j in range(n):
        x = 24 + off + j * kw; d.rounded_rectangle((x + 3, 22 + r * 56, x + kw - 3, 22 + r * 56 + 48), 5, fill=(52, 53, 57))
d.rounded_rectangle((180, 22 + 5 * 56 - 2, 560, 22 + 5 * 56 + 16), 4, fill=(52, 53, 57))
for j in range(4):
    for r in range(5): d.rounded_rectangle((800 + j * 52, 22 + r * 56, 846 + j * 52, 70 + r * 56), 5, fill=(52, 53, 57))
save('keys', np.array(im)[..., ::-1], 86)
print('ok')
