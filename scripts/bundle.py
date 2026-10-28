"""Junta todo en un solo archivo (dist/index.single.html): útil para pegarlo en claude.ai u hospedarlo en cualquier lado.
Uso: python scripts/build_data.py && python scripts/bundle.py"""
import base64, json, re
from pathlib import Path
R = Path(__file__).resolve().parent.parent
h = (R / "index.html").read_text(encoding="utf-8")
h = h.replace('<link rel="stylesheet" href="css/styles.css">', "<style>" + (R / "css/styles.css").read_text(encoding="utf-8") + "</style>")
data = json.dumps(json.load(open(R / "data/fighters.json", encoding="utf-8")), ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
for f in ("i18n", "model", "images", "app"):
    code = (R / f"js/{f}.js").read_text(encoding="utf-8")
    if f == "app": code = f"window.__DATA__={data};\n" + code
    h = h.replace(f'<script src="js/{f}.js"></script>', "<script>" + code + "</script>")
h = h.replace("assets/logo.png", "data:image/png;base64," + base64.b64encode((R / "assets/logo.png").read_bytes()).decode())
(R / "dist").mkdir(exist_ok=True)
(R / "dist/index.single.html").write_text(h, encoding="utf-8")
print("dist/index.single.html", len(h) // 1024, "KB")
