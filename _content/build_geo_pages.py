#!/usr/bin/env python3
"""
Baut aus den Markdown-Content-Paketen in _content/seiten_geo/ die echten HTML-Seiten
im Repo-Root. Teil des programmatic_seo_geo-Workflows.

Quelle und Ausgabe liegen seit 2026-08-14 im selben Repo (vorher lag die Quelle im
XPO_Agentic_Workflow-Repo unter eigene_website/seiten_geo/). Die Markdown-Dateien sind
die Quelle der Wahrheit fuer diese Seiten: HTML nicht direkt bearbeiten, sondern die
.md aendern und dieses Skript neu laufen lassen. Beides muss committet bleiben, sonst
gehen die Quellen bei einem Sitzungs-/Umgebungs-Reset spurlos verloren
(siehe _content/seiten_geo/sitemap_eintraege.md, Vorfall 2026-08-03).

Aufruf aus dem Repo-Root oder von ueberall: python3 _content/build_geo_pages.py
"""
import re, glob, os, json

_HERE = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(_HERE, "seiten_geo")
OUT_DIR = os.path.dirname(_HERE)

REDIRECT = {
    "/leistungen/zeitfresser-workshop.html": "/effizienz.html",
}

ORT_LABEL = {"bonn": "Bonn", "koeln": "Köln"}

FEATURED_SLUG = "/blog/sichtbarkeit-chatgpt-google-ai-overviews-architekturbuero.html"

CLUSTER_META = {
    "Sichtbarkeit bei Bauherren & Kommunen": {
        "tag": "Sichtbarkeit",
        "desc": "Wie Architekturbüros online gefunden werden, von Google-Profil bis GEO.",
    },
    "Zeitfresser & Prozessoptimierung": {
        "tag": "Zeitfresser",
        "desc": "Wo im Büroalltag Zeit verloren geht, und wie ihr sie zurückgewinnt.",
    },
    "Kosten von Online-Marketing für Architekturbüros": {
        "tag": "Kosten",
        "desc": "Realistische Größenordnungen für Website, SEO und Google Ads.",
    },
}

def reading_minutes(capsule, paragraphs):
    text = capsule + " " + " ".join(c for k, c in paragraphs if k == "p")
    words = len(re.findall(r"\w+", text))
    return max(2, round(words / 200))

def excerpt(capsule, max_len=150):
    plain = re.sub(r'\*\*(.+?)\*\*', r'\1', capsule)
    plain = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', plain)
    if len(plain) <= max_len:
        return plain
    cut = plain[:max_len].rsplit(" ", 1)[0]
    return cut + "…"

def parse_md(path):
    text = open(path, encoding="utf-8").read()
    m = re.match(r'^---\n(.*?)\n---\n(.*)$', text, re.S)
    fm_raw, body = m.group(1), m.group(2).strip()
    import yaml
    fm = yaml.safe_load(fm_raw)
    return fm, body

def md_inline(s, redirect_map):
    s = s.replace("&", "&amp;")
    def link_sub(mm):
        label, url = mm.group(1), mm.group(2)
        url = redirect_map.get(url, url)
        return f'<a href="{url}">{label}</a>'
    s = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', link_sub, s)
    s = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', s)
    return s

def render_table(block, redirect_map):
    lines = [l for l in block.strip().split("\n") if l.strip()]
    rows = [[c.strip() for c in l.strip().strip("|").split("|")] for l in lines]
    header, sep, *body_rows = rows
    out = ['<div class="table-wrap"><table class="content-table"><thead><tr>']
    for h in header:
        out.append(f"<th>{md_inline(h, redirect_map)}</th>")
    out.append("</tr></thead><tbody>")
    for r in body_rows:
        out.append("<tr>" + "".join(f"<td>{md_inline(c, redirect_map)}</td>" for c in r) + "</tr>")
    out.append("</tbody></table></div>")
    return "\n".join(out)

def render_body(body, redirect_map):
    blocks = re.split(r'\n\n+', body.strip())
    capsule = None
    paragraphs = []
    sources = None
    for b in blocks:
        b = b.strip()
        if not b:
            continue
        if b.startswith("|"):
            paragraphs.append(("table", b))
            continue
        if re.match(r'^\*\*Quelle', b):
            sources = b
            continue
        if capsule is None:
            capsule = b
        else:
            paragraphs.append(("p", b))
    return capsule, paragraphs, sources

