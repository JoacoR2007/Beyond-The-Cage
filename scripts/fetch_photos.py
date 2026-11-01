"""Descarga una foto con licencia libre (Wikimedia Commons) para cada una de las 8 peleas del carrusel.
Guarda assets/photos/fight-N.jpg y data/fight_photos.json (autor y licencia: el sitio los muestra, como exigen las licencias CC).
Uso:  python scripts/fetch_photos.py [--force]        Requiere: pip install requests
Si no te gusta una foto, poné en FIGHTS  "file": "Nombre_exacto_del_archivo.jpg"  (título en commons.wikimedia.org) y volvé a correrlo con --force."""
import html, json, re, sys, time
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "photos"
JSON = ROOT / "data" / "fight_photos.json"
API = "https://commons.wikimedia.org/w/api.php"
S = requests.Session()
S.headers["User-Agent"] = "beyond-the-cage/1.0 (fan site; Commons photo fetcher)"
OK = re.compile(r"^(CC BY(-SA)?[ -]\d|CC0|Public domain|PD)", re.I)      # licencias que permiten reutilizar con crédito
BAD = re.compile(r"NC|ND|fair use", re.I)

# q: búsquedas (de más a menos específica) · names: apellidos que deben aparecer en el título o la descripción · ev: evento
FIGHTS = [
    {"q": ["Anderson Silva Chael Sonnen UFC 117", "Anderson Silva UFC", "Chael Sonnen"], "names": ["silva", "sonnen"], "ev": "UFC 117"},
    {"q": ["Jon Jones Lyoto Machida UFC 140", "Jon Jones UFC", "Lyoto Machida"], "names": ["jones", "machida"], "ev": "UFC 140"},
    {"q": ["Conor McGregor Jose Aldo UFC 194", "Conor McGregor UFC 194", "Conor McGregor"], "names": ["mcgregor", "aldo"], "ev": "UFC 194"},
    {"q": ["Jon Jones Daniel Cormier UFC 214", "Daniel Cormier Jon Jones", "Daniel Cormier"], "names": ["jones", "cormier"], "ev": "UFC 214"},
    {"q": ["Khabib Nurmagomedov Conor McGregor UFC 229", "Khabib Nurmagomedov", "Conor McGregor"], "names": ["khabib", "nurmagomedov", "mcgregor"], "ev": "UFC 229"},
    {"q": ["Islam Makhachev Alexander Volkanovski UFC 284", "Islam Makhachev", "Alexander Volkanovski"], "names": ["makhachev", "volkanovski"], "ev": "UFC 284"},
    {"q": ["Israel Adesanya Alex Pereira UFC 287", "Israel Adesanya", "Alex Pereira"], "names": ["adesanya", "pereira"], "ev": "UFC 287"},
    {"q": ["Ilia Topuria Alexander Volkanovski UFC 298", "Ilia Topuria", "Alexander Volkanovski"], "names": ["topuria", "volkanovski"], "ev": "UFC 298"},
]

def query(**kw):
    p = {"action": "query", "format": "json", "prop": "imageinfo", "iiprop": "url|size|mime|extmetadata", "iiurlwidth": 1400}
    r = S.get(API, params={**p, **kw}, timeout=60)
    r.raise_for_status()
    return list(r.json().get("query", {}).get("pages", {}).values())

def clean(s): return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html.unescape(s or ""))).strip()

def score(p, f):
    ii = (p.get("imageinfo") or [{}])[0]
    m = ii.get("extmetadata", {})
    lic = m.get("LicenseShortName", {}).get("value", "")
    if not OK.search(lic) or BAD.search(lic) or ii.get("mime") != "image/jpeg" or ii.get("width", 0) < 900: return None
    text = (p["title"] + " " + clean(m.get("ImageDescription", {}).get("value"))).lower()
    hits = sum(n in text for n in f["names"])
    if not hits: return None
    return hits * 2 + (3 if f["ev"].lower() in text else 0) + (1 if ii["width"] > ii.get("height", 0) else 0)

def pick(f):
    if f.get("file"):
        pages = query(titles="File:" + f["file"].replace("File:", ""))
        return pages[0] if pages and "imageinfo" in pages[0] else None
    for q in f["q"]:
        pages = query(generator="search", gsrsearch=q + " filetype:bitmap", gsrnamespace=6, gsrlimit=30)
        ranked = sorted(((score(p, f), p) for p in pages), key=lambda x: -(x[0] or -1))
        if ranked and ranked[0][0] is not None:
            return ranked[0][1]
        time.sleep(1)
    return None

def main():
    force = "--force" in sys.argv
    OUT.mkdir(parents=True, exist_ok=True)
    old = json.loads(JSON.read_text(encoding="utf-8")).get("photos", []) if JSON.exists() else []
    old += [None] * (len(FIGHTS) - len(old))
    photos = []
    for i, f in enumerate(FIGHTS):
        name = f"fight-{i + 1}"
        if old[i] and (ROOT / old[i]["file"]).exists() and not force:
            print(f"[{i + 1}/8] {f['ev']}: ya estaba"); photos.append(old[i]); continue
        try:
            p = pick(f)
            if not p: print(f"[{i + 1}/8] {f['ev']}: sin foto libre adecuada (el sitio muestra un afiche)"); photos.append(None); continue
            ii, m = p["imageinfo"][0], p["imageinfo"][0]["extmetadata"]
            img = S.get(ii.get("thumburl") or ii["url"], timeout=120); img.raise_for_status()
            (OUT / f"{name}.jpg").write_bytes(img.content)
            photos.append({"file": f"assets/photos/{name}.jpg", "credit": clean(m.get("Artist", {}).get("value")) or clean(m.get("Credit", {}).get("value")) or "Wikimedia Commons",
                           "license": m.get("LicenseShortName", {}).get("value", "CC"), "page": ii["descriptionurl"], "source": "Wikimedia Commons"})
            print(f"[{i + 1}/8] {f['ev']}: {p['title']} ({photos[-1]['license']})")
        except Exception as e:
            print(f"[{i + 1}/8] {f['ev']}: ERROR {e}"); photos.append(old[i])
        time.sleep(1)
    JSON.write_text(json.dumps({"photos": photos}, ensure_ascii=False, indent=1), encoding="utf-8")
    print("Listo. Recargá el sitio y tocá una cara del octágono.")

if __name__ == "__main__":
    main()
