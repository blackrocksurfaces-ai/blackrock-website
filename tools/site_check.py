#!/usr/bin/env python3
"""Static health check for the BlackRock Surface Co. website.

Run from the repository root:  python3 tools/site_check.py
Prints a JSON report and exits 0 when every check passes, 1 otherwise.
Checks only the files in this repository; the daily task separately checks
the live site and the quote form's email delivery.
"""
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit, unquote

ROOT = Path(__file__).resolve().parent.parent
PHONE = "403-866-2915"
EMAIL = "blackrocksurfaces@gmail.com"
FORM_ACTION = "https://api.web3forms.com/submit"
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}
BIG_IMAGE = 1_500_000  # bytes


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.refs = []      # (tag, attr, value)
        self.stack = []
        self.problems = []
        self.forms = []     # dicts
        self._form = None
        self.has_title = False
        self._in_svg = 0

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "svg":
            self._in_svg += 1
        for key in ("href", "src", "srcset", "poster"):
            if a.get(key):
                vals = [v.strip().split(" ")[0] for v in a[key].split(",")] if key == "srcset" else [a[key]]
                for v in vals:
                    self.refs.append((tag, key, v))
        if tag == "title":
            self.has_title = True
        if tag == "form":
            self._form = {"id": a.get("id"), "action": a.get("action", ""), "fields": {}}
            self.forms.append(self._form)
        if tag == "input" and self._form is not None and a.get("name"):
            self._form["fields"][a["name"]] = a.get("value", "")
        if tag not in VOID and not self._in_svg:
            self.stack.append((tag, self.getpos()[0]))

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in VOID and not self._in_svg and self.stack and self.stack[-1][0] == tag:
            self.stack.pop()

    def handle_endtag(self, tag):
        if tag == "svg":
            self._in_svg = max(0, self._in_svg - 1)
            return
        if self._in_svg or tag in VOID:
            return
        if tag == "form":
            self._form = None
        # pop to the matching tag; anything skipped was left unclosed
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                for t, line in self.stack[i + 1:]:
                    if t not in ("p", "li", "option"):  # HTML allows these to close implicitly
                        self.problems.append(f"<{t}> opened on line {line} is never closed")
                del self.stack[i:]
                return
        self.problems.append(f"stray </{tag}> on line {self.getpos()[0]}")


def local_target(ref):
    if not ref or ref.startswith(("#", "mailto:", "tel:", "sms:", "data:", "javascript:")):
        return None
    parts = urlsplit(ref)
    if parts.scheme or parts.netloc:
        return None
    path = unquote(parts.path)
    if not path:
        return None
    return path


def main():
    checks = []
    pages = sorted(p for p in ROOT.glob("*.html") if not p.name.startswith("google"))
    missing, html_problems, contact_missing, form_problems, big_images = [], [], [], [], []
    versions = {}
    external = set()

    for page in pages:
        text = page.read_text(encoding="utf-8", errors="replace")
        parser = PageParser()
        parser.feed(text)
        parser.close()
        for t, line in parser.stack:
            if t not in ("html", "body", "head", "p", "li", "option"):
                parser.problems.append(f"<{t}> opened on line {line} is never closed")
        if not parser.has_title:
            parser.problems.append("no <title>")
        html_problems += [f"{page.name}: {p}" for p in parser.problems]

        for tag, attr, ref in parser.refs:
            if ref.startswith(("http://", "https://")):
                external.add(ref)
            target = local_target(ref)
            if target is None:
                continue
            fpath = (ROOT / target.lstrip("/")) if target.startswith("/") else (page.parent / target)
            if fpath.is_dir():
                fpath = fpath / "index.html"
            if not fpath.exists():
                missing.append(f"{page.name}: {tag} {attr}=\"{ref}\" points to a file that doesn't exist")
            m = re.search(r"\?v=([\w.-]+)", ref)
            if m:
                versions.setdefault(urlsplit(ref).path, {}).setdefault(m.group(1), []).append(page.name)

        # url(...) in inline styles and <style> blocks (skip template strings built by scripts)
        for ref in re.findall(r"url\(\s*['\"]?([^'\")]+)['\"]?\s*\)", text):
            target = local_target(ref.strip())
            if target and "${" not in target and not (page.parent / target).exists():
                missing.append(f"{page.name}: url({ref}) points to a file that doesn't exist")

        if PHONE not in text:
            contact_missing.append(f"{page.name}: phone number {PHONE} not found")
        if EMAIL not in text and page.name not in ("designer.html", "products.html"):
            contact_missing.append(f"{page.name}: email {EMAIL} not found")

        for f in parser.forms:
            if f["id"] != "quote":
                continue
            if f["action"] != FORM_ACTION:
                form_problems.append(f"{page.name}: quote form sends to {f['action'] or '(nothing)'} instead of {FORM_ACTION}")
            key = f["fields"].get("access_key", "")
            if not re.fullmatch(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", key):
                form_problems.append(f"{page.name}: quote form has no valid Web3Forms access key")

    # url(...) references inside CSS files
    for css in ROOT.glob("*.css"):
        for ref in re.findall(r"url\(\s*['\"]?([^'\")]+)['\"]?\s*\)", css.read_text(errors="replace")):
            target = local_target(ref)
            if target and not (css.parent / target).exists():
                missing.append(f"{css.name}: url({ref}) points to a file that doesn't exist")

    for img in ROOT.glob("img/**/*"):
        if img.is_file() and img.stat().st_size > BIG_IMAGE:
            big_images.append(f"{img.relative_to(ROOT)} is {img.stat().st_size // 1024} KB (slows the page)")
        if img.is_file() and img.stat().st_size == 0:
            missing.append(f"{img.relative_to(ROOT)} is an empty file")

    mismatched = [f"{asset} is loaded with different ?v= versions: " + ", ".join(f"{v} on {len(p)} page(s)" for v, p in vs.items())
                  for asset, vs in versions.items() if len(vs) > 1]

    def add(name, problems, fail_detail=None, pass_detail=""):
        checks.append({"name": name, "result": "fail" if problems else "pass",
                       "detail": "; ".join(problems[:8]) + (f" (+{len(problems) - 8} more)" if len(problems) > 8 else "") if problems else pass_detail})

    add("Links, images, CSS and scripts point to real files", missing, pass_detail=f"{len(pages)} pages scanned")
    add("Page code is well-formed", html_problems)
    add("Phone and email on every page", contact_missing)
    add("Quote form wired to Web3Forms", form_problems, pass_detail="home and Free Quote forms")
    add("Pages load the same version of shared files", mismatched)
    add("Images are a reasonable size", big_images)

    report = {"pages": [p.name for p in pages], "checks": checks, "external_links": sorted(external)}
    print(json.dumps(report, indent=2))
    return 0 if all(c["result"] == "pass" for c in checks) else 1


if __name__ == "__main__":
    sys.exit(main())