def parse_citations(src):
    if not src:
        return []
    m = re.match(r'^\*\*([^:]+):\*\*\s*(.*)$', src, re.S)
    if not m:
        return []
    rest = m.group(2)
    citations = []
    for name, url in re.findall(r'\[([^\]]+)\]\(([^)]+)\)', rest):
        citations.append({"@type": "CreativeWork", "name": name.strip(), "url": url.strip()})
    return citations

def slugify_ort_leistung(slug):
    parts = slug.strip("/").replace(".html", "").split("/")
    return parts

def load_all():
    files = sorted(glob.glob(os.path.join(SRC_DIR, "**/*.html.md"), recursive=True))
    entries = {}
    for f in files:
        fm, body = parse_md(f)
        entries[fm["slug"]] = (fm, body, f)
    return entries

def build_link_labels(entries):
    labels = {"/": "Startseite", "/leistungen.html": "Leistungen", "/effizienz.html": "Zeitfresser & Prozessoptimierung"}
    for slug, (fm, body, f) in entries.items():
        target = REDIRECT.get(slug, slug)
        labels[target] = fm.get("h1") or fm.get("title")
    return labels

def breadcrumb_for(slug, fm):
    parts = slugify_ort_leistung(slug)
    crumbs = [("/", "Home")]
    if parts[0] == "leistungen":
        crumbs.append(("/leistungen.html", "Leistungen"))
        crumbs.append((None, fm["h1"]))
    elif parts[0] == "einzugsgebiet":
        ort = parts[1]
        if len(parts) == 2:
            crumbs.append((None, ORT_LABEL.get(ort, ort.title())))
        else:
            crumbs.append((f"/einzugsgebiet/{ort}.html", ORT_LABEL.get(ort, ort.title())))
            crumbs.append((None, fm["h1"]))
    elif parts[0] == "blog":
        crumbs.append(("/blog/index.html", "Blog"))
        crumbs.append((None, fm["h1"]))
    return crumbs

def schema_for(fm, slug, canonical, breadcrumbs, citations=None):
    seitentyp = fm["seitentyp"]
    blocks = []
    if seitentyp == "leistungsseite":
        blocks.append({
            "@context": "https://schema.org", "@type": "Service",
            "serviceType": fm["h1"], "name": fm["h1"], "description": fm["meta_description"], "url": canonical,
            "provider": {"@type": "ProfessionalService", "name": "XPO Next GbR", "url": "https://www.xponext.de"},
            "areaServed": {"@type": "Country", "name": "Deutschland"},
        })
    elif seitentyp in ("einzugsgebiet-haupt", "einzugsgebiet-leistung"):
        ort = slugify_ort_leistung(slug)[1]
        blocks.append({
            "@context": "https://schema.org", "@type": "ProfessionalService",
            "name": "XPO Next GbR", "description": fm["meta_description"], "url": canonical,
            "address": {"@type": "PostalAddress", "streetAddress": "Adrianstraße 88", "addressLocality": "Bonn", "postalCode": "53227", "addressCountry": "DE"},
            "areaServed": {"@type": "City", "name": ORT_LABEL.get(ort, ort.title())},
        })
    elif seitentyp == "blogartikel":
        blocks.append({
            "@context": "https://schema.org", "@type": "Article",
            "headline": fm["h1"], "description": fm["meta_description"], "url": canonical, "datePublished": "2026-07-26",
            "author": {"@type": "Organization", "name": "XPO Next GbR", "url": "https://www.xponext.de"},
            "publisher": {"@type": "Organization", "name": "XPO Next GbR", "url": "https://www.xponext.de"},
        })
    if citations and blocks:
        blocks[0]["citation"] = citations
    items = []
    pos = 1
    for href, label in breadcrumbs:
        item = {"@type": "ListItem", "position": pos, "name": label}
        if href:
            item["item"] = "https://www.xponext.de" + (href if href != "/" else "/")
        items.append(item)
        pos += 1
    blocks.append({"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": items})
    return blocks

