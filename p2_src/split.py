"""OCR JSON → 문장마다 스캔 단어 조각을 이은 한 줄 이미지(s/f01-03.jpg) + 목록 JSON(sentences.json).
화면에선 단어마다 이 이미지의 해당 구간만 보여줘서 글처럼 줄바꿈된다.
usage: split.py raw.json <out_dir>   (raw.json = ocr.py 결과)"""
import json, os, re, sys
from PIL import Image

H_OUT = 56           # 출력 높이(px). 화면에선 절반 이하로 보여 2배 선명도
PAD_X, PAD_Y = 3, 6  # 단어 상자 바깥 여유
ENDS, CLOSERS = ".?!", "”\"’'」』)"
HEADER = re.compile(r"\d+\s*p$")  # 원문 맨 위 「책 제목 120p」 줄


def med(xs):
    xs = sorted(xs)
    return xs[len(xs) // 2]


def good_boxes(ln):
    """공백(0 상자)·줄 전체를 덮는 엉뚱한 상자(Vision이 가끔 줌)는 None"""
    real = [bx if bx and bx[2] > 0 and bx[3] > 0 else None for bx in ln["boxes"]]
    m = med([bx[3] for bx in real if bx])
    return [bx if bx and bx[3] < m * 1.6 and bx[2] < m * 3 else None for bx in real]


def line_band(ln):
    """(줄 세로 중심, 줄 높이) = 글자 상자 위·아래선 중앙값"""
    bs = [bx for bx in good_boxes(ln) if bx]
    t, b = med([bx[1] for bx in bs]), med([bx[1] + bx[3] for bx in bs])
    return (t + b) / 2, b - t


def reading_order(lines):
    """위→아래, 같은 줄(세로 중심 차이 < 줄높이 절반)로 쪼개진 OCR 조각은 왼→오"""
    info = []
    for ln in lines:
        c, h = line_band(ln)
        info.append((c, h, min(bx[0] for bx in good_boxes(ln) if bx), ln))
    info.sort(key=lambda i: i[0])
    rows = []
    for i in info:
        if rows and abs(i[0] - rows[-1][0][0]) < i[1] / 2: rows[-1].append(i)
        else: rows.append([i])
    return [i[3] for row in rows for i in sorted(row, key=lambda i: i[2])]


def is_end(s, i):
    if s[i] not in ENDS: return False
    # 「A. 몰레스」 같은 이니셜은 문장 끝 아님
    if s[i] == "." and i >= 1 and s[i-1].isupper() and s[i-1].isascii() and (i == 1 or s[i-2] == " "): return False
    j = i + 1
    while j < len(s) and s[j] in CLOSERS: j += 1
    return j == len(s) or s[j] == " "


def sentences(lines):
    """줄들 → 문장마다 [(줄, 시작, 끝), ...]"""
    out, cur = [], []
    for li, ln in enumerate(lines):
        s, start = ln["text"], 0
        for i in range(len(s)):
            if is_end(s, i):
                j = i + 1
                while j < len(s) and s[j] in CLOSERS: j += 1
                cur.append((li, start, j)); out.append(cur); cur = []; start = j
        if s[start:].strip(): cur.append((li, start, len(s)))
    if cur: out.append(cur)
    # 문장부호만 남은 조각(OCR이 마침표를 다음 줄에 한 번 더 읽는 경우)은 버림
    has_word = lambda seg: re.search(r"\w", lines[seg[0]]["text"][seg[1]:seg[2]])
    return [s for s in ([seg for seg in sent if has_word(seg)] for sent in out) if s]


def words(ln, a, b):
    """줄의 [a, b) 구간 → 띄어쓰기 단위 (시작, 끝) 목록"""
    return [(a + m.start(), a + m.end()) for m in re.finditer(r"\S+", ln["text"][a:b])]


def crop_word(img, ln, boxes, a, b, line_h):
    bs = [bx for bx in boxes[a:b] if bx]
    if not bs: return None
    c, _ = line_band(ln)
    x0, x1 = min(bx[0] for bx in bs) - PAD_X, max(bx[0] + bx[2] for bx in bs) + PAD_X
    y0, y1 = c - line_h / 2 - PAD_Y, c + line_h / 2 + PAD_Y  # 한 지면 안은 모두 같은 높이 → 같은 글자 크기
    piece = img.crop((max(0, int(x0)), max(0, int(y0)), min(img.width, int(x1)), min(img.height, int(y1))))
    return piece.resize((max(1, round(piece.width * H_OUT / piece.height)), H_OUT), Image.LANCZOS)


def main(raw_path, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    items = []
    for path, page in sorted(json.load(open(raw_path)).items()):
        kind = "f" if "/front/" in path else "n"
        day = int(re.search(r"day(\d+)", path).group(1))
        lines = reading_order(page["lines"])
        if kind == "f" and lines and HEADER.search(lines[0]["text"].strip()): lines = lines[1:]
        line_h = med([line_band(ln)[1] for ln in lines])
        img = Image.open(path).convert("RGB")
        for n, sent in enumerate(sentences(lines), 1):
            pieces = []
            for li, a, b in sent:
                boxes = good_boxes(lines[li])
                pieces += [p for wa, wb in words(lines[li], a, b) if (p := crop_word(img, lines[li], boxes, wa, wb, line_h))]
            strip = Image.new("RGB", (sum(p.width for p in pieces), H_OUT), "white")
            spans, x = [], 0
            for p in pieces:
                strip.paste(p, (x, 0)); spans.append([x, p.width]); x += p.width
            strip.save(os.path.join(out_dir, f"{kind}{day:02d}-{n:02d}.jpg"), quality=78, optimize=True)
            items.append({"d": day, "k": kind, "n": n, "sw": strip.width, "w": spans,
                          "t": " ".join(lines[li]["text"][a:b].strip() for li, a, b in sent)})
    json.dump(items, open(os.path.join(out_dir, "..", "sentences.json"), "w"), ensure_ascii=False, separators=(",", ":"))
    print(len(items), "문장")


if __name__ == "__main__":
    main(*sys.argv[1:])
