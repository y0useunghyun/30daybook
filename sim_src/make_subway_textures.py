"""4호선 객차 질감: 전부 직접 그림. 광고 자리엔 이 작업의 지면을 넣음. 사용: make_subway_textures.py <pages폴더> <출력폴더>"""
import cv2, numpy as np, sys, glob
from PIL import Image, ImageDraw, ImageFont
PAGES, OUT = sys.argv[1], sys.argv[2]
rng = np.random.default_rng(4)
FONT = '/System/Library/Fonts/AppleSDGothicNeo.ttc'
font = lambda s, bold=True: ImageFont.truetype(FONT, s, index=6 if bold else 2)
LINE4 = (0, 165, 222)
def save(n, im, q=88):
    if isinstance(im, Image.Image): im.convert('RGB').save(f'{OUT}/{n}.jpg', quality=q)
    else: cv2.imwrite(f'{OUT}/{n}.jpg', np.clip(im, 0, 255).astype(np.uint8), [cv2.IMWRITE_JPEG_QUALITY, q])
noise = lambda sz, sig: (lambda n: n / n.std())(cv2.GaussianBlur(rng.normal(0, 1, sz).astype(np.float32), (0, 0), sig))
# 바닥: 무광 회색 시트 (BGR). 가운데 파란 띠는 지오메트리
f = np.array([138., 136., 134.], np.float32)[None, None] * (1 + .012 * noise((1024, 1024), 40)[..., None]) + (noise((1024, 1024), .9) * 2.5)[..., None]
save('sfloor', f, 84)
# 터널: 어두운 벽 + 케이블 + 조명 하나. 달리는 속도로 번짐. 8m 타일
T = np.full((256, 1536, 3), (128., 118., 66.), np.float32)
T += (cv2.GaussianBlur(rng.normal(0, 1, (256, 1536)).astype(np.float32), (121, 3), 0) * 20)[..., None]
for y, c in ((70, 8), (84, 10), (96, 6), (178, 12)): T[y:y + 3] *= .72; T[y + 3:y + 4] += c
g = np.zeros((256, 1536), np.float32); cv2.ellipse(g, (768, 52), (150, 10), 0, 0, 360, 1, -1, cv2.LINE_AA)
g = cv2.GaussianBlur(g, (0, 0), 14)
T += g[..., None] * np.array([170., 205., 225.], np.float32) * 1.3
save('tunnel', T, 82)
# 연결 통로 너머 다음 칸: 흰 벽 + 파란 띠가 멀어지는 그림
GW, GH = 512, 880; gang = np.full((GH, GW, 3), (232, 234, 234), np.uint8)
vx, vy = GW // 2, int(GH * .44)
cv2.fillPoly(gang, [np.array([[0, GH], [GW, GH], [vx + 26, vy + 24], [vx - 26, vy + 24]])], (150, 150, 148), cv2.LINE_AA)
cv2.fillPoly(gang, [np.array([[110, GH], [GW - 110, GH], [vx + 9, vy + 24], [vx - 9, vy + 24]])], (186, 124, 58), cv2.LINE_AA)
cv2.rectangle(gang, (vx - 26, vy - 24), (vx + 26, vy + 24), (205, 208, 208), -1)
save('gang', cv2.GaussianBlur(gang, (0, 0), 1.6), 84)
# 노선도
ST = '진접 오남 별내별가람 당고개 상계 노원 창동 쌍문 수유 미아 미아사거리 길음 성신여대입구 한성대입구 혜화 동대문 동대문역사문화공원 충무로 명동 회현 서울 숙대입구 삼각지 신용산 이촌 동작 총신대입구 사당 남태령 선바위 경마공원 대공원 과천 정부과천청사 인덕원 평촌 범계 금정 산본 수리산 대야미 반월 상록수 한대앞 중앙 고잔 초지 안산 신길온천 정왕 오이도'.split()
assert len(ST) == 51
W, H = 2600, 520
im = Image.new('RGB', (W, H), (248, 248, 245)); d = ImageDraw.Draw(im)
d.ellipse((24, 22, 96, 94), fill=LINE4); d.text((60, 58), '4', font=font(52), fill='white', anchor='mm')
d.text((112, 58), '수도권 전철 4호선', font=font(38), fill=(30, 30, 30), anchor='lm')
rows = [ST[:26], ST[26:][::-1]]
for r, (row, y) in enumerate(zip(rows, (205, 440))):
    x0, x1 = 90, W - 90
    d.line((x0, y, x1, y), fill=LINE4, width=14)
    for i, name in enumerate(row):
        x = x0 + (x1 - x0) * i / (len(row) - 1)
        d.ellipse((x - 13, y - 13, x + 13, y + 13), fill='white', outline=LINE4, width=5)
        t = Image.new('RGBA', (240, 44), (0, 0, 0, 0)); ImageDraw.Draw(t).text((2, 22), name, font=font(25, False), fill=(25, 25, 25), anchor='lm')
        t = t.rotate(52, expand=True, resample=Image.BICUBIC)
        im.paste(t, (int(x - 8), int(y - 24 - t.height)), t)
d.arc((W - 130, 205, W - 50, 440), -90, 90, fill=LINE4, width=14)
save('route', im, 90)
# 안내 스티커
im = Image.new('RGB', (512, 128), (232, 112, 150)); d = ImageDraw.Draw(im)
d.text((256, 64), '노약자·장애인·임산부 보호석', font=font(38), fill='white', anchor='mm'); save('priority', im, 88)
im = Image.new('RGB', (256, 256), (246, 200, 40)); d = ImageDraw.Draw(im)
d.text((128, 92), '기대지', font=font(62), fill=(30, 30, 30), anchor='mm'); d.text((128, 168), '마세요', font=font(62), fill=(30, 30, 30), anchor='mm'); save('caution', im, 88)
# 광고 칸: 이 책의 지면 8장
pages = sorted(p for p in glob.glob(f'{PAGES}/small/front*.jpg') if '/._' not in p)
sel = [pages[i] for i in (0, 4, 8, 12, 16, 20, 24, 28)]
atlas = Image.new('RGB', (2048, 1024), 'white')
for i, p in enumerate(sel):
    pg = Image.open(p).convert('RGB'); pw, ph = 512, 512
    cell = Image.new('RGB', (pw, ph), (250, 250, 247)); k = min(490 / pg.width, 490 / pg.height); pg = pg.resize((int(pg.width * k), int(pg.height * k)))
    cell.paste(pg, ((pw - pg.width) // 2, (ph - pg.height) // 2)); atlas.paste(cell, ((i % 4) * 512, (i // 4) * 512))
save('ads', atlas, 84)
print('ok')