PAGE_CSS = """
    @font-face { font-family: 'Inter'; src: url('/assets/fonts/inter-variable.woff2') format('woff2'); font-weight: 100 900; font-style: normal; font-display: swap; }
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: 'Inter', -apple-system, sans-serif; background: #fff; color: #0D0D0D; -webkit-font-smoothing: antialiased; }
    a { text-decoration: none; transition: opacity 0.15s, color 0.15s; }
    nav { display: flex; align-items: center; justify-content: space-between; padding: 0.7rem 2.5%; background: #0D0D0D; position: sticky; top: 0; z-index: 100; border-bottom: 1px solid #1A1A1A; }
    .nav-logo { display: inline-flex; align-items: center; gap: 0.55rem; font-size: 1.15rem; font-weight: 800; color: #fff; letter-spacing: -0.01em; }
    .nav-logo .nav-wm { color: #fff; font-weight: 800; }
    .nav-logo .nav-wm em { color: #4CAF7E; font-weight: 400; font-style: normal; }
    .nav-links { display: flex; gap: 1.6rem; align-items: center; }
    .nav-links a { color: #9CA3AF; font-size: 0.9rem; font-weight: 500; }
    .nav-links a:hover, .nav-links a.active { color: #fff; opacity: 1; }
    .nav-dd { position: relative; }
    .nav-dd-trigger { display: inline-flex; align-items: center; gap: 4px; color: #9CA3AF; font-size: 0.9rem; font-weight: 500; }
    .nav-dd-trigger:hover, .nav-dd-trigger.active { color: #fff; opacity: 1; }
    .nav-dd-arrow { font-size: 0.6rem; transition: transform 0.15s; }
    .nav-dd:hover .nav-dd-arrow { transform: rotate(180deg); }
    .nav-dd-menu { display: none; flex-direction: column; gap: 0.15rem; position: absolute; top: 100%; left: 50%; transform: translateX(-50%); background: #fff; border: 1px solid #E5E7EB; border-top: none; border-radius: 0 0 12px 12px; padding: 0.9rem 0.5rem 0.5rem; min-width: 220px; z-index: 200; }
    .nav-dd:hover .nav-dd-menu, .nav-dd:focus-within .nav-dd-menu { display: flex; }
    .nav-dd-menu a { color: #374151; opacity: 1; font-size: 0.88rem; font-weight: 500; padding: 0.55rem 0.75rem; border-radius: 8px; white-space: nowrap; }
    .nav-dd-menu a:hover { background: #F9FAFB; color: #0D0D0D; }
    .nav-cta { background: #1B6B45; color: #fff !important; padding: 0.55rem 1.25rem; border-radius: 7px; font-weight: 600; font-size: 0.9rem; }
    .nav-cta:hover { background: #134D32 !important; opacity: 1 !important; }
    .breadcrumb-bar { padding: 0.9rem 5%; background: #fff; border-bottom: 1px solid #F3F4F6; font-size: 0.85rem; color: #6B7280; }
    .breadcrumb-bar a { color: #6B7280; }
    .breadcrumb-bar a:hover { color: #1B6B45; opacity: 1; }
    .breadcrumb-bar .sep { margin: 0 0.4rem; color: #D1D5DB; }
    .breadcrumb-bar .current { color: #0D0D0D; font-weight: 600; }
    .page-hero { padding: 3.5rem 5% 3rem; background: #F9FAFB; border-bottom: 1px solid #E5E7EB; text-align: center; }
    .ps-badge { display: inline-flex; align-items: center; gap: 6px; background: #E8F0EB; color: #1B6B45; padding: 0.35rem 0.9rem; border-radius: 99px; font-size: 0.85rem; font-weight: 600; margin-bottom: 1.2rem; }
    .page-hero h1 { font-size: clamp(1.8rem, 4vw, 2.6rem); font-weight: 900; line-height: 1.15; color: #0D0D0D; margin: 0 auto 0; letter-spacing: -0.02em; max-width: 780px; }
    .content-wrap { padding: 3.5rem 5%; }
    .content-inner { max-width: 760px; margin: 0 auto; }
    .capsule-block { background: #F9FAFB; border-left: 4px solid #1B6B45; border-radius: 10px; padding: 1.4rem 1.7rem; margin-bottom: 2rem; font-size: 1.05rem; line-height: 1.75; color: #0D0D0D; overflow-wrap: break-word; word-break: break-word; }
    .body-text p { font-size: 1rem; line-height: 1.85; color: #374151; margin-bottom: 1.4rem; overflow-wrap: break-word; word-break: break-word; }
    .body-text a { color: #1B6B45; font-weight: 600; border-bottom: 1px solid rgba(27,107,69,0.3); }
    .body-text a:hover { opacity: 1; border-bottom-color: #1B6B45; }
    .body-text strong { color: #0D0D0D; }
    .table-wrap { overflow-x: auto; margin-bottom: 1.6rem; }
    .content-table { width: 100%; border-collapse: collapse; font-size: 0.92rem; }
    .content-table th, .content-table td { border: 1px solid #E5E7EB; padding: 0.65rem 0.9rem; text-align: left; }
    .content-table th { background: #F9FAFB; font-weight: 700; color: #0D0D0D; }
    .content-table td a { color: #1B6B45; font-weight: 600; }
    .related-links { margin-top: 3rem; }
    .related-links h3 { font-size: 1.1rem; font-weight: 800; color: #0D0D0D; margin-bottom: 1rem; }
    .related-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 0.75rem; }
    .related-card { display: block; padding: 1rem 1.1rem; background: #fff; border: 1px solid #E5E7EB; border-radius: 12px; font-size: 0.9rem; font-weight: 600; color: #0D0D0D; }
    .related-card:hover { border-color: #1B6B45; opacity: 1; color: #1B6B45; }
    .cta-block { padding: 4rem 5%; background: #F9FAFB; border-top: 1px solid #E5E7EB; text-align: center; }
    .cta-block h2 { font-size: clamp(1.4rem, 3vw, 1.9rem); font-weight: 800; color: #0D0D0D; margin-bottom: 0.8rem; letter-spacing: -0.01em; }
    .cta-block h2 em { font-style: normal; color: #1B6B45; }
    .cta-block p { color: #4B5563; font-size: 1rem; margin-bottom: 1.8rem; }
    .btn-primary { background: #1B6B45; color: #fff; padding: 0.9rem 1.8rem; border-radius: 8px; font-weight: 700; font-size: 0.95rem; display: inline-flex; align-items: center; gap: 6px; }
    .btn-primary:hover { background: #134D32; opacity: 1; }
    footer { padding: 2rem 5%; border-top: 1px solid #E5E7EB; display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 2rem; }
    .footer-logo { font-size: 1rem; font-weight: 800; color: #0D0D0D; }
    .footer-logo span { color: #1B6B45; }
    .footer-copy { color: #9CA3AF; font-size: 0.82rem; margin-top: 0.7rem; }
    .footer-col { display: flex; flex-direction: column; gap: 0.6rem; min-width: 130px; }
    .footer-col-title { font-size: 0.75rem; font-weight: 700; color: #9CA3AF; letter-spacing: 0.07em; text-transform: uppercase; margin-bottom: 0.2rem; }
    .footer-col a { color: #6B7280; font-size: 0.88rem; }
    .footer-col a:hover { color: #0D0D0D; opacity: 1; }
    .cookie-reopen { background: none; border: 0; padding: 0; font: inherit; cursor: pointer; color: #6B7280; font-size: 0.88rem; text-align: left; }
    .cookie-reopen:hover { color: #0D0D0D; }
    .blog-wrap { padding: 0 5% 4rem; }
    .blog-inner { max-width: 1100px; margin: 0 auto; }
    .featured-card { display: block; background: #F9FAFB; border: 1px solid #E5E7EB; border-left: 4px solid #1B6B45; border-radius: 14px; padding: 2rem 2.2rem; margin-bottom: 3.5rem; text-decoration: none; }
    .featured-tag { display: inline-block; background: #E8F0EB; color: #134D32; padding: 0.3rem 0.8rem; border-radius: 99px; font-size: 0.78rem; font-weight: 700; letter-spacing: 0.02em; margin-bottom: 1rem; }
    .featured-card h2 { font-size: clamp(1.25rem, 2.5vw, 1.6rem); font-weight: 800; color: #0D0D0D; line-height: 1.3; margin-bottom: 0.6rem; letter-spacing: -0.01em; }
    .featured-card:hover h2 { color: #1B6B45; }
    .featured-card p { font-size: 1rem; color: #4B5563; line-height: 1.65; margin-bottom: 0.9rem; }
    .featured-meta { font-size: 0.82rem; color: #9CA3AF; font-weight: 600; }
    .cluster-section { margin-top: 3.2rem; }
    .cluster-head { display: flex; align-items: baseline; gap: 0.6rem; border-bottom: 2px solid #0D0D0D; padding-bottom: 0.7rem; margin-bottom: 0.5rem; }
    .cluster-head h2 { font-size: 1.15rem; font-weight: 800; color: #0D0D0D; letter-spacing: -0.01em; }
    .cluster-count { color: #9CA3AF; font-size: 0.82rem; font-weight: 600; }
    .cluster-desc { color: #6B7280; font-size: 0.92rem; line-height: 1.5; margin-bottom: 1.5rem; }
    .article-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 1.2rem; }
    .article-card { display: flex; flex-direction: column; gap: 0.55rem; background: #fff; border: 1px solid #E5E7EB; border-left: 3px solid #1B6B45; border-radius: 12px; padding: 1.3rem 1.4rem; text-decoration: none; }
    .article-card:hover { border-color: #1B6B45; opacity: 1; box-shadow: 0 6px 18px rgba(13,13,13,0.06); }
    .article-tag { display: inline-flex; background: #E8F0EB; color: #134D32; padding: 0.2rem 0.65rem; border-radius: 99px; font-size: 0.72rem; font-weight: 700; letter-spacing: 0.02em; align-self: flex-start; }
    .article-card h3 { font-size: 0.98rem; font-weight: 700; color: #0D0D0D; line-height: 1.4; }
    .article-card:hover h3 { color: #1B6B45; }
    .article-card p { font-size: 0.85rem; color: #6B7280; line-height: 1.55; flex-grow: 1; }
    .article-meta { font-size: 0.78rem; color: #9CA3AF; font-weight: 600; }
    @media (max-width: 680px) {
      .nav-links a:not(.nav-cta) { display: none; }
      .nav-dd { display: none; }
      footer { flex-direction: column; }
    }
"""

