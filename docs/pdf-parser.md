# PDF parser

The parser performs typed `%PDF-` signature, readable page-count, and zero-page preflight checks.
The `invalid_signature`, `malformed`, `zero_pages`, `encrypted`, `limit_exceeded`, and `timeout`
categories are preserved in pipeline error codes and remediation metadata. Raw PyMuPDF messages
such as `Invalid number of pages` do not cross the reporting boundary. An image-based PDF with
valid pages produces `likely_scanned_pdf` and `no_extractable_text` warnings instead of a malformed
file error; OCR is not performed yet.

İlk PDF parser yalnız text-based PDF extraction için PyMuPDF kullanır. `SourceContent` memory
buffer olarak açılır; file path, link, attachment veya remote resource PyMuPDF'ye verilmez. OCR,
rendering ve password denemesi yoktur. PyMuPDF'nin güncel `Document.needs_pass`,
`embfile_count`, catalog/xref ve page text/image/link inventory API'leri kullanılır.

## Page mapping

Tek `Document` oluşturulur. Sayfalar sırayla birleştirilir ve araya sabit ASCII
`PAGE_SEPARATOR` konur. Extracted text aynı separator'ı içerirse reserved marker escape edilir.
Her page metadata kaydı 1-based page number, text start/end offset, separator start/end,
character count, empty flag, image count ve warning code'ları taşır. Offset slice yalnız sayfa
metnini döndürür; separator dahil değildir. Böylece ileride chunk → page eşlemesi recoverable'dır.

## Warning ve OCR sınırı

`empty_page`, `no_extractable_text`, `likely_scanned_pdf`, `partially_scanned_pdf`,
`extraction_failed_page`, replacement/control/printable/fragmentation/whitespace/garbled,
page-number-only ve repeated-boilerplate sinyalleri finding değil structured parser warning'idir.
Image-only veya düşük-text PDF yalnız “likely” olarak işaretlenir. OCR yapılmaz.

Metadata title, author, subject, keywords, creator, producer, creation/modification date ve page
count ile sınırlıdır. Değerler control-normalized, secret-redacted ve bounded'dır. Malformed date
warning üretir. Title metadata yoksa filename stem kullanılır.

## Güvenlik ve limitler

- File size, page count, page başı/total extracted character ve metadata field limitleri vardır.
- Password-required PDF `encrypted` parser error ile reddedilir; brute force yoktur.
- Catalog/annotation/link inventory JavaScript, launch/automatic action, link ve embedded-file
  warning'i üretir; hiçbirini execute/follow/extract etmez.
- Attachment içeriği okunmaz; yalnız count kontrol edilir.
- Ağ ve subprocess çağrısı yoktur; raw içerik loglanmaz.
- Timeout page sınırlarında cooperative elapsed-time kontrolüdür. Native PDF open veya tek page
  extraction çağrısını process-level preemption ile kesemez; hostile-input isolation ileride ayrı
  worker/process hardening gerektirir.

PyMuPDF text extraction reading order ve font encoding kalitesine bağlıdır. Complex layout,
tables, unusual fonts, damaged content ve scanned documents düşük kaliteli veya eksik metin
üretebilir. Parser OCR-quality score veya factual security finding üretmez.

Referans: [PyMuPDF Document API](https://pymupdf.readthedocs.io/en/latest/document.html),
[PyMuPDF TextPage API](https://pymupdf.readthedocs.io/en/latest/textpage.html).
