#!/usr/bin/env python3
"""Extract a Halo QR-ordering menu and render it as a visual HTML page.

Usage:
    python3 halo_menu.py --token <TOKEN>          # fetch live from /getToken
    python3 halo_menu.py --from-file resp.json    # parse a saved getToken response

Outputs:
    menu.json   normalized menu data
    menu.html   self-contained visual menu
"""
import argparse
import html
import json
import sys
import urllib.request
from collections import defaultdict

HOST = "https://www.haloweb.thesimplepower.com"
URL = HOST + "/getToken"

# Category names are not present in the API response; only numeric ids are.
# These were inferred by hand from the items in each group for store 隱炭 (id 79).
CATEGORY_NAMES = {
    1064: "Salt/sauce-grilled skewers",
    1065: "Grilled / baked dishes",
    1066: "Stir-fry / mains",
    1067: "Fried",
    1068: "Soups",
    1069: "Cold dishes",
    1070: "Rice / noodles",
    1071: "Salads",
    1072: "Sashimi",
    1073: "Sake",
    1074: "Plum & fruit liqueurs",
    1075: "Soft drinks",
    1076: "Sours / chu-hi",
    1077: "Beer / highball",
    1079: "Dessert",
    1085: "Spirits / other",
    1114: "Sets / promos",
    1257: "Signature / premium",
}


def loc(field):
    """Parse a Halo locale-array field into {locale: value}."""
    if not field:
        return {}
    arr = json.loads(field) if isinstance(field, str) else field
    return {
        o["locale"]: o["value"]
        for o in arr
        if isinstance(o, dict) and o.get("value")
    }


def fetch(token):
    req = urllib.request.Request(
        URL,
        data=json.dumps({"type": "qr", "param": token}).encode(),
        headers={
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X)",
        },
        method="POST",
    )
    return json.load(urllib.request.urlopen(req, timeout=20))


def normalize(resp):
    scd = resp["spaceCartData"]
    if not scd.get("result"):
        raise SystemExit(f"getToken returned result=false: {scd.get('message')!r}")
    data = scd["data"]

    seen = {}
    for c in data.get("campaignList", []):
        for p in c.get("productList", []):
            pid = p["id"]
            if pid in seen:
                continue
            nm = loc(p.get("name"))
            seen[pid] = {
                "id": pid,
                "zh": nm.get("zh", ""),
                "en": nm.get("en", ""),
                "ja": nm.get("ja", ""),
                "price": p.get("price"),
                "categoryId": p.get("categoryId"),
                "displayOrder": p.get("displayOrder"),
                "imageUrl": p.get("imageUrl") or "",
                "enabled": p.get("isEnable"),
                "online": p.get("isOnlineShow"),
            }

    items = []
    for v in seen.values():
        # Drop disabled/hidden rows and $0 promo/review placeholders.
        if v["enabled"] is False or v["online"] is False:
            continue
        if not v["price"] and ("好評" in v["zh"] or v["price"] == 0):
            continue
        items.append(v)

    store = (
        data.get("storeName")
        or loc(data.get("name")).get("zh")
        or "隱炭"
    )
    return {"store": store, "items": items}


def image_src(url):
    if not url:
        return ""
    if url.startswith("http://") or url.startswith("https://"):
        return url
    return HOST + "/" + url.lstrip("/")


