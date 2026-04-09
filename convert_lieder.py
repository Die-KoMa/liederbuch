import re
import subprocess
from pathlib import Path
from bisect import bisect_right
import tempfile
from pylatexenc.latex2text import LatexNodes2Text
from pathvalidate import sanitize_filename


BASE_DIR = Path(".")  # Ordner mit main.tex
MAIN_TEX = BASE_DIR / "liederbuch.tex"
SUBFOLDER = BASE_DIR / "lieder"
OUTPUT_DIR = BASE_DIR / "lieder_md"

OUTPUT_DIR.mkdir(exist_ok=True)

def extract_chapters(text):
    """
    Liefert Liste von (position, category)
    """
    pattern = re.compile(
        r'\\addcontentsline\s*\{toc\}\s*\{chapter\}\s*\{([^}]*)\}',
        re.DOTALL
    )

    chapters = []

    for m in pattern.finditer(text):
        pos = m.start()
        category = m.group(1).strip()
        chapters.append((pos, category))

    return chapters


def extract_inputs(text):
    """
    Liefert Liste von (position, input_path)
    """
    pattern = re.compile(
        r'\\input\s*\{([^}]*)\}'
    )

    inputs = []

    for m in pattern.finditer(text):
        pos = m.start()
        path = m.group(1).strip().replace(".tex", "")
        inputs.append((pos, path))

    return inputs


def build_mapping(text):
    chapters = extract_chapters(text)
    inputs = extract_inputs(text)

    # nur Positionen für binäre Suche
    chapter_positions = [pos for pos, _ in chapters]

    mapping = {}

    for input_pos, input_path in inputs:
        # finde Index des letzten Chapters davor
        idx = bisect_right(chapter_positions, input_pos) - 1

        if idx < 0:
            print(f"⚠️ Kein Kapitel für: {input_path}")
            continue

        category = chapters[idx][1]
        mapping[input_path] = category

    return mapping

def parse_main_tex(main_tex_path):
    """
    Extrahiert Mapping: input-file -> Kategorie
    """
    content = main_tex_path.read_text(encoding="utf-8")

    mapping = build_mapping(content)

    return mapping


def convert_tex_to_md(tex_file, output_file):
    """
    Nutzt Pandoc zur Konvertierung
    """
    makros_file = Path("macros.tex")
    subfile = Path(tex_file)
    with tempfile.NamedTemporaryFile("w+", suffix=".tex", delete=False) as tmp:
        tmp.write(r"\documentclass[twoside]{report}")
        tmp.write("\n")
        tmp.write(r"""\newcommand{\lied}[3]{
\newpage
\section*{#1}
\addcontentsline{toc}{section}{#1\\(#2)}
{\vspace*{-2ex} \textit{Melodie: #2} \hspace*{1em} (#3) \vspace*{1ex} }
}
\newcommand{\strophe}[1]{
\begin{verse}
#1
\end{verse}
}
\newcommand{\refrain}[1]{
\begin{verse}
\textsl{Refrain:}\\
#1
\end{verse}
}""")
        tmp.write("\n")
        tmp.write(makros_file.read_text(encoding="utf-8"))
        tmp.write("\n")
        tmp.write(r"\begin{document}")
        tmp.write("\n")
        tmp.write(subfile.read_text(encoding="utf-8"))
        tmp.write("\n")
        tmp.write(r"\end{document}")
        tmp_path = tmp.name
        tmp_test = tmp_path
#    with open(tmp.name, "r") as f:
#        print(f.read())
    subprocess.run([
        "pandoc",
        str(tmp.name),
        "-f", "latex",
#        "-t", "gfm",  # GitHub-Flavored Markdown (gut für Astro)
        "-o", str(output_file)
    ], check=True)









def add_frontmatter(md_file, category):
    content = md_file.read_text(encoding="utf-8")
    begin_trash = content.find(" {")
    title = content[:begin_trash]
    title = LatexNodes2Text().latex_to_text(title)
    
    pattern = re.compile(r'\$(.+?)\$', re.DOTALL)  # minimal match zwischen $...$
    def repl(match):
        formula = match.group(1)
        return LatexNodes2Text().latex_to_text(formula)

    content = pattern.sub(repl, content)

    tmp = content.find("==\n")+3
    frontmatter = f"""---
title: {title}
category: "{category}"
---
"""
    if title == "Analysis kennt auch keine Lösung":
        content = content.replace("ℂ^n","ℂⁿ")
    if title == "Die Mathematik hat festgestellt":
        content = content.replace("ℝ^+", "ℝ⁺")
    if title == "Fachschaftsraum":
        content = content.replace("\n> ℂ", " ℂ")
    if title == "Möbius Theme":
        content = content.replace("ℝ^3", "ℝ³")
    if title == "Topologen auf dem Möbiusband":
        content = content.replace("S^1", "S¹")
    if title == "Was machen wir mit den Erstsemestern":
        content = content.replace("|:", r'<span style="letter-spacing:-0.1em;">\|:</span>')
        content = content.replace(":|", r'<span style="letter-spacing:-0.1em;">:\|</span>')
    if title == "Skandal im ℝ hoch n":
        content = content.replace("a_n", "aₙ")
    md_file.write_text(frontmatter + content[tmp:], encoding="utf-8")
    return title


def main():
    mapping = parse_main_tex(MAIN_TEX)

    for tex_file in SUBFOLDER.rglob("*.tex"):
        rel_path = tex_file.relative_to(BASE_DIR).with_suffix("")
        key = str(rel_path).replace("\\", "/")

        category = mapping.get(key)

        if not category:
            print(f"⚠️ Keine Kategorie gefunden für: {key}")
            continue

        output_file = OUTPUT_DIR / (tex_file.stem + ".md")

        print(f"→ {tex_file} → {output_file} ({category})")

        convert_tex_to_md(tex_file, output_file)
        title = add_frontmatter(output_file, category)
        title = title.replace("?", "")
        title = title.replace("ℝ", "R") # nicht zu viel Unicode in Dateinamen
        title = sanitize_filename(title) # bruteforce anschließend
        output_file.rename(Path("lieder_md") / (title+".md") )


if __name__ == "__main__":
    main()