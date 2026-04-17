# kit-newsletter-pipeline

A small Python script for publishing markdown posts to [Kit](https://kit.com) as newsletter broadcasts.

If you found this from my newsletter, welcome. If you found it from somewhere else, the context is [here](https://ciccio.kit.com/posts/how-i-used-claude-and-kit-to-start-this-newsletter). The short version: I write posts in markdown on my laptop and wanted a one-command way to get them into Kit as drafts I can review and send. This is that command.

## What it does

Given a markdown file, the script:

1. Parses the first `# H1` as the post title and email subject
2. Converts the rest of the markdown to HTML with inline styles on every element (headings, code blocks, blockquotes, lists, inline code) so it survives email client rendering
3. Replaces `[[IMAGE:name]]` placeholders with `<img>` tags pointing to hosted URLs configured at the top of the script
4. Calls Kit's V4 API to create a draft broadcast

Optionally, it can also:

- Publish the post to your public Creator Profile feed (`--publish`)
- Schedule the email to go out to your subscribers (`--send`, defaults to now + 2 minutes)

It always creates a draft first. The `--publish` and `--send` flags run as a separate update call after the draft exists, so if anything fails you're left with a recoverable draft rather than a broken partial state.

## What it is not

- A replacement for Kit's broadcast editor. You still open the draft in Kit before sending, because any automated HTML conversion can surprise you, and thirty seconds of visual review catches things a script never will.
- A newsletter platform. Kit is the platform; this is a thin layer that fits my particular writing workflow to it.
- Production-ready for anyone but me. It does what I need. If you want to use it, fork it.

## Requirements

- Python 3.10+
- A Kit account with a V4 API key (Settings → Developer → Create API Key)
- Two pip packages: `requests` and `markdown`

## Quick start

```bash
git clone https://github.com/ciccio-kit/kit-newsletter-pipeline.git
cd kit-newsletter-pipeline

python3 -m venv .venv
source .venv/bin/activate
pip install requests markdown

export KIT_API_KEY="your_v4_api_key_here"
export IMAGE_BASE_URL="https://raw.githubusercontent.com/your-user/your-assets-repo/refs/heads/main"
python push_to_kit.py example_post.md --dry-run
```

The `--dry-run` flag writes `preview.html` instead of calling the API, so you can open the rendered output in a browser before committing to a real API call.

When you're ready to actually push:

```bash
python push_to_kit.py example_post.md
```

You'll get back a broadcast ID and a link to find the draft in Kit.

## Flags

| Flag | What it does |
|---|---|
| `--dry-run` | Render to `preview.html`, don't call the API |
| `--subject "..."` | Override the email subject (defaults to the H1) |
| `--description "..."` | Internal description shown in Kit's admin |
| `--publish` | Set `public: true` on the broadcast so it appears on your Creator Profile |
| `--send` | Schedule the email send for two minutes from now |

## Markdown conventions

The script expects markdown to follow a few light conventions:

- **First `# H1`** is the title and default email subject
- **`## H2` headings** for sections (they render with a subtle border-bottom)
- **Fenced code blocks** render as dark syntax boxes
- **Blockquotes** render as amber callout boxes, good for "worth knowing" asides
- **`[[IMAGE:name]]`** on its own line pulls the image URL for `name` from the `IMAGE_URLS` map at the top of the script and inserts a centered `<img>` tag

## Images

Images in broadcasts need to be hosted somewhere the HTML can reference by URL.

The script uses a convention-based lookup: `[[IMAGE:mesh]]` in your markdown resolves to `{IMAGE_BASE_URL}/mesh.png`. Drop a `mesh.png` into your image host with that filename and it works — no registration, no dict to maintain. Add a new image? Just upload the PNG with the right filename.

Set the base URL via environment variable:

```bash
export IMAGE_BASE_URL="https://raw.githubusercontent.com/your-user/your-assets-repo/refs/heads/main"
```

I use a public GitHub repo for image hosting. Cloudinary, S3, your own server, or any other publicly-fetchable URL works fine — whatever you set as the base URL.

## Things worth knowing

**The HTML is styled inline because email clients strip `<style>` blocks.** Every element gets a `style="..."` attribute injected by a small regex pass after markdown conversion. This is ugly, but it's what email demands.

**The script never sends without you asking.** Default behavior creates a draft. You need to pass `--send` explicitly to schedule an actual email. I'd suggest doing a few test runs before trusting this with a real list.

**Rate limits are not a concern for normal use.** Kit's V4 API allows 120 requests per rolling minute. This script makes at most two per post.

## License

MIT. Do whatever.

## Bugs / feedback

Open an issue on this repo. If I fix it, I'll update the script here.
