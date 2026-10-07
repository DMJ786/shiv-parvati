#!/usr/bin/env python3
"""lyria.py MODEL OUT_BASENAME "prompt" -> saves audio returned by Lyria via generateContent"""
import base64, json, os, sys, urllib.request, urllib.error
model, out, prompt = sys.argv[1:4]
body = {"contents": [{"parts": [{"text": prompt}]}]}
req = urllib.request.Request(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
    data=json.dumps(body).encode(), headers={"Content-Type": "application/json", "x-goog-api-key": os.environ["GEMINI_KEY"]})
try: d = json.load(urllib.request.urlopen(req, timeout=600))
except urllib.error.HTTPError as e: print("ERR", e.code, e.read().decode()[:500]); sys.exit(1)
n = 0
for c in d.get("candidates", []):
    for p in c.get("content", {}).get("parts", []):
        if "inlineData" in p:
            mt = p["inlineData"].get("mimeType", "audio/wav"); ext = {"audio/mpeg": "mp3", "audio/mp3": "mp3", "audio/wav": "wav", "audio/x-wav": "wav", "audio/L16": "pcm"}.get(mt.split(';')[0], "bin")
            fn = f"{out}_{n}.{ext}"; open(fn, 'wb').write(base64.b64decode(p["inlineData"]["data"])); print("saved", fn, mt); n += 1
        elif "text" in p: print("text:", p["text"][:300])
if not n: print("NO AUDIO", json.dumps(d)[:600])
