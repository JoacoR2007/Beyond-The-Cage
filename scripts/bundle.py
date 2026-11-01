"""Junta todo en un solo archivo (dist/index.single.html): útil para pegarlo en claude.ai u hospedarlo en cualquier lado.
Incrusta CSS, JS, datos, íconos y (si existen) las fotos de assets/photos.
Uso: python scripts/build_data.py && python scripts/bundle.py"""
import base64, json, re
from pathlib import Path
R = Path(__file__).resolve().parent.parent
b64 = lambda p: base64.b64encode(p.read_bytes()).decode()
h = (R / "index.html").read_text(encoding="utf-8")
h = h.replace('<link rel="stylesheet" href="css/styles.css">', "<style>" + (R / "css/styles.css").read_text(encoding="utf-8") + "</style>")
def uri(m):
    p = R / m.group(2)
    if not p.exists(): return m.group(0)
    return f'{m.group(1)}="data:{"image/x-icon" if p.suffix == ".ico" else "image/png"};base64,{b64(p)}"'
h = re.sub(r'(href|src)="(assets/[^"]+\.(?:png|ico))"', uri, h)
dump = lambda o: json.dumps(o, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
data = dump(json.load(open(R / "data/fighters.json", encoding="utf-8")))
photos = {"photos": []}
if (R / "data/fight_photos.json").exists():
    photos = json.load(open(R / "data/fight_photos.json", encoding="utf-8"))
    for p in photos["photos"]:
        if p and (R / p["file"]).exists(): p["file"] = "data:image/jpeg;base64," + b64(R / p["file"])
        elif p: p["file"] = ""          # sin archivo local: se muestra el afiche
for f in ("i18n", "model", "images", "app"):
    code = (R / f"js/{f}.js").read_text(encoding="utf-8")
    if f == "app": code = f"window.__DATA__={data};window.__PHOTOS__={dump(photos)};\n" + code
    h = h.replace(f'<script src="js/{f}.js"></script>', "<script>" + code + "</script>")
(R / "dist").mkdir(exist_ok=True)
(R / "dist/index.single.html").write_text(h, encoding="utf-8")
print("dist/index.single.html", len(h) // 1024, "KB")
