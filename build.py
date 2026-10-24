#!/usr/bin/env python3
"""District Times — static site generator.

Usage:  python3 build.py   -> writes dist/
Settings in site.json; sections in sections.json; articles in content/articles/*.md
(created from the newsroom panel at /admin/); fixed pages in content/pages/*.md.
"""
import shutil, json, hashlib, re, datetime as dt
from email.utils import format_datetime
from zoneinfo import ZoneInfo
from pathlib import Path
import markdown, yaml
from jinja2 import Environment, FileSystemLoader

ROOT = Path(__file__).parent
DIST = ROOT / "dist"
TZ = ZoneInfo("America/New_York")
env = Environment(loader=FileSystemLoader(ROOT / "templates"), autoescape=True)
SITE = json.loads((ROOT / "site.json").read_text(encoding="utf-8"))
SECTIONS = json.loads((ROOT / "sections.json").read_text(encoding="utf-8"))
SITE["v"] = hashlib.md5(b"".join((ROOT / "static" / f).read_bytes()
                                 for f in ("site.css", "site.js"))).hexdigest()[:8]
SITE["year"] = dt.date.today().year
WARDS = [f"ward-{i}" for i in range(1, 9)]
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August",
          "September", "October", "November", "December"]


def fmt_date(d, short=False):
    m = MONTHS[d.month - 1]
    return f"{m[:3]}. {d.day}" if short else f"{m} {d.day}, {d.year}"


env.filters["date"] = fmt_date


def img(src, w=1200):
    """Serve every image through Netlify Image CDN from our own domain.
    Remote (licensed) images are fetched by Netlify, never by the reader's browser."""
    from urllib.parse import quote
    if not src:
        return ""
    return f"/.netlify/images?url={quote(src, safe='')}&w={w}&fm=webp&q=75"


env.filters["img"] = img
env.globals["today"] = fmt_date(dt.datetime.now(TZ))
MD = lambda s: markdown.markdown((s or "").strip(), extensions=["extra", "sane_lists", "smarty"])


def to_dt(d):
    if d is None or d == "":
        return None
    if isinstance(d, str):
        d = dt.datetime.fromisoformat(d.replace("Z", "+00:00"))
    if isinstance(d, dt.date) and not isinstance(d, dt.datetime):
        d = dt.datetime(d.year, d.month, d.day, 9)
    return d.replace(tzinfo=TZ) if d.tzinfo is None else d.astimezone(TZ)


def front(f):
    raw = f.read_text(encoding="utf-8")
    if not raw.startswith("---"):
        raise SystemExit(f"{f}: missing front matter")
    _, head, body = raw.split("---", 2)
    return yaml.safe_load(head) or {}, body


class EditorialError(Exception):
    pass


def load_articles():
    """Every published article must be signed, dated and cite at least one source."""
    out, problems = [], []
    for f in sorted((ROOT / "content" / "articles").glob("*.md")):
        m, body = front(f)
        if m.get("draft"):
            continue
        miss = [k for k in ("title", "section", "author", "date", "dek") if not m.get(k)]
        if not m.get("sources"):
            miss.append("sources")
        if m.get("section") not in SECTIONS:
            miss.append("valid section")
        if miss:
            problems.append(f"{f.name}: missing {', '.join(miss)}")
            continue
        m["date"] = to_dt(m["date"])
        m["updated"] = to_dt(m.get("updated"))
        m["slug"] = re.sub(r"^\d{4}-\d{2}-\d{2}-", "", f.stem)
        m["url"] = f"/{m['section']}/{m['slug']}/"
        m["html"] = MD(body)
        m["minutes"] = max(1, round(len(body.split()) / 230))
        m["wards"] = [w for w in (m.get("wards") or []) if w in WARDS]
        m["tags"] = m.get("tags") or []
        out.append(m)
    if problems:
        raise EditorialError("Articles blocked by editorial checks:\n  " + "\n  ".join(problems))
    out.sort(key=lambda a: a["date"], reverse=True)
    return out


def load_pages():
    pages = {}
    for f in sorted((ROOT / "content" / "pages").glob("*.md")):
        m, body = front(f)
        m["html"] = MD(body)
        m["slug"] = f.stem
        m["updated"] = to_dt(m.get("updated"))
        pages[f.stem] = m
    return pages


def write(path, tpl, **ctx):
    p = DIST / path.strip("/") / "index.html" if path.strip("/") else DIST / "index.html"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(env.get_template(tpl).render(site=SITE, sections=SECTIONS, **ctx), encoding="utf-8")
    return path


