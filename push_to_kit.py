#!/usr/bin/env python3
"""
push_to_kit.py — take a markdown post and create a draft broadcast in Kit.

Features:
  - Converts markdown to HTML with inline styles (safer for email rendering)
  - Replaces [[IMAGE:name]] placeholders with <img> tags pointing to
    {IMAGE_BASE_URL}/{name}.png
  - Creates a draft. Optional flags publish to the Creator Profile or
    schedule a send.

Usage:
    export KIT_API_KEY="your_v4_api_key_here"
    export IMAGE_BASE_URL="https://raw.githubusercontent.com/you/assets/refs/heads/main"
    python push_to_kit.py my_post.md

Requirements:
    pip install requests markdown
"""

import argparse
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests
import markdown

KIT_API_BASE = "https://api.kit.com/v4"

# [[IMAGE:name]] in markdown becomes {IMAGE_BASE_URL}/{name}.{IMAGE_EXT}.
# Set both via environment.
IMAGE_BASE_URL = os.environ.get("IMAGE_BASE_URL", "").rstrip("/")
IMAGE_EXT = "png"

# --- Inline styles, applied per-element after markdown conversion.
STYLE_BODY = (
    "font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; "
    "font-size: 16px; line-height: 1.6; color: #1f2937; max-width: 640px; "
    "margin: 0 auto; padding: 8px;"
)
STYLE_H2 = (
    "font-size: 22px; font-weight: 600; color: #111827; "
    "margin: 36px 0 12px 0; padding-bottom: 6px; border-bottom: 2px solid #e5e7eb;"
)
STYLE_H3 = "font-size: 18px; font-weight: 600; color: #111827; margin: 28px 0 10px 0;"
STYLE_P = "margin: 0 0 16px 0;"
STYLE_PRE = (
    "background: #0f172a; color: #e2e8f0; padding: 16px; border-radius: 6px; "
    "overflow-x: auto; font-family: ui-monospace, 'SF Mono', Menlo, monospace; "
    "font-size: 13px; line-height: 1.5; margin: 0 0 20px 0;"
)
STYLE_CODE_INLINE = (
    "background: #f1f5f9; color: #0f172a; padding: 2px 6px; border-radius: 3px; "
    "font-family: ui-monospace, 'SF Mono', Menlo, monospace; font-size: 0.92em;"
)
STYLE_BLOCKQUOTE = (
    "background: #fef3c7; border-left: 4px solid #d97706; padding: 12px 16px; "
    "margin: 20px 0; color: #78350f; border-radius: 0 4px 4px 0;"
)
STYLE_UL = "margin: 0 0 20px 0; padding-left: 22px;"
STYLE_LI = "margin: 0 0 6px 0;"
STYLE_HR = "border: none; border-top: 1px solid #e5e7eb; margin: 32px 0;"
STYLE_EM_SMALL = "color: #6b7280; font-size: 14px; font-style: italic;"
STYLE_IMG_WRAPPER = "text-align: center; margin: 24px 0;"
STYLE_IMG = "max-width: 100%; height: auto; border-radius: 4px;"


def inline_image(name: str) -> str:
    """Return an <img> tag referencing the externally hosted PNG.

    The URL is derived from IMAGE_BASE_URL + name + '.' + IMAGE_EXT.
    Upload the file with the matching filename to your image host — no registration.
    """
    if not IMAGE_BASE_URL:
        raise RuntimeError(
            "IMAGE_BASE_URL is not set. Export it before running, e.g.\n"
            "  export IMAGE_BASE_URL='https://example.com/assets'"
        )
    src = f"{IMAGE_BASE_URL}/{name}.{IMAGE_EXT}"
    return (
        f'<div style="{STYLE_IMG_WRAPPER}">'
        f'<img src="{src}" alt="{name} diagram" style="{STYLE_IMG}" />'
        f"</div>"
    )


def apply_inline_styles(html: str) -> str:
    """
    Walk the HTML output from markdown and inject inline style attributes on each element.
    Regex-based because email HTML is simple and we control the source.
    """
    replacements = [
        (r"<h2>", f'<h2 style="{STYLE_H2}">'),
        (r"<h3>", f'<h3 style="{STYLE_H3}">'),
        (r"<p>", f'<p style="{STYLE_P}">'),
        (r"<pre>", f'<pre style="{STYLE_PRE}">'),
        (r"<code>(?!</pre>)", f'<code style="{STYLE_CODE_INLINE}">'),
        (r"<blockquote>", f'<blockquote style="{STYLE_BLOCKQUOTE}">'),
        (r"<ul>", f'<ul style="{STYLE_UL}">'),
        (r"<li>", f'<li style="{STYLE_LI}">'),
        (r"<hr />", f'<hr style="{STYLE_HR}" />'),
        (r"<hr/>", f'<hr style="{STYLE_HR}" />'),
        (r"<hr>", f'<hr style="{STYLE_HR}" />'),
    ]
    out = html
    for pattern, replacement in replacements:
        out = re.sub(pattern, replacement, out)
    # Strip the inline-style from <code> tags that live inside <pre> (don't want double styling)
    out = re.sub(
        r'(<pre[^>]*>)<code style="[^"]*">',
        r"\1<code>",
        out,
    )
    return out


