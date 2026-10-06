#!/usr/bin/env python3
"""Take a screenshot of terminal output using playwright + brave-origin."""
import sys
import pathlib
import tempfile
import html as html_mod

BRAVE = "/usr/bin/brave-origin"


def terminal_to_html(text: str, title: str = "") -> str:
    escaped = html_mod.escape(text)
    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>{html_mod.escape(title)}</title>
<style>
  body {{ background: #1e1e1e; margin: 0; padding: 16px 20px; }}
  .title {{
    font-family: 'Segoe UI', sans-serif;
    color: #569cd6;
    font-size: 11px;
    margin-bottom: 8px;
  }}
  pre {{
    font-family: 'Cascadia Code', 'Fira Mono', 'Consolas', monospace;
    font-size: 13px;
    color: #d4d4d4;
    background: #1e1e1e;
    margin: 0;
    white-space: pre-wrap;
    word-break: break-all;
    line-height: 1.5;
  }}
</style>
</head>
<body>
<div class="title">{html_mod.escape(title)}</div>
<pre>{escaped}</pre>
</body>
</html>"""


def take_screenshot(text: str, out_path: str, title: str = "") -> None:
    from playwright.sync_api import sync_playwright

    html_content = terminal_to_html(text, title)
    with tempfile.NamedTemporaryFile(suffix=".html", mode="w", delete=False, encoding="utf-8") as f:
        f.write(html_content)
        tmp_html = pathlib.Path(f.name)

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                executable_path=BRAVE,
                args=["--no-sandbox", "--disable-setuid-sandbox"],
            )
            page = browser.new_page(viewport={"width": 920, "height": 600})
            page.goto(f"file://{tmp_html}")
            page.wait_for_timeout(400)
            page.screenshot(path=out_path, full_page=True)
            browser.close()
        print(f"[screenshot] saved → {out_path}")
    finally:
        tmp_html.unlink(missing_ok=True)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: screenshot.py <output.png> [title]", file=sys.stderr)
        sys.exit(1)
    out = sys.argv[1]
    title = sys.argv[2] if len(sys.argv) > 2 else ""
    text = sys.stdin.read()
    take_screenshot(text, out, title)
