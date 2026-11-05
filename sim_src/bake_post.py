"""lightmap.npy → webp + 배율. 사용: bake_post.py <build폴더> <사이트 sim 폴더>"""
import numpy as np, cv2, sys, json, shutil, os
B, OUT = sys.argv[1], sys.argv[2]
SMOOTH = len(sys.argv) > 3 and sys.argv[3] == "smooth"  # 흰 벽처럼 민무늬가 많은 공간은 더 곱게
px = np.load(f'{B}/lightmap.npy')
live = px[px.sum(2) > 0]
GAMMA = .62                                      # 폰 사진의 HDR처럼 어두운 곳을 끌어올림
ref = float(np.median(live))                     # 중간 밝기 = 1.0
y = np.power(px / ref, GAMMA)
k = float(np.percentile(y[px.sum(2) > 0], 99.7))
x = np.clip(y / k, 0, 1)
def encode(y, name):
    x = np.clip(y / k, 0, 1)
    x = np.dstack([cv2.medianBlur(x[..., c], 5) for c in range(3)])  # 튀는 점(반딧불) 제거
    x = cv2.bilateralFilter(x, 15, .14, 7) if SMOOTH else cv2.bilateralFilter(x, 7, .05, 2.2)  # 표본 노이즈만 지움
    s = np.where(x <= .0031308, x * 12.92, 1.055 * np.power(x, 1 / 2.4) - .055)
    s = (s * 255 + np.random.default_rng(1).uniform(-.5, .5, s.shape) + .5).clip(0, 255).astype(np.uint8)[..., ::-1]
    cv2.imwrite(f'{OUT}/{name}.webp', s, [cv2.IMWRITE_WEBP_QUALITY, 92])
os.makedirs(OUT, exist_ok=True)
encode(y, 'lightmap')
has_off = os.path.exists(f'{B}/lightmap_off.npy')
if has_off:
    encode(np.power(np.load(f'{B}/lightmap_off.npy').clip(0) / ref, GAMMA), 'lightmap_off')  # 켠 상태와 같은 기준이라 실제로 어두움
scene = json.load(open(f'{B}/scene.json')); scene['lightmapScale'] = k; scene['lightmapOff'] = has_off
json.dump(scene, open(f'{OUT}/scene.json', 'w'), ensure_ascii=False)
shutil.copy(f'{B}/room.glb', f'{OUT}/room.glb'); shutil.copy(f'{B}/env.jpg', f'{OUT}/env.jpg')
print('lightmap scale', k, 'kb', os.path.getsize(f'{OUT}/lightmap.webp') // 1024, 'glb kb', os.path.getsize(f'{OUT}/room.glb') // 1024)
