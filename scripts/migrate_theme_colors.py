"""
Migration des couleurs hardcodées rgb() → classes Tailwind CSS variables.

Applique un mapping exhaustif sur tous les fichiers .tsx de frontend/app/ et
frontend/components/ pour que le mode clair fonctionne.

Usage :
  python scripts/migrate_theme_colors.py [--dry-run]
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "frontend"

# ── Mapping hex → CSS variable name ──────────────────────────────────────────
# Couvre les valeurs utilisées dans les inline style={{ }} et les classes [#hex]
HEX_MAP: dict[str, str] = {
    # Surfaces
    "#090c1a": "if-bg",
    "#0d1020": "if-bg",
    "#0e0e16": "if-deep",
    "#0f1225": "if-surface",
    "#111428": "if-card",
    "#111524": "if-card",
    "#13162e": "if-card",
    "#191926": "if-elevated",
    "#1e1e2a": "if-input",
    # Bordures
    "#1a1d35": "if-border-lo",
    "#1e2240": "if-border",
    "#252850": "if-border",
    "#323246": "if-border-mid",
    "#2d3260": "if-border-hi",
    "#3a3f65": "if-border-hi",
    "#3d4170": "if-border-hi",
    # Variantes card/surface supplémentaires
    "#191925": "if-card",
    "#16192e": "if-card",
    "#13162a": "if-card",
    # Texte
    "#4a4f75": "if-text-lo",
    "#6b7199": "if-muted",
    "#8b91c8": "if-text-lo",
    "#8c8ca0": "if-text-xs",
    "#9aa0c0": "if-text-xs",
    "#a0a0b4": "if-text-lo",
    "#c8cbe8": "if-text-dim",
    "#c8cbf0": "if-text-dim",
    "#dcdcff": "if-text-hi",
    "#e1e4ff": "if-text",
    "#e8e8ff": "if-text-hi",
}

# ── Mapping rgb() → classe Tailwind CSS variable ──────────────────────────────
#
# Règle : on remplace le pattern Tailwind arbitraire  prefix-[rgb(r,g,b)]
# ainsi que les valeurs dans style={{ }} inline.
#
# L'ordre compte : les valeurs les plus spécifiques en premier.

# Surfaces / fonds
BG_MAP = {
    # if-surface  (#0f1225 = rgb(15,18,37))
    "rgb(15,15,20)":  "if-surface",
    "rgb(15,15,22)":  "if-surface",
    # if-deep  (#0e0e16 = rgb(14,14,22))
    "rgb(14,14,22)":  "if-deep",
    # if-card  (#111428 = rgb(17,20,40))
    "rgb(17,20,40)":  "if-card",
    "rgb(18,18,26)":  "if-card",
    "rgb(18,18,28)":  "if-card",
    "rgb(20,20,28)":  "if-card",
    "rgb(20,20,30)":  "if-card",
    "rgb(20,20,32)":  "if-card",
    # if-elevated  (#191926 = rgb(25,25,38))
    "rgb(22,22,32)":  "if-elevated",
    "rgb(22,22,35)":  "if-elevated",
    "rgb(25,25,35)":  "if-elevated",
    "rgb(25,25,38)":  "if-elevated",
    "rgb(28,28,40)":  "if-elevated",
    # if-input  (#1e1e2a = rgb(30,30,42))
    "rgb(30,30,42)":  "if-input",
    "rgb(30,30,45)":  "if-input",
    "rgb(32,32,46)":  "if-input",
    "rgb(35,35,48)":  "if-input",
    "rgb(35,35,50)":  "if-input",
    "rgb(38,38,52)":  "if-input",
    "rgb(40,40,55)":  "if-input",
    # Légèrement au-dessus de if-input → if-elevated
    "rgb(42,42,58)":  "if-elevated",
    "rgb(45,45,62)":  "if-elevated",
    "rgb(50,50,68)":  "if-elevated",
    "rgb(50,50,70)":  "if-elevated",
    "rgb(55,55,75)":  "if-elevated",
    "rgb(60,60,80)":  "if-elevated",
    # Variantes supplémentaires non couvertes au premier passage
    "rgb(10,10,18)":  "if-surface",
    "rgb(20,20,35)":  "if-card",
    "rgb(30,30,45)":  "if-input",
    "rgb(35,35,48)":  "if-input",
    "rgb(35,35,50)":  "if-input",
    "rgb(40,40,55)":  "if-input",
    "rgb(45,45,65)":  "if-elevated",
    "rgb(50,50,70)":  "if-elevated",
    "rgb(70,70,90)":  "if-elevated",
}

# Textes
TEXT_MAP = {
    # if-text  (#e1e4ff = rgb(225,228,255))
    "rgb(225,228,255)": "if-text",
    "rgb(230,233,255)": "if-text",
    # if-text-hi  (#dcdcff = rgb(220,220,255))
    "rgb(220,220,255)": "if-text-hi",
    "rgb(215,215,255)": "if-text-hi",
    # if-text-dim  (#c8cbf0 = rgb(200,203,240))
    "rgb(200,200,240)": "if-text-dim",
    "rgb(200,200,230)": "if-text-dim",
    "rgb(200,200,220)": "if-text-dim",
    "rgb(205,205,235)": "if-text-dim",
    "rgb(210,210,245)": "if-text-dim",
    # if-text-lo  (#a0a0b4 = rgb(160,160,180))
    "rgb(180,180,210)": "if-text-lo",
    "rgb(175,175,205)": "if-text-lo",
    "rgb(170,170,200)": "if-text-lo",
    "rgb(165,165,195)": "if-text-lo",
    "rgb(160,160,180)": "if-text-lo",
    "rgb(155,155,185)": "if-text-lo",
    # if-text-xs  (#78788c = rgb(120,120,140))
    "rgb(140,140,170)": "if-text-xs",
    "rgb(135,135,165)": "if-text-xs",
    "rgb(130,130,160)": "if-text-xs",
    "rgb(125,125,150)": "if-text-xs",
    "rgb(120,120,140)": "if-text-xs",
    "rgb(115,115,135)": "if-text-xs",
    "rgb(110,110,130)": "if-text-xs",
    # if-muted  (#6b7199 = rgb(107,113,153))
    "rgb(107,113,153)": "if-muted",
    "rgb(105,105,135)": "if-muted",
    "rgb(100,100,140)": "if-muted",
    "rgb(100,100,130)": "if-muted",
    "rgb(100,100,120)": "if-muted",
    "rgb(95,95,125)":   "if-muted",
    "rgb(90,90,120)":   "if-muted",
    "rgb(90,90,110)":   "if-muted",
    "rgb(85,85,115)":   "if-muted",
    "rgb(80,80,110)":   "if-muted",
    "rgb(80,80,100)":   "if-muted",
    "rgb(75,75,105)":   "if-muted",
    "rgb(70,70,100)":   "if-muted",
    "rgb(70,70,90)":    "if-muted",
    # Variantes supplémentaires
    "rgb(120,120,150)": "if-text-xs",
    "rgb(140,140,165)": "if-text-xs",
    "rgb(160,160,200)": "if-text-lo",
    "rgb(180,180,200)": "if-text-lo",
}

# Bordures
BORDER_MAP = {
    # if-border-mid  (#323246 = rgb(50,50,70))
    "rgb(50,50,70)":    "if-border-mid",
    "rgb(48,48,68)":    "if-border-mid",
    "rgb(55,55,75)":    "if-border-mid",
    # if-border  (#1e2240 = rgb(30,34,64))
    "rgb(40,40,60)":    "if-border",
    "rgb(40,42,65)":    "if-border",
    # if-border-lo  (#1a1d35 = rgb(26,29,53))
    "rgb(30,30,50)":    "if-border-lo",
    "rgb(28,28,48)":    "if-border-lo",
}

# ── Regex patterns ────────────────────────────────────────────────────────────

def build_tailwind_pattern(rgb_val: str, prefix: str) -> tuple[str, str]:
    """Retourne (pattern, replacement) pour un usage Tailwind className."""
    escaped = re.escape(rgb_val)
    # Cas : prefix-[rgb(r,g,b)]  ou  hover:prefix-[rgb(r,g,b)]  etc.
    var_name = (BG_MAP | TEXT_MAP | BORDER_MAP).get(rgb_val, "")
    if not var_name:
        return "", ""
    pat = rf'(?<!\w){re.escape(prefix)}-\[{escaped}\]'
    rep = f"{prefix}-{var_name}"
    return pat, rep


def replace_inline_style_bg(content: str, rgb_val: str, var_name: str) -> str:
    """Remplace background: 'rgb(...)' dans les style={{ }} inline."""
    escaped = re.escape(rgb_val)
    # "rgb(...)" ou 'rgb(...)' dans style=
    for quote in ['"', "'"]:
        content = re.sub(
            rf'background:\s*{quote}{escaped}{quote}',
            f'background: {quote}var(--color-{var_name}){quote}',
            content,
        )
    # background-color: rgb(...)
    content = re.sub(
        rf'backgroundColor:\s*["\']?{escaped}["\']?',
        f"backgroundColor: 'var(--color-{var_name})'",
        content,
    )
    return content


def replace_inline_style_color(content: str, rgb_val: str, var_name: str) -> str:
    """Remplace color: 'rgb(...)' dans les style={{ }} inline."""
    escaped = re.escape(rgb_val)
    for quote in ['"', "'"]:
        content = re.sub(
            rf'color:\s*{quote}{escaped}{quote}',
            f'color: {quote}var(--color-{var_name}){quote}',
            content,
        )
    return content


def replace_hex_colors(content: str) -> tuple[str, int]:
    """Remplace les hex codes dans les classes Tailwind et les inline styles."""
    changes = 0

    for hex_val, var_name in HEX_MAP.items():
        # 1. Tailwind arbitrary: bg-[#hex], text-[#hex], border-[#hex], etc.
        for prefix in ["bg", "text", "border", "hover:bg", "hover:text",
                       "hover:border", "ring", "from", "to", "via",
                       "divide", "fill", "stroke"]:
            pat = rf'{re.escape(prefix)}-\[{re.escape(hex_val)}\]'
            rep = f"{prefix}-{var_name}"
            new = re.sub(pat, rep, content, flags=re.IGNORECASE)
            if new != content:
                changes += len(re.findall(pat, content, re.IGNORECASE))
                content = new

        # 2. Inline style values: background: "#hex", color: "#hex", etc.
        #    Matches both single and double quotes.
        for quote in ['"', "'"]:
            q = re.escape(quote)
            escaped = re.escape(hex_val)
            # background / backgroundColor
            for prop in ["background", "backgroundColor"]:
                pat = rf'{re.escape(prop)}:\s*{q}{escaped}{q}'
                rep = f'{prop}: {quote}var(--color-{var_name}){quote}'
                new = re.sub(pat, rep, content, flags=re.IGNORECASE)
                if new != content:
                    changes += 1
                    content = new
            # color
            pat = rf'color:\s*{q}{escaped}{q}'
            rep = f'color: {quote}var(--color-{var_name}){quote}'
            new = re.sub(pat, rep, content, flags=re.IGNORECASE)
            if new != content:
                changes += 1
                content = new
            # borderColor / border (inline)
            for prop in ["borderColor", "borderTopColor", "borderBottomColor",
                         "borderLeftColor", "borderRightColor", "outlineColor"]:
                pat = rf'{re.escape(prop)}:\s*{q}{escaped}{q}'
                rep = f'{prop}: {quote}var(--color-{var_name}){quote}'
                new = re.sub(pat, rep, content, flags=re.IGNORECASE)
                if new != content:
                    changes += 1
                    content = new
            # fill / stroke
            for prop in ["fill", "stroke"]:
                pat = rf'{re.escape(prop)}:\s*{q}{escaped}{q}'
                rep = f'{prop}: {quote}var(--color-{var_name}){quote}'
                new = re.sub(pat, rep, content, flags=re.IGNORECASE)
                if new != content:
                    changes += 1
                    content = new

        # 3. Hex in border shorthand: border: "1px solid #hex"
        for quote in ['"', "'"]:
            q = re.escape(quote)
            escaped = re.escape(hex_val)
            pat = rf'(border:\s*{q}[^{quote}]*?){escaped}({q})'
            rep = rf'\1var(--color-{var_name})\2'
            new = re.sub(pat, rep, content)
            if new != content:
                changes += 1
                content = new

    # 4. Template literals: `1px solid ${cond ? "#accent" : "#hex"}`
    #    and JS event handler assignments: style.borderColor = "#hex"
    for hex_val, var_name in HEX_MAP.items():
        escaped = re.escape(hex_val)
        css_var  = f"var(--color-{var_name})"

        # Template literal with hex: "#hex"} or : "#hex"`
        for delim in ['}"', "`"]:
            pat = rf':\s*{re.escape(chr(34))}{escaped}{re.escape(chr(34))}{re.escape(delim)}'
            rep = f': "{css_var}"{delim}'
            new = re.sub(pat, rep, content)
            if new != content:
                changes += 1
                content = new

        # JS assignment: style.borderColor = "#hex" or style.background = "#hex"
        pat = rf'(style\.\w+)\s*=\s*{re.escape(chr(34))}{escaped}{re.escape(chr(34))}'
        rep = rf'\1 = "{css_var}"'
        new = re.sub(pat, rep, content)
        if new != content:
            changes += 1
            content = new


    return content, changes


def migrate_file(path: Path, dry_run: bool = False) -> int:
    original = path.read_text(encoding="utf-8")
    content  = original
    changes  = 0

    # ── Tailwind className replacements ───────────────────────────────────────
    for rgb_val, var_name in BG_MAP.items():
        for prefix in ["bg", "hover:bg", "focus:bg", "from", "to", "via",
                       "border", "hover:border", "divide", "ring", "outline"]:
            pat, rep = build_tailwind_pattern(rgb_val, prefix)
            if not pat:
                continue
            new = re.sub(pat, rep, content)
            if new != content:
                changes += content.count(f"{prefix}-[{rgb_val}]")
                content = new

    for rgb_val, var_name in TEXT_MAP.items():
        for prefix in ["text", "hover:text", "focus:text", "placeholder:text"]:
            pat, rep = build_tailwind_pattern(rgb_val, prefix)
            if not pat:
                continue
            new = re.sub(pat, rep, content)
            if new != content:
                changes += content.count(f"{prefix}-[{rgb_val}]")
                content = new

    for rgb_val, var_name in BORDER_MAP.items():
        for prefix in ["border", "hover:border", "ring", "outline"]:
            pat, rep = build_tailwind_pattern(rgb_val, prefix)
            if not pat:
                continue
            new = re.sub(pat, rep, content)
            if new != content:
                changes += content.count(f"{prefix}-[{rgb_val}]")
                content = new

    # ── Inline style replacements ─────────────────────────────────────────────
    for rgb_val, var_name in BG_MAP.items():
        new = replace_inline_style_bg(content, rgb_val, var_name)
        if new != content:
            changes += 1
            content = new

    for rgb_val, var_name in TEXT_MAP.items():
        new = replace_inline_style_color(content, rgb_val, var_name)
        if new != content:
            changes += 1
            content = new

    # ── Hex colors ────────────────────────────────────────────────────────────
    content, hex_changes = replace_hex_colors(content)
    changes += hex_changes

    if content != original:
        if not dry_run:
            path.write_text(content, encoding="utf-8")
        print(f"  {'[DRY]' if dry_run else '✓'} {path.relative_to(ROOT.parent)} ({changes} remplacement(s))")
    return changes


def main() -> None:
    dry_run = "--dry-run" in sys.argv
    if dry_run:
        print("Mode dry-run — aucune écriture\n")

    targets = [
        *ROOT.glob("app/**/*.tsx"),
        *ROOT.glob("components/**/*.tsx"),
    ]

    total   = 0
    touched = 0
    for path in sorted(targets):
        n = migrate_file(path, dry_run=dry_run)
        if n:
            touched += 1
            total   += n

    print(f"\n{'Simulation' if dry_run else 'Migration'} terminée — {touched} fichier(s), {total} remplacement(s)")


if __name__ == "__main__":
    main()
