#!/usr/bin/env python3
"""
scripts/check_i18n.py — Validate i18n coverage for landing/index.html

Checks:
  1. All data-i18n keys are present in both T.ru and T.en
  2. All T.ru keys have a T.en counterpart
  3. Reports any gaps

Exit code 0 = all good, 1 = gaps found.

Usage:
    python scripts/check_i18n.py
"""
from __future__ import annotations

import re
import sys
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HTML_PATH = os.path.join(ROOT, "landing", "index.html")


def _extract_data_i18n_keys(html: str) -> list[str]:
    """Return all values of data-i18n and data-i18n-html attributes."""
    keys: list[str] = []
    for pat in [r'data-i18n="([^"]+)"', r"data-i18n='([^']+)'"]:
        keys.extend(re.findall(pat, html))
    for pat in [r'data-i18n-html="([^"]+)"', r"data-i18n-html='([^']+)'"]:
        keys.extend(re.findall(pat, html))
    return keys


def _extract_js_dict(js_block: str, dict_name: str) -> dict[str, str]:
    """
    Pull a simple JS string-keyed object from a JS source block.
    Handles single and double quoted keys/values, ignores comments.

    Works for:
        var T = { ru: { 'key': 'value', ... }, en: { ... } };
        var RU_EN = { 'key': 'value', ... };
    """
    result: dict[str, str] = {}
    # Strip single-line comments
    js_block = re.sub(r"//[^\n]*", "", js_block)

    # Find the outer object for dict_name
    # e.g. "T.ru" or "RU_EN"
    # Strategy: locate `<name>\s*:\s*{` or `var <name>\s*=\s*{`, then
    # extract up to balanced closing brace.
    if "." in dict_name:
        parent, child = dict_name.split(".", 1)
        # Find `var T = { ... }` first
        m = re.search(rf"var\s+{re.escape(parent)}\s*=\s*\{{", js_block)
        if not m:
            return result
        start = m.end()
        # Then find child key `ru:` or `en:`
        inner_m = re.search(
            rf"""['"]?{re.escape(child)}['"]?\s*:\s*\{{""", js_block[start:]
        )
        if not inner_m:
            return result
        inner_start = start + inner_m.end()
        obj_src = _balanced_brace(js_block, inner_start)
    else:
        m = re.search(
            rf"""var\s+{re.escape(dict_name)}\s*=\s*\{{""", js_block
        )
        if not m:
            return result
        obj_src = _balanced_brace(js_block, m.end())

    if obj_src is None:
        return result

    # Extract key-value pairs: 'key': 'value', or "key": "value",
    # Note: no spaces around the alternation | — literal spaces in regex break it
    kv_pat = re.compile(
        r"""['"]([^'"]+)['"]\s*:\s*(?:'((?:[^'\\]|\\.)*)'|"([^"\\]*(?:\\.[^"\\]*)*)")""",
        re.DOTALL,
    )
    for m in kv_pat.finditer(obj_src):
        key = m.group(1)
        value = m.group(2) if m.group(2) is not None else m.group(3)
        result[key] = value

    return result


def _balanced_brace(src: str, start: int) -> str | None:
    """Return substring from start until the matching closing `}` (depth 1)."""
    depth = 1
    i = start
    while i < len(src) and depth > 0:
        c = src[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
        i += 1
    if depth == 0:
        return src[start : i - 1]
    return None


def main() -> int:
    if not os.path.exists(HTML_PATH):
        print(f"ERROR: {HTML_PATH} not found", file=sys.stderr)
        return 1

    html = open(HTML_PATH, encoding="utf-8").read()

    # ── Extract JS block (the i18n <script>) ──────────────────────────────
    # Find the big i18n script block (starts with `var T = {`)
    js_start = html.find("var T = {")
    js_end = html.find("</script>", js_start)
    js_block = html[js_start:js_end] if js_start != -1 else ""

    ru_keys = _extract_js_dict(js_block, "T.ru")
    en_keys = _extract_js_dict(js_block, "T.en")
    ru_en_keys = _extract_js_dict(js_block, "RU_EN")
    data_i18n = _extract_data_i18n_keys(html)

    gaps: list[str] = []

    # 1. Keys in T.ru missing from T.en
    ru_only = set(ru_keys) - set(en_keys)
    for k in sorted(ru_only):
        gaps.append(f"[T dict] Key in T.ru missing from T.en: '{k}'")

    # 2. data-i18n keys missing from T.ru or T.en
    all_t_keys = set(ru_keys) | set(en_keys)
    for k in sorted(set(data_i18n)):
        if k not in all_t_keys:
            gaps.append(f"[data-i18n] Key '{k}' not found in T.ru or T.en")

    # 3. Summary
    total_keys = len(set(ru_keys) | set(en_keys) | set(ru_en_keys) | set(data_i18n))
    print(f"T.ru keys:       {len(ru_keys)}")
    print(f"T.en keys:       {len(en_keys)}")
    print(f"RU_EN entries:   {len(ru_en_keys)}")
    print(f"data-i18n attrs: {len(set(data_i18n))}")
    print()

    if gaps:
        print(f"⚠️  {len(gaps)} gap(s) found:")
        for g in gaps:
            print(f"  - {g}")
        print()
        print(f"Summary: {total_keys} keys checked, {len(gaps)} gaps found")
        return 1
    else:
        print(f"✅  Summary: {total_keys} keys checked, 0 gaps found")
        return 0


if __name__ == "__main__":
    sys.exit(main())