NAV = """
  <nav>
    <a href="/index.html" class="nav-logo">
      <svg width="30" height="30" viewBox="0 0 120 120" fill="none" xmlns="http://www.w3.org/2000/svg"><rect width="120" height="120" rx="28" fill="#1B6B45"/><line x1="32" y1="88" x2="32" y2="32" stroke="#fff" stroke-width="7" stroke-linecap="round"/><line x1="88" y1="32" x2="88" y2="88" stroke="#fff" stroke-width="7" stroke-linecap="round"/><line x1="32" y1="32" x2="88" y2="88" stroke="#fff" stroke-width="7" stroke-linecap="round"/><line x1="32" y1="88" x2="88" y2="32" stroke="#fff" stroke-width="7" stroke-linecap="round" opacity="0.3"/></svg>
      <span class="nav-wm">XPO<em>Next</em></span>
    </a>
    <div class="nav-links">
      <div class="nav-dd">
        <a href="/leistungen.html" class="nav-dd-trigger">Leistungen <span class="nav-dd-arrow">▾</span></a>
        <div class="nav-dd-menu">
          <a href="/leistungen.html">Online-Präsenz (Übersicht)</a>
          <a href="/leistungen/seo.html">Lokales SEO</a>
          <a href="/leistungen/website-erstellung.html">Website-Erstellung</a>
          <a href="/leistungen/geo.html">GEO</a>
          <a href="/leistungen/google-ads.html">Google Ads &amp; AI Ads</a>
          <a href="/effizienz.html">Zeitfresser & Prozessoptimierung</a>
        </div>
      </div>
      <a href="/blog/index.html">Blog</a>
      <a href="/index.html#vorteile">Vorteile</a>
      <a href="/index.html#faq">FAQ</a>
      <a href="/ueber-uns.html">Über uns</a>
      <a href="/website-check.html">Website-Check</a>
      <a href="/index.html#kontakt" class="nav-cta">Termin buchen</a>
    </div>
  </nav>
"""

