#!/usr/bin/env python3
"""transcribe.py AUDIO.wav "question" -> Gemini audio understanding"""
import base64, json, os, sys, urllib.request
f, q = sys.argv[1:3]
body = {"contents": [{"parts": [{"inline_data": {"mime_type": "audio/wav", "data": base64.b64encode(open(f, 'rb').read()).decode()}}, {"text": q}]}]}
req = urllib.request.Request("https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent",
    data=json.dumps(body).encode(), headers={"Content-Type": "application/json", "x-goog-api-key": os.environ["GEMINI_KEY"]})
d = json.load(urllib.request.urlopen(req, timeout=300))
print("".join(p.get("text", "") for p in d["candidates"][0]["content"]["parts"]).strip())
