#!/usr/bin/env python3
"""veo.py OUT.mp4 KEYFRAME.png "prompt" [resolution]  -> Veo 3.1 Fast image-to-video, 9:16, 8 s, native audio"""
import base64, json, os, sys, time, urllib.request, urllib.error
out, img, prompt = sys.argv[1:4]; res = sys.argv[4] if len(sys.argv) > 4 else "1080p"
KEY = os.environ["GEMINI_KEY"]; BASE = "https://generativelanguage.googleapis.com/v1beta/"
def call(url, body=None):
    req = urllib.request.Request(BASE + url, data=json.dumps(body).encode() if body else None,
                                 headers={"Content-Type": "application/json", "x-goog-api-key": KEY})
    return json.load(urllib.request.urlopen(req, timeout=120))
body = {"instances": [{"prompt": prompt, "image": {"bytesBase64Encoded": base64.b64encode(open(img, 'rb').read()).decode(), "mimeType": "image/png"}}],
        "parameters": {"aspectRatio": "9:16", "durationSeconds": 8, "resolution": res, "personGeneration": "allow_adult",
                       "negativePrompt": "text, captions, watermark, logo, distorted hands, extra fingers, morphing face, cartoon"}}
try:
    op = call("models/veo-3.1-fast-generate-preview:predictLongRunning", body)
except urllib.error.HTTPError as e:
    print("SUBMIT ERR", e.code, e.read().decode()[:600]); sys.exit(1)
name = op["name"]; print("op", name, flush=True)
while True:
    time.sleep(15); st = call(name)
    if st.get("done"): break
if "error" in st: print("ERR", json.dumps(st["error"])[:600]); sys.exit(1)
resp = st["response"].get("generateVideoResponse", st["response"])
samples = resp.get("generatedSamples") or resp.get("videos")
if not samples: print("NO VIDEO", json.dumps(st)[:800]); sys.exit(1)
uri = samples[0]["video"]["uri"]
req = urllib.request.Request(uri, headers={"x-goog-api-key": KEY})
open(out, 'wb').write(urllib.request.urlopen(req, timeout=300).read()); print("saved", out)