FOOTER = """
  <footer>
    <div class="footer-col">
      <div class="footer-logo">XPO<span>Next</span></div>
      <p style="color:#9CA3AF;font-size:0.85rem;line-height:1.6;max-width:220px;">Mehr Sichtbarkeit für Architekturbüros – aus einer Hand.</p>
      <p class="footer-copy">© 2026 XPONext GbR</p>
    </div>
    <div class="footer-col">
      <div class="footer-col-title">Seiten</div>
      <a href="/leistungen.html">Leistungen</a>
      <a href="/blog/index.html">Blog</a>
      <a href="/effizienz.html">Zeitfresser & Prozessoptimierung</a>
      <a href="/index.html#vorteile">Vorteile</a>
      <a href="/index.html#faq">FAQ</a>
      <a href="/ueber-uns.html">Über uns</a>
    </div>
    <div class="footer-col">
      <div class="footer-col-title">Einzugsgebiete</div>
      <a href="/einzugsgebiet/bonn.html">Bonn</a>
      <a href="/einzugsgebiet/koeln.html">Köln</a>
    </div>
    <div class="footer-col">
      <div class="footer-col-title">Rechtliches</div>
      <a href="/impressum.html">Impressum</a>
      <a href="/datenschutz.html">Datenschutz</a>
      <a href="/agb.html">AGB</a>
      <button data-action="cookie-settings" class="cookie-reopen">Cookie-Einstellungen</button>
    </div>
    <div class="footer-col">
      <div class="footer-col-title">Kontakt</div>
      <address style="font-style:normal;color:#6B7280;font-size:0.88rem;line-height:1.6;">XPO Next GbR<br>Adrianstraße 88<br>53227 Bonn</address>
      <a href="mailto:info@xponext.de" style="color:#6B7280;font-size:0.88rem;">info@xponext.de</a>
    </div>
  </footer>

  <div class="cookie-banner" id="cookieBanner" role="dialog" aria-live="polite" aria-label="Cookie-Einstellungen" aria-hidden="true">
    <div class="cookie-banner__card">
      <div class="cookie-banner__head">
        <div class="cookie-banner__icon" aria-hidden="true">🍪</div>
        <div>
          <h2 class="cookie-banner__title">Cookies & Datenschutz</h2>
          <p class="cookie-banner__text">Wir nutzen technisch notwendige Cookies, damit die Website funktioniert. Mit deiner Zustimmung setzen wir zusätzlich Google Analytics und Microsoft Clarity ein, um die Nutzung anonymisiert zu analysieren. Details in unserer <a href="/datenschutz.html">Datenschutzerklärung</a>.</p>
        </div>
      </div>
      <div class="cookie-banner__options" id="cookieOptions" hidden>
        <label class="cookie-option">
          <div>
            <div class="cookie-option__title">Notwendig</div>
            <div class="cookie-option__desc">Speichert deine Cookie-Einstellungen im Browser. Kein Tracking.</div>
          </div>
          <span class="cookie-option__always">Immer aktiv</span>
        </label>
        <label class="cookie-option">
          <div>
            <div class="cookie-option__title">Statistik</div>
            <div class="cookie-option__desc">Anonyme Nutzungsanalyse via Google Analytics 4 und Microsoft Clarity.</div>
          </div>
          <input type="checkbox" id="consentStatistics" class="cookie-switch">
          <span class="cookie-switch__slider" aria-hidden="true"></span>
        </label>
      </div>
      <div class="cookie-banner__actions">
        <button class="cookie-btn cookie-btn--ghost" id="cookieEssentials" type="button">Nur notwendige</button>
        <button class="cookie-btn cookie-btn--ghost" id="cookieSettingsToggle" type="button">Einstellungen</button>
        <button class="cookie-btn cookie-btn--primary" id="cookieAcceptAll" type="button">Alle akzeptieren</button>
        <button class="cookie-btn cookie-btn--primary" id="cookieSaveCustom" type="button" hidden>Auswahl speichern</button>
      </div>
    </div>
  </div>
  <script src="/js/cookie-banner.js"></script>
"""

