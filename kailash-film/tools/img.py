#!/usr/bin/env python3
"""gen image: img.py OUT.png "prompt" [ref1.png ref2.png ...]  -> Gemini 3 Pro Image, 9:16"""
import base64, json, os, sys, urllib.request
out, prompt, refs = sys.argv[1], sys.argv[2], sys.argv[3:]
parts = [{"text": prompt}]
for r in refs:
    parts.append({"inline_data": {"mime_type": "image/png", "data": base64.b64encode(open(r, 'rb').read()).decode()}})
body = {"contents": [{"parts": parts}], "generationConfig": {"responseModalities": ["IMAGE"], "imageConfig": {"aspectRatio": "9:16", "imageSize": "2K"}}}
req = urllib.request.Request("https://generativelanguage.googleapis.com/v1beta/models/gemini-3-pro-image:generateContent",
    data=json.dumps(body).encode(), headers={"Content-Type": "application/json", "x-goog-api-key": os.environ["GEMINI_KEY"]})
d = json.load(urllib.request.urlopen(req, timeout=300))
for c in d.get("candidates", []):
    for p in c.get("content", {}).get("parts", []):
        if "inlineData" in p:
            open(out, 'wb').write(base64.b64decode(p["inlineData"]["data"])); print("saved", out); sys.exit(0)
print("NO IMAGE", json.dumps(d)[:800]); sys.exit(1)