def esc(x):
    return str(x).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def build():
    articles = load_articles()
    pages = load_pages()
    if DIST.exists():
        shutil.rmtree(DIST)
    urls = []
    urls.append(write("/", "home.html", page="home", articles=articles,
                      by_section={k: [a for a in articles if a["section"] == k] for k in SECTIONS},
                      wards=WARDS))
    for key, s in SECTIONS.items():
        items = [a for a in articles if a["section"] == key]
        urls.append(write(f"/{key}/", "section.html", page=key, sec=s, items=items,
                          title=s["title"], lede=s["lede"], wards=WARDS))
    # D.C. Council topic page (articles tagged dc-council in any section)
    council = [a for a in articles if "dc-council" in a["tags"]]
    urls.append(write("/politics/dc-council/", "section.html", page="dc-council",
                      sec=SECTIONS["politics"], items=council, title="D.C. Council",
                      lede="Coverage of the Council of the District of Columbia: legislation, hearings, budget and oversight.",
                      wards=WARDS))
    # Ward pages
    for i, w in enumerate(WARDS, 1):
        items = [a for a in articles if w in a["wards"]]
        urls.append(write(f"/neighborhoods/{w}/", "section.html", page="neighborhoods",
                          sec=SECTIONS["neighborhoods"], items=items, title=f"Ward {i}",
                          lede=f"Reporting from Ward {i} of the District of Columbia.",
                          wards=WARDS, current_ward=w))
    for a in articles:
        related = [r for r in articles if r is not a and r["section"] == a["section"]][:4]
        urls.append(write(a["url"], "article.html", page=a["section"], a=a,
                          sec=SECTIONS[a["section"]], related=related,
                          title=a["title"], lede=a["dek"],
                          og_image=a.get("image")))
    for slug, pg in pages.items():
        urls.append(write(f"/{slug}/", "page.html", page=slug, pg=pg,
                          title=pg["title"], lede=pg.get("lede", "")))
    write("/search/", "search.html", page="search", title="Search",
          lede="Search District Times articles.")

    shutil.copytree(ROOT / "static", DIST / "static")
    shutil.copytree(ROOT / "admin", DIST / "admin")
    (DIST / "404.html").write_text(env.get_template("page.html").render(
        site=SITE, sections=SECTIONS, page="404", title="Page not found",
        lede="This address does not exist or has moved.",
        pg={"title": "Page not found", "html": '<p><a href="/">Go to the front page</a> or <a href="/search/">search the site</a>.</p>'}),
        encoding="utf-8")

    base = f"https://{SITE['domain']}"
    (DIST / "search.json").write_text(json.dumps([
        {"t": a["title"], "d": a["dek"], "u": a["url"], "s": SECTIONS[a["section"]]["title"],
         "a": a["author"], "p": fmt_date(a["date"])} for a in articles]), encoding="utf-8")
    items = "".join(
        f"<item><title>{esc(a['title'])}</title><link>{base}{a['url']}</link>"
        f"<guid>{base}{a['url']}</guid><pubDate>{format_datetime(a['date'])}</pubDate>"
        f"<dc:creator>{esc(a['author'])}</dc:creator><description>{esc(a['dek'])}</description></item>"
        for a in articles[:40])
    (DIST / "rss.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?><rss version="2.0" xmlns:dc="http://purl.org/dc/elements/1.1/"><channel>'
        f"<title>District Times</title><link>{base}/</link><description>{esc(SITE['description'])}</description>"
        f"<language>en-us</language>{items}</channel></rss>", encoding="utf-8")
    (DIST / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "".join(f"  <url><loc>{base}{u}</loc></url>\n" for u in urls) + "</urlset>\n", encoding="utf-8")
    pre = SITE["prelaunch"]
    (DIST / "robots.txt").write_text(
        ("User-agent: *\nDisallow: /\n" if pre else "User-agent: *\nAllow: /\nDisallow: /admin/\n")
        + f"Sitemap: {base}/sitemap.xml\n", encoding="utf-8")
    (DIST / "_headers").write_text(
        "/*\n  X-Content-Type-Options: nosniff\n"
        "  Referrer-Policy: strict-origin-when-cross-origin\n"
        "  X-Frame-Options: SAMEORIGIN\n"
        "  Permissions-Policy: camera=(), microphone=(), geolocation=(), interest-cohort=()\n"
        + ("  X-Robots-Tag: noindex\n" if pre else "")
        + "/admin/*\n  X-Robots-Tag: noindex\n"
        + "/static/*\n  Cache-Control: public, max-age=604800\n", encoding="utf-8")
    print(f"✓ dist/ ready: {len(urls)} pages, {len(articles)} articles, prelaunch={pre}")


if __name__ == "__main__":
    try:
        build()
    except EditorialError as e:
        raise SystemExit(str(e))