def badge_for(fm, slug):
    parts = slugify_ort_leistung(slug)
    if parts[0] == "leistungen":
        return "Leistung"
    if parts[0] == "einzugsgebiet":
        return "Einzugsgebiet"
    if parts[0] == "blog":
        return fm.get('cluster', 'Blog')
    return "XPONext"

def head(title, meta_desc, canonical, schemas):
    schema_scripts = "\n".join(
        f'<script type="application/ld+json">{json.dumps(s, ensure_ascii=False, indent=2)}</script>'
        for s in schemas
    )
    return f"""<!DOCTYPE html>
<html lang="de">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
  <meta name="description" content="{meta_desc}">
  <meta name="robots" content="index, follow">
  <link rel="canonical" href="{canonical}">
  <link rel="icon" type="image/png" sizes="32x32" href="/favicon.png">
  <link rel="icon" type="image/svg+xml" href="/favicon.svg">
  <link rel="stylesheet" href="/css/cookie-banner.css">
  <script async src="https://www.googletagmanager.com/gtag/js?id=G-S0KYC5QEKH"></script>
  <script>
    window.dataLayer = window.dataLayer || [];
    function gtag(){{dataLayer.push(arguments);}}
    gtag('consent', 'default', {{
      'analytics_storage': 'denied', 'ad_storage': 'denied', 'ad_user_data': 'denied', 'ad_personalization': 'denied'
    }});
    gtag('js', new Date());
    gtag('config', 'G-S0KYC5QEKH', {{ 'anonymize_ip': true }});
  </script>
  {schema_scripts}
  <style>{PAGE_CSS}</style>
</head>
<body>
{NAV}"""

