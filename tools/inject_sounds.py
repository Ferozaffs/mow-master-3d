"""Injects base64-encoded mp3s from tools/mp3 into ../index.html."""
import base64, json, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
MP3 = os.path.join(HERE, "mp3")
HTML = os.path.join(HERE, "..", "index.html")

data = {}
names = ["music", "engine", "hit", "gnome", "cluck", "squawk", "swing", "step"]
for n in names:
    with open(os.path.join(MP3, n + ".mp3"), "rb") as f:
        data[n] = base64.b64encode(f.read()).decode()
    print(n, len(data[n]) // 1024, "KB (b64)")

with open(HTML, "r", encoding="utf-8") as f:
    html = f.read()

new, count = re.subn(
    r"const SOUND_DATA = /\*SOUNDS\*/\{.*?\};",  # replace inner we can't with .*? across same line
    "const SOUND_DATA = /*SOUNDS*/__DATA__;".replace("__DATA__", json.dumps(data, separators=(",", ":"))),
    html, count=1, flags=re.S)

if count == 0:
    # build replacement for the multiline base64 already embedded
    new = re.sub(
        r"const SOUND_DATA = /\*SOUNDS\*/.*?;",
        "const SOUND_DATA = /*SOUNDS*/" + json.dumps(data, separators=(",", ":")) + ";",
        html, count=1, flags=re.S)

with open(HTML, "w", encoding="utf-8") as f:
    f.write(new)
print("injected, total", sum(len(v) for v in data.values()) // 1024, "KB (b64)")
