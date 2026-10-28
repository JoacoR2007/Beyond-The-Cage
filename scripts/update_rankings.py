"""Actualiza data/rankings.json (campeón + top 15 por división) desde Wikipedia, usando su API oficial.
ATENCIÓN: escrito sin poder probarlo contra Wikipedia. Si algo no cuadra, NO modifica el archivo,
imprime el motivo y termina con error (el workflow sigue con los rankings anteriores).
Uso: python scripts/update_rankings.py   (requiere: pip install requests lxml)"""
import datetime as dt, json, re, sys
from pathlib import Path
import requests
from lxml import html

PATH = Path(__file__).resolve().parent.parent / "data" / "rankings.json"
CODES = {"light heavyweight": "LHW", "flyweight": "FLY", "bantamweight": "BW", "featherweight": "FW",
         "lightweight": "LW", "welterweight": "WW", "middleweight": "MW", "heavyweight": "HW"}
DIVS = ["FLY", "BW", "FW", "LW", "WW", "MW", "LHW", "HW"]

def fail(msg): sys.exit("update_rankings: " + msg)
def text(el): return re.sub(r"\[[^\]]*\]", "", el.text_content()).strip()
def division(heading):
    h = heading.lower()
    for name, code in CODES.items():                      # "light heavyweight" va antes que "heavyweight"
        if name in h: return code

r = requests.get("https://en.wikipedia.org/w/api.php", timeout=60, headers={"User-Agent": "beyond-the-cage/1.0 (fan site; github)"},
                 params={"action": "parse", "page": "UFC_rankings", "prop": "text", "format": "json", "formatversion": 2})
r.raise_for_status()
root = html.fromstring(r.json()["parse"]["text"])
found, ctx = {}, {"h2": "", "h3": "", "h4": ""}
for el in root.iter("h2", "h3", "h4", "table"):
    if el.tag != "table":
        ctx[el.tag] = text(el)
        if el.tag == "h2": ctx["h3"] = ctx["h4"] = ""
        elif el.tag == "h3": ctx["h4"] = ""
        continue
    if "wikitable" not in (el.get("class") or "") or "women" in " ".join(ctx.values()).lower(): continue
    code = division(ctx["h4"] or ctx["h3"] or ctx["h2"])
    if not code or code in found: continue               # se usa la primera tabla masculina de cada división
    head = [text(c).lower() for c in el.xpath(".//tr[1]/th|.//tr[1]/td")]
    ni = next((i for i, c in enumerate(head) if c in ("fighter", "name")), None)
    ri = next((i for i, c in enumerate(head) if "record" in c), None)
    if ni is None: continue
    champ, ranked = None, []
    for tr in el.xpath(".//tr[position()>1]"):
        c = tr.xpath("./th|./td")
        if len(c) <= ni: continue
        rank, name = text(c[0]), text(c[ni])
        rec = re.match(r"\s*(\d+)\s*[–-]\s*(\d+)(?:\s*[–-]\s*(\d+))?", text(c[ri])) if ri is not None and len(c) > ri else None
        item = {"n": name, "r": "-".join(g for g in rec.groups() if g) if rec else None}
        if rank.upper().startswith("C"): champ = item
        elif rank.isdigit() and name: ranked.append((int(rank), item))
    ranked = [i for _, i in sorted(ranked, key=lambda x: x[0])]
    found[code] = ([champ] if champ else []) + ranked

old = json.loads(PATH.read_text(encoding="utf-8"))
if sorted(found) != sorted(DIVS): fail(f"no encontré todas las divisiones masculinas: {sorted(found)}")
today = dt.date.today().isoformat()
known = {f["n"]: f for d in old["divisions"].values() for f in d}
new, overlap = {}, 0
for code in DIVS:
    lst = found[code]
    champ = old.get("champions", {}).get(code)            # campeón fijado a mano (ej. título vacante)
    if champ: lst = [x for x in lst if x["n"] == champ][:1] or [{"n": champ, "r": None}] + [x for x in lst if x["n"] != champ]
    if len(lst) < 16: fail(f"{code}: solo {len(lst)} peleadores")
    new[code] = []
    for it in lst[:16]:
        k = known.get(it["n"])
        overlap += bool(k)
        new[code].append(dict(k) if k else {"n": it["n"], "c": "—", "r": it["r"] or "0-0", "s": "all", "asOf": today})
if overlap < 0.6 * 128: fail(f"solo {overlap} de 128 nombres coinciden con la lista anterior: no se actualiza")
old["divisions"] = new
PATH.write_text(json.dumps(old, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"rankings.json actualizado ({overlap} de 128 ya conocidos)")