def build_page(fm, body, slug, labels):
    canonical = "https://www.xponext.de" + slug
    crumbs = breadcrumb_for(slug, fm)
    capsule, paragraphs, sources = render_body(body, REDIRECT)
    citations = parse_citations(sources)
    schemas = schema_for(fm, slug, canonical, crumbs, citations)

    crumb_html = []
    for href, label in crumbs:
        if href:
            crumb_html.append(f'<a href="{href}">{label}</a>')
        else:
            crumb_html.append(f'<span class="current">{label}</span>')
    breadcrumb_html = f'<span class="sep">/</span>'.join(crumb_html)

    body_parts = [f'<div class="capsule-block">{md_inline(capsule, REDIRECT)}</div>']
    body_parts.append('<div class="body-text">')
    for kind, content in paragraphs:
        if kind == "table":
            body_parts.append(render_table(content, REDIRECT))
        else:
            body_parts.append(f"<p>{md_inline(content, REDIRECT)}</p>")
    body_parts.append("</div>")

    related_cards = []
    for link in fm.get("interne_links", []):
        target = REDIRECT.get(link, link)
        label = labels.get(target, target)
        related_cards.append(f'<a class="related-card" href="{target}">{label}</a>')
    related_html = ""
    if related_cards:
        related_html = f'''<div class="related-links"><h3>Das könnte dich auch interessieren</h3><div class="related-grid">{"".join(related_cards)}</div></div>'''

    badge = badge_for(fm, slug)
    html = head(fm["title"], fm["meta_description"], canonical, schemas)
    html += f"""
  <div class="breadcrumb-bar">{breadcrumb_html}</div>

  <div class="page-hero">
    <div class="ps-badge">{badge}</div>
    <h1>{fm["h1"]}</h1>
  </div>

  <div class="content-wrap">
    <div class="content-inner">
      {''.join(body_parts)}
      {related_html}
    </div>
  </div>

  <div class="cta-block">
    <h2>Bereit für <em>mehr Sichtbarkeit?</em></h2>
    <p>Kostenloses Erstgespräch – wir schauen uns deine Situation an und zeigen, was möglich ist.</p>
    <a href="/index.html#kontakt" class="btn-primary">Kostenloses Erstgespräch →</a>
  </div>
{FOOTER}
</body>
</html>
"""
    return html