def render_html(menu):
    bycat = defaultdict(list)
    for v in menu["items"]:
        bycat[v["categoryId"]].append(v)

    store = html.escape(menu["store"])
    sections = []
    for cat in sorted(bycat, key=lambda c: (c is None, c)):
        cat_name = CATEGORY_NAMES.get(cat, f"Category {cat}")
        rows = sorted(bycat[cat], key=lambda x: (x["displayOrder"] is None, x["displayOrder"] or 0))
        cards = []
        for v in rows:
            zh = html.escape(v["zh"])
            en = html.escape(v["en"] or v["ja"] or "")
            price = v["price"]
            price_txt = f"NT$ {price:,}" if isinstance(price, (int, float)) else ""
            src = image_src(v["imageUrl"])
            img = (
                f'<div class="thumb" style="background-image:url(\'{html.escape(src, quote=True)}\')"></div>'
                if src
                else '<div class="thumb noimg"></div>'
            )
            en_html = f'<div class="en">{en}</div>' if en else ""
            cards.append(
                f'<li class="card">{img}'
                f'<div class="body"><div class="zh">{zh}</div>{en_html}'
                f'<div class="price">{price_txt}</div></div></li>'
            )
        sections.append(
            f'<section><h2>{html.escape(cat_name)}</h2>'
            f'<ul class="grid">{"".join(cards)}</ul></section>'
        )

    return f"""<!doctype html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{store} — Menu</title>
<style>
  :root {{ --bg:#14110f; --card:#1f1b18; --ink:#f3ede4; --muted:#b8a890; --accent:#d9a441; }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; background:var(--bg); color:var(--ink);
         font-family:"Helvetica Neue",-apple-system,"Noto Sans TC",sans-serif; }}
  header {{ padding:2.5rem 1.25rem 1.5rem; text-align:center; border-bottom:1px solid #322c27; }}
  header h1 {{ margin:0; font-size:2.4rem; letter-spacing:.15em; }}
  header p {{ margin:.5rem 0 0; color:var(--muted); letter-spacing:.3em; font-size:.8rem; text-transform:uppercase; }}
  main {{ max-width:1100px; margin:0 auto; padding:1.25rem; }}
  section {{ margin:2rem 0; }}
  section h2 {{ font-size:1.15rem; color:var(--accent); border-bottom:1px solid #322c27;
                padding-bottom:.5rem; margin:0 0 1rem; letter-spacing:.05em; }}
  .grid {{ list-style:none; margin:0; padding:0; display:grid;
           grid-template-columns:repeat(auto-fill,minmax(220px,1fr)); gap:1rem; }}
  .card {{ background:var(--card); border-radius:12px; overflow:hidden; display:flex; flex-direction:column; }}
  .thumb {{ aspect-ratio:4/3; background-size:cover; background-position:center; background-color:#2a2420; }}
  .thumb.noimg {{ background:linear-gradient(135deg,#2a2420,#1a1613); }}
  .body {{ padding:.75rem .85rem 1rem; display:flex; flex-direction:column; gap:.2rem; flex:1; }}
  .zh {{ font-size:1.05rem; font-weight:600; }}
  .en {{ font-size:.8rem; color:var(--muted); }}
  .price {{ margin-top:auto; padding-top:.4rem; color:var(--accent); font-weight:600; }}
  footer {{ text-align:center; color:var(--muted); font-size:.75rem; padding:2rem 1rem 3rem; }}
</style>
</head>
<body>
<header><h1>{store}</h1><p>Charcoal grill &middot; Izakaya</p></header>
<main>{"".join(sections)}</main>
<footer>Prices in NT$. Generated from Halo menu data.</footer>
</body>
</html>
"""


def main():
    ap = argparse.ArgumentParser(description="Extract & render a Halo QR menu.")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--token", help="QR value token")
    g.add_argument("--from-file", help="path to a saved getToken JSON response")
    ap.add_argument("--json-out", default="menu.json")
    ap.add_argument("--html-out", default="menu.html")
    args = ap.parse_args()

    if args.from_file:
        with open(args.from_file, encoding="utf-8") as f:
            resp = json.load(f)
    else:
        resp = fetch(args.token)

    menu = normalize(resp)

    with open(args.json_out, "w", encoding="utf-8") as f:
        json.dump(menu, f, ensure_ascii=False, indent=2)
    with open(args.html_out, "w", encoding="utf-8") as f:
        f.write(render_html(menu))

    print(f"store: {menu['store']}")
    print(f"items: {len(menu['items'])}")
    print(f"wrote: {args.json_out}, {args.html_out}")


if __name__ == "__main__":
    main()
