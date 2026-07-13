# Markdown parser

The Markdown parser preserves `.md`/`.markdown` content as original Markdown text. It does not
render HTML, execute embedded code, fetch links/images, or resolve remote resources.

Title precedence is: a bounded scalar `title` in `---` front matter, the first H1 outside a fenced
code block, then the filename stem. Front matter must close within 100 lines/16 KiB; only simple
`key: scalar` values are accepted. Nested YAML, tags, anchors, and object construction are not
supported. Secret-like values are redacted. Heading metadata contains level, text, and line; content
inside code fences is ignored for headings. Markdown and HTML always remain untrusted text.
