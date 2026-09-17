"""MediaWiki helpers shared by IF-wiki extract scripts."""

from __future__ import annotations

import re

from etl.utils.http import get_json

WIKI_API = "https://infinitefusion.fandom.com/api.php"

_WIKILINK_RE  = re.compile(r"\[\[(?:[^\]|]*\|)?([^\]]*)\]\]")
_BOLD_RE      = re.compile(r"'''?([^']+)'''?")
_HTML_TAG_RE  = re.compile(r"<[^>]+>")
_TEMPLATE_RE  = re.compile(r"\{\{[^}]+\}\}")


def fetch_wikitext(page: str) -> str:
    """Fetch raw wikitext of a page via the MediaWiki `parse` API.

    Raises RuntimeError if the API call fails or returns an unexpected shape.
    """
    data = get_json(WIKI_API, params={
        "action": "parse",
        "page":   page,
        "prop":   "wikitext",
        "format": "json",
    })
    if not data or "parse" not in data:
        raise RuntimeError(f"Failed to fetch wiki page: {page}")
    return data["parse"]["wikitext"]["*"]


def clean_wikitext(text: str, *, strip_html: bool = True, strip_templates: bool = False) -> str:
    """Strip common wiki markup. Returns trimmed plain text.

    Always strips:
        - `[[target|display]]` → `display`, `[[target]]` → `target`
        - `'''bold'''` / `''italic''` markers

    Optional (on by default where relevant):
        - `strip_html`      — remove `<tag>` HTML sequences
        - `strip_templates` — remove `{{...}}` template invocations
    """
    text = _WIKILINK_RE.sub(r"\1", text)
    text = _BOLD_RE.sub(r"\1", text)
    if strip_html:
        text = _HTML_TAG_RE.sub("", text)
    if strip_templates:
        text = _TEMPLATE_RE.sub("", text)
    return text.strip()


def _split_template_args(inner: str) -> list[str]:
    """Split template arguments on top-level `|` only.

    Pipes inside `[[link|label]]` and nested `{{...}}` belong to the argument
    and must not split it.
    """
    args: list[str] = []
    buf: list[str] = []
    depth_link = depth_tpl = 0
    i = 0
    while i < len(inner):
        two = inner[i:i + 2]
        if two == "[[":
            depth_link += 1; buf.append(two); i += 2; continue
        if two == "]]" and depth_link:
            depth_link -= 1; buf.append(two); i += 2; continue
        if two == "{{":
            depth_tpl += 1; buf.append(two); i += 2; continue
        if two == "}}" and depth_tpl:
            depth_tpl -= 1; buf.append(two); i += 2; continue
        ch = inner[i]
        if ch == "|" and not depth_link and not depth_tpl:
            args.append("".join(buf)); buf = []
        else:
            buf.append(ch)
        i += 1
    args.append("".join(buf))
    return args


def parse_template_calls(wikitext: str, template: str) -> list[dict[int, str]]:
    """Parse every `{{template|...}}` call into MediaWiki positional params.

    Follows MediaWiki semantics instead of one fixed-arity regex:
      - unnamed args fill params 1, 2, 3... in order;
      - a numeric named arg `7=value` sets param 7 directly (the IF wiki
        started using it to skip empty columns: `|Water|7=Route 119}}`);
      - calls never span past their own closing `}}`, so a short row can't
        swallow the next one.

    Returns one ``{position: raw_value}`` dict per call (values stripped).
    Non-numeric named args are ignored.
    """
    calls: list[dict[int, str]] = []
    opener = "{{" + template
    pos = 0
    while True:
        start = wikitext.find(opener, pos)
        if start == -1:
            break
        i = start + 2
        depth = 1
        while i < len(wikitext) and depth:
            if wikitext.startswith("{{", i):
                depth += 1; i += 2
            elif wikitext.startswith("}}", i):
                depth -= 1; i += 2
            else:
                i += 1
        if depth:           # unterminated call — stop, don't guess
            break
        body = wikitext[start + 2 + len(template):i - 2]
        pos = i

        if not body.lstrip().startswith("|"):
            continue        # e.g. {{PokedexTable/Header}} vs {{PokedexTable/Data
        params: dict[int, str] = {}
        next_pos = 1
        for arg in _split_template_args(body.lstrip()[1:]):
            name, sep, value = arg.partition("=")
            if sep and name.strip().isdigit() and "[[" not in name and "{{" not in name:
                params[int(name.strip())] = value.strip()
            else:
                params[next_pos] = arg.strip()
                next_pos += 1
        calls.append(params)
    return calls
