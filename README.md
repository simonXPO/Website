# Website
The official XPONext Website

## Tech Stack
- HTML/CSS — kein Framework, kein Build-Step
- Hosted via GitHub Pages

## Development
Dateien direkt bearbeiten, dann pushen — GitHub Pages aktualisiert sich automatisch.
Ausnahme: die generierten Seiten unter `_content/`, siehe unten.

## Generierte Seiten (`_content/`)

Die Leistungs-, Einzugsgebiet-, Kombi- und Blogseiten werden **nicht von Hand gepflegt**.
Ihre Quelle sind die Markdown-Content-Pakete unter `_content/seiten_geo/`:

```
_content/seiten_geo/
├── leistungen/       → /leistungen/*.html
├── einzugsgebiet/    → /einzugsgebiet/*.html + /einzugsgebiet/{ort}/*.html
├── blog/             → /blog/*.html (+ blog/index.html)
└── sitemap_eintraege.md   Liste aller Slugs, Grundlage für sitemap.xml
```

Ändern: die `.md` bearbeiten, dann

```bash
python3 _content/build_geo_pages.py
```

Das Skript schreibt die fertigen `.html` in den Repo-Root. **Das HTML dieser Seiten nicht
direkt bearbeiten** — beim nächsten Lauf wird es überschrieben.

`_content/` beginnt mit einem Unterstrich und wird von GitHub Pages/Jekyll nicht
ausgeliefert. Quelle und Generator lagen bis 14.08.2026 im Repo `XPO_Agentic_Workflow`
(`eigene_website/`, `tools/geo_page_generator/`) und sind hierher gezogen, damit Quelle
und Ausgabe im selben Repo liegen. Erzeugt werden die Content-Pakete vom
`programmatic_seo_geo`-Skill.