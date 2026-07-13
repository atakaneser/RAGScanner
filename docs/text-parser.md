# Plain-text parser

TXT parser yalnız `text/plain` içerik kabul eder. Connector'ın seçtiği UTF-8, `utf-8-sig` veya
açık fallback encoding ile decode eder. Replacement strategy warning taşır. Original decoded text
`Document.content` içinde korunur; CRLF/CR yalnız `normalized_content` içinde LF olur. Source
identity/path/time ve 1-based line range korunur. Language `None`; chunking yapılmaz.
