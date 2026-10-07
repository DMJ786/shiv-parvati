#!/usr/bin/env python3
"""veo2.py OUT.mp4 FIRST.png "prompt" [LAST.png]  -> Veo 3.1 Fast, 9:16, 8 s, 1080p, native audio.
Retries on 429 (rate limit) with backoff."""
import base64, json, os, sys, time, urllib.request, urllib.error
out, first, prompt = sys.argv[1:4]; last = sys.argv[4] if len(sys.argv) > 4 else None
KEY = os.environ["GEMINI_KEY"]; BASE = "https://generativelanguage.googleapis.com/v1beta/"
def call(url, body=None):
    req = urllib.request.Request(BASE + url, data=json.dumps(body).encode() if body else None,
                                 headers={"Content-Type": "application/json", "x-goog-api-key": KEY})
    return json.load(urllib.request.urlopen(req, timeout=120))
b64 = lambda p: {"bytesBase64Encoded": base64.b64encode(open(p, 'rb').read()).decode(), "mimeType": "image/png"}
inst = {"prompt": prompt, "image": b64(first)}
if last: inst["lastFrame"] = b64(last)
body = {"instances": [inst], "parameters": {"aspectRatio": "9:16", "durationSeconds": 8, "resolution": "1080p", "personGeneration": "allow_adult",
        "negativePrompt": "text, captions, watermark, extra fingers, merged hands, glowing eyes, sparks, magic explosion, lightning flashes, cartoon, plastic skin, morphing face, clothing change, swapped hands"}}
for attempt in range(int(os.environ.get("TRIES", "12"))):
    try: op = call("models/" + os.environ.get("VEO_MODEL", "veo-3.1-fast-generate-preview") + ":predictLongRunning", body); break
    except urllib.error.HTTPError as e:
        msg = e.read().decode()[:400]
        if e.code == 429: print("429:", msg.replace(chr(10)," ")[:400], flush=True); time.sleep(60); continue
        print("SUBMIT ERR", e.code, msg); sys.exit(1)
else: print("gave up"); sys.exit(1)
name = op["name"]; print("op", name, flush=True)
while True:
    time.sleep(15)
    try: st = call(name)
    except Exception as e: print("poll err", e, flush=True); continue
    if st.get("done"): break
if "error" in st: print("ERR", json.dumps(st["error"])[:600]); sys.exit(1)
resp = st["response"].get("generateVideoResponse", st["response"])
samples = resp.get("generatedSamples") or resp.get("videos")
if not samples: print("NO VIDEO (filtered?)", json.dumps(st)[:800]); sys.exit(1)
req = urllib.request.Request(samples[0]["video"]["uri"], headers={"x-goog-api-key": KEY})
open(out, 'wb').write(urllib.request.urlopen(req, timeout=300).read()); print("saved", out)
