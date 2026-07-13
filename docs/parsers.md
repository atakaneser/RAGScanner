# Document parsers

Parser portu `SourceContent` kabul eder ve valid `Document`, typed warning, parser adı/sürümü,
source item ID ve metadata içeren `ParserResult` döndürür. Parser'lar içerik okumaz, ağ çağrısı
yapmaz, chunk üretmez, render veya execution gerçekleştirmez.

Bu sürüm [plain text](text-parser.md), [Markdown](markdown-parser.md), text-based
[PDF](pdf-parser.md) ve [DOCX](docx-parser.md) destekler. Legacy DOC, DOCM, HTML parser, OCR,
language detection ve chunking yoktur.

Parser'ın original `Document.content` çıktısı sonraki aşamada ayrı
[document normalization pipeline](normalization.md) tarafından işlenebilir. Parser içi minimal
newline işlemleri bu pipeline'ın source-aware, versioned sonucunun yerine geçmez.
