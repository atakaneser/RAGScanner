# Plain-text parser

The TXT parser accepts only `text/plain` content. It uses the UTF-8, `utf-8-sig`, or explicit
fallback encoding selected by the connector. Replacement decoding produces a warning. Original
decoded text remains in `Document.content`; CRLF/CR is converted to LF only in
`normalized_content`. Source identity, path, timestamp, and one-based line range are preserved.
Language remains `None`, and the parser does not perform chunking.
