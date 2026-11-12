"""스캔 지면 → Vision OCR 줄별 글자 상자 JSON. usage: ocr.py <out.json> <img>..."""
import json, sys
import Vision, Quartz
from Foundation import NSURL, NSMakeRange

def ocr(path):
    src = Quartz.CGImageSourceCreateWithURL(NSURL.fileURLWithPath_(path), None)
    cg = Quartz.CGImageSourceCreateImageAtIndex(src, 0, None)
    W, H = Quartz.CGImageGetWidth(cg), Quartz.CGImageGetHeight(cg)
    req = Vision.VNRecognizeTextRequest.alloc().init()
    req.setRecognitionLevel_(Vision.VNRequestTextRecognitionLevelAccurate)
    req.setRecognitionLanguages_(["ko-KR", "en-US"])
    req.setUsesLanguageCorrection_(True)
    Vision.VNImageRequestHandler.alloc().initWithCGImage_options_(cg, None).performRequests_error_([req], None)
    lines = []
    for o in req.results() or []:
        c = o.topCandidates_(1)[0]
        s = str(c.string())
        boxes = []
        for i in range(len(s)):
            ob, _ = c.boundingBoxForRange_error_(NSMakeRange(i, 1), None)
            if ob is None: boxes.append(None); continue
            b = ob.boundingBox()
            boxes.append([b.origin.x * W, (1 - b.origin.y - b.size.height) * H, b.size.width * W, b.size.height * H])
        lines.append({"text": s, "boxes": boxes})
    return {"w": W, "h": H, "lines": lines}

json.dump({p: ocr(p) for p in sys.argv[2:]}, open(sys.argv[1], "w"), ensure_ascii=False)
