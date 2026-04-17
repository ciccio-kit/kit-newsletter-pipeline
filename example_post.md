# Hello from kit-newsletter-pipeline

This is an example post you can use to test the pipeline. Run it with:

```bash
python push_to_kit.py example_post.md --dry-run
```

That will produce a `preview.html` file you can open in a browser to see how the rendered email looks. When you're ready to push a real draft to Kit, drop the `--dry-run` flag.

## What gets rendered

Headings like the one above render with a subtle border underneath. Paragraphs get standard spacing. Inline `code` gets a light grey background. Code blocks get the dark treatment:

```python
def hello():
    print("hello from kit")
```

Blockquotes become amber callout boxes, useful for "worth knowing" asides:

> The script creates a draft by default. You need to pass `--send` to actually email it. No accidental blasts.

Lists work too:

- Markdown source
- Converted to email-safe HTML
- Pushed to Kit as a draft
- Reviewed in the editor
- Sent when it looks right

## Images

To include an image, upload its PNG to your image host (the location set by `IMAGE_BASE_URL` at the top of `push_to_kit.py`) with a matching filename, then reference it in your markdown:

```
[[IMAGE:my_diagram]]
```

The script derives the URL automatically — `[[IMAGE:my_diagram]]` becomes `{IMAGE_BASE_URL}/my_diagram.png`. No registration, no dict to maintain. Just upload the file and write the placeholder.

## That's it

Edit this file, run the script, see what comes out. When you like what you see, write your own post and push it to Kit for real.
