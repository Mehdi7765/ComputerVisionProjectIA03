"""
Convertit docs/rapport.md en docs/rapport.pdf.

    python3 docs/generer_rapport_pdf.py

Étapes : Markdown -> HTML (module `markdown`) avec une feuille de style
d'impression, puis HTML -> PDF avec Chrome/Chromium en mode sans fenêtre.
Prérequis : pip install markdown ; Google Chrome ou Chromium installé.
"""
import os
import re
import shutil
import subprocess
import sys

import markdown

DOSSIER = os.path.dirname(os.path.abspath(__file__))
SOURCE = os.path.join(DOSSIER, "rapport.md")
HTML = os.path.join(DOSSIER, "rapport.html")
PDF = os.path.join(DOSSIER, "rapport.pdf")

STYLE = """
@page { size: A4; margin: 18mm 16mm; }
body { font-family: "DejaVu Serif", Georgia, serif; font-size: 10.5pt; line-height: 1.45; color: #111; max-width: 180mm; margin: 0 auto; }
h1 { font-size: 20pt; margin-bottom: 0.2em; }
h2 { font-size: 14pt; margin-top: 1.6em; border-bottom: 1px solid #999; padding-bottom: 2px; page-break-after: avoid; }
h3 { font-size: 11.5pt; margin-top: 1.2em; page-break-after: avoid; }
p, li { text-align: justify; }
table { border-collapse: collapse; width: 100%; font-size: 9pt; margin: 0.6em 0 1em; page-break-inside: avoid; }
th, td { border: 1px solid #bbb; padding: 4px 6px; vertical-align: top; text-align: left; }
th { background: #eee; }
img { max-width: 100%; max-height: 120mm; width: auto; display: block; margin: 0.8em auto 0.3em; page-break-inside: avoid; }
p.legende { text-align: center; font-size: 9pt; color: #444; margin-bottom: 1.2em; }
code { font-family: "DejaVu Sans Mono", monospace; font-size: 9pt; background: #f2f2f2; padding: 0 3px; }
pre { background: #f2f2f2; padding: 8px 10px; font-size: 9pt; overflow-x: auto; }
pre code { background: none; padding: 0; }
hr { border: 0; border-top: 1px solid #999; margin: 1em 0; }
a { color: #1a4d8f; text-decoration: none; }
"""


def main():
    with open(SOURCE, encoding="utf-8") as f:
        corps = markdown.markdown(f.read(), extensions=["tables", "fenced_code", "sane_lists"])
    # Les légendes sont les paragraphes en italique commençant par « Figure »
    corps = re.sub(r"<p><em>(Figure .*?)</em></p>", r'<p class="legende"><em>\1</em></p>', corps)
    with open(HTML, "w", encoding="utf-8") as f:
        f.write(f'<!doctype html><html lang="fr"><head><meta charset="utf-8">'
                f'<title>Rapport IA03</title><style>{STYLE}</style></head><body>{corps}</body></html>')
    print("HTML :", HTML)

    chrome = next((c for c in ("google-chrome", "chromium", "chromium-browser", "chrome")
                   if shutil.which(c)), None)
    if not chrome:
        print("Chrome/Chromium introuvable : ouvrez rapport.html dans un navigateur et imprimez en PDF.")
        return 1
    subprocess.run([chrome, "--headless=new", "--disable-gpu", "--no-sandbox", "--no-pdf-header-footer",
                    f"--print-to-pdf={PDF}", f"file://{HTML}"],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print("PDF  :", PDF, f"({os.path.getsize(PDF) // 1024} Ko)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