def md_to_html(md_text: str) -> tuple[str, str]:
    """Split markdown into (title, body_html). First H1 is the title."""
    lines = md_text.splitlines()
    title = None
    body_start = 0
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("# "):
            title = stripped[2:].strip()
            body_start = i + 1
            break
    if title is None:
        raise ValueError("No H1 title found in the markdown file.")

    body_md = "\n".join(lines[body_start:]).strip()

    # Replace [[IMAGE:name]] placeholders BEFORE markdown conversion so they
    # end up as raw HTML that markdown leaves alone.
    def image_sub(match):
        return inline_image(match.group(1))

    body_md = re.sub(r"\[\[IMAGE:([a-zA-Z0-9_-]+)\]\]", image_sub, body_md)

    body_html = markdown.markdown(
        body_md,
        extensions=["fenced_code", "tables"],
    )
    body_html = apply_inline_styles(body_html)

    # Wrap everything in a styled container div
    wrapped = f'<div style="{STYLE_BODY}">{body_html}</div>'
    return title, wrapped


def create_draft_broadcast(
    api_key: str,
    subject: str,
    content_html: str,
    description: str | None = None,
) -> dict:
    """POST /v4/broadcasts with no published_at or send_at → draft."""
    url = f"{KIT_API_BASE}/broadcasts"
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "X-Kit-Api-Key": api_key,
    }
    payload = {
        "subject": subject,
        "content": content_html,
    }
    if description:
        payload["description"] = description

    response = requests.post(url, headers=headers, json=payload, timeout=30)
    if response.status_code >= 400:
        print(f"ERROR {response.status_code}: {response.text}", file=sys.stderr)
        response.raise_for_status()
    return response.json()


def update_broadcast(
    api_key: str,
    broadcast_id: int,
    public: bool | None = None,
    send_at: str | None = None,
) -> dict:
    """
    PUT /v4/broadcasts/:id
    - public=True → publish to the Creator Profile newsletter feed
    - send_at=<ISO8601> → schedule the email send at that time
    """
    url = f"{KIT_API_BASE}/broadcasts/{broadcast_id}"
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "X-Kit-Api-Key": api_key,
    }
    payload: dict = {}
    if public is not None:
        payload["public"] = public
    if send_at is not None:
        payload["send_at"] = send_at

    response = requests.put(url, headers=headers, json=payload, timeout=30)
    if response.status_code >= 400:
        print(f"ERROR {response.status_code}: {response.text}", file=sys.stderr)
        response.raise_for_status()
    return response.json()


def main():
    parser = argparse.ArgumentParser(description="Push a markdown post to Kit as a broadcast.")
    parser.add_argument("markdown_file", type=Path, help="Path to the markdown post")
    parser.add_argument("--subject", help="Email subject. Defaults to the post's H1 title.")
    parser.add_argument("--description", help="Internal description (shown in Kit admin)")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be sent; don't call the API. Also writes preview.html.",
    )
    parser.add_argument(
        "--publish",
        action="store_true",
        help="Publish to the Creator Profile public newsletter feed (public=true).",
    )
    parser.add_argument(
        "--send",
        action="store_true",
        help="Schedule the email to actually go out to subscribers "
        "(send_at = now + 2 minutes).",
    )
    args = parser.parse_args()

    api_key = os.environ.get("KIT_API_KEY")
    if not api_key and not args.dry_run:
        print("ERROR: set KIT_API_KEY environment variable.", file=sys.stderr)
        sys.exit(1)

    md_text = args.markdown_file.read_text(encoding="utf-8")
    title, body_html = md_to_html(md_text)
    subject = args.subject or title

    print(f"Title:   {title}")
    print(f"Subject: {subject}")
    print(f"Body:    {len(body_html):,} chars of HTML")

    if args.dry_run:
        preview_path = Path("preview.html")
        preview_path.write_text(body_html, encoding="utf-8")
        print(f"\nWrote preview to {preview_path.resolve()}")
        print("Open that file in a browser to see how the broadcast will look.")
        return

    # Step 1: create the draft
    result = create_draft_broadcast(
        api_key=api_key,
        subject=subject,
        content_html=body_html,
        description=args.description,
    )
    broadcast = result.get("broadcast", result)
    broadcast_id = broadcast.get("id")
    print(f"\n✓ Draft broadcast created. ID: {broadcast_id}")

    # Step 2: publish and/or send if requested
    if args.publish or args.send:
        send_at_iso = None
        if args.send:
            send_at = datetime.now(timezone.utc) + timedelta(minutes=2)
            send_at_iso = send_at.strftime("%Y-%m-%dT%H:%M:%SZ")

        update_broadcast(
            api_key=api_key,
            broadcast_id=broadcast_id,
            public=True if args.publish else None,
            send_at=send_at_iso,
        )
        if args.publish:
            print("✓ Published to Creator Profile newsletter feed (public=true).")
        if args.send:
            print(f"✓ Scheduled to send at {send_at_iso} (~2 minutes from now).")
    else:
        print("Review and send it from: https://app.kit.com/broadcasts")


if __name__ == "__main__":
    main()