def build_blog_index(entries, labels):
    clusters = {}
    for slug, (fm, body, f) in entries.items():
        if fm["seitentyp"] != "blogartikel":
            continue
        clusters.setdefault(fm["cluster"], []).append((slug, fm))
    order = [
        "Sichtbarkeit bei Bauherren & Kommunen",
        "Zeitfresser & Prozessoptimierung",
        "Kosten von Online-Marketing für Architekturbüros",
    ]
    canonical = "https://www.xponext.de/blog/index.html"
    title = "Blog für Architekturbüros | XPONext"
    meta_desc = "Praxiswissen für Architekturbüros: Sichtbarkeit bei Bauherren, Zeitfresser im Büroalltag und Kosten von Online-Marketing – recherchiert mit echten Quellen."
    schemas = [
        {"@context": "https://schema.org", "@type": "CollectionPage", "name": title, "description": meta_desc, "url": canonical},
        {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Home", "item": "https://www.xponext.de/"},
            {"@type": "ListItem", "position": 2, "name": "Blog"},
        ]},
    ]
    html = head(title, meta_desc, canonical, schemas)
    html += """
  <div class="breadcrumb-bar"><a href="/index.html">Home</a><span class="sep">/</span><span class="current">Blog</span></div>

  <div class="page-hero">
    <div class="ps-badge">Blog</div>
    <h1>Praxiswissen für Architekturbüros</h1>
  </div>

  <div class="blog-wrap">
    <div class="blog-inner">
"""
    featured = entries.get(FEATURED_SLUG)
    if featured:
        ffm, fbody, _ = featured
        fcapsule, fparagraphs, _ = render_body(fbody, REDIRECT)
        fmins = reading_minutes(fcapsule, fparagraphs)
        ftag = CLUSTER_META.get(ffm["cluster"], {}).get("tag", ffm["cluster"])
        html += f'''      <a class="featured-card" href="{FEATURED_SLUG}">
        <div class="featured-tag">Empfohlen · {ftag}</div>
        <h2>{ffm["h1"]}</h2>
        <p>{excerpt(fcapsule, 220)}</p>
        <div class="featured-meta">{fmins} Min Lesezeit</div>
      </a>
'''
    for cluster in order:
        articles = [(s, f) for s, f in clusters.get(cluster, []) if s != FEATURED_SLUG]
        meta = CLUSTER_META.get(cluster, {"tag": cluster, "desc": ""})
        total = len(clusters.get(cluster, []))
        html += f'''      <div class="cluster-section">
        <div class="cluster-head"><h2>{cluster}</h2><span class="cluster-count">{total} Artikel</span></div>
        <p class="cluster-desc">{meta["desc"]}</p>
        <div class="article-grid">
'''
        for slug, fm in sorted(articles, key=lambda x: x[1]["h1"]):
            _, abody, _ = entries[slug]
            acapsule, aparagraphs, _ = render_body(abody, REDIRECT)
            amins = reading_minutes(acapsule, aparagraphs)
            html += f'''          <a class="article-card" href="{slug}">
            <span class="article-tag">{meta["tag"]}</span>
            <h3>{fm["h1"]}</h3>
            <p>{excerpt(acapsule, 105)}</p>
            <div class="article-meta">{amins} Min Lesezeit</div>
          </a>
'''
        html += "        </div>\n      </div>\n"
    html += """    </div>
  </div>

  <div class="cta-block">
    <h2>Bereit für <em>mehr Sichtbarkeit?</em></h2>
    <p>Kostenloses Erstgespräch – wir schauen uns deine Situation an und zeigen, was möglich ist.</p>
    <a href="/index.html#kontakt" class="btn-primary">Kostenloses Erstgespräch →</a>
  </div>
"""
    html += FOOTER + "\n</body>\n</html>\n"
    return html

def main():
    entries = load_all()
    labels = build_link_labels(entries)
    written = []
    skipped = []
    for slug, (fm, body, srcfile) in entries.items():
        if slug in REDIRECT:
            skipped.append((slug, REDIRECT[slug]))
            continue
        out_path = os.path.join(OUT_DIR, slug.lstrip("/"))
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        html_out = build_page(fm, body, slug, labels)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(html_out)
        written.append(out_path)

    blog_index_path = os.path.join(OUT_DIR, "blog", "index.html")
    with open(blog_index_path, "w", encoding="utf-8") as f:
        f.write(build_blog_index(entries, labels))
    written.append(blog_index_path)

    print(f"Geschrieben: {len(written)} Dateien (inkl. blog/index.html)")
    print(f"Übersprungen (Redirect statt neuer Datei): {len(skipped)}")
    for s, t in skipped:
        print(" -", s, "->", t)

if __name__ == "__main__":
    main()
