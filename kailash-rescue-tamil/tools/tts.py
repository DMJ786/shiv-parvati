#!/usr/bin/env python3
"""tts.py MODEL VOICE OUT.wav "text"  -> Gemini TTS (24 kHz PCM) to wav"""
import base64, json, os, sys, urllib.request, urllib.error, wave
model, voice, out, text = sys.argv[1:5]
body = {"contents": [{"parts": [{"text": text}]}], "generationConfig": {"responseModalities": ["AUDIO"],
        "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": voice}}}}}
req = urllib.request.Request(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
    data=json.dumps(body).encode(), headers={"Content-Type": "application/json", "x-goog-api-key": os.environ["GEMINI_KEY"]})
try: d = json.load(urllib.request.urlopen(req, timeout=300))
except urllib.error.HTTPError as e: print("ERR", e.code, e.read().decode()[:400]); sys.exit(1)
p = d["candidates"][0]["content"]["parts"][0]["inlineData"]
pcm = base64.b64decode(p["data"])
with wave.open(out, 'wb') as w: w.setnchannels(1); w.setsampwidth(2); w.setframerate(24000); w.writeframes(pcm)
print("saved", out, p.get("mimeType"), len(pcm) / 48000, "s")
