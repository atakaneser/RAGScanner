# DOCX parser

İlk DOCX parser `SourceContent` içindeki `.docx`/DOCX MIME verisini tamamen bellek içinde,
render etmeden işler. `python-docx` 1.2 kullanır ve body için paragraph/table sırasını koruyan
`iter_inner_content()` akışını temel alır. Paragraph, heading, list item, table cell, section/page
break, header ve footer ayrı, sıralı bloklardır; her blok birleşik metindeki başlangıç/bitiş
offset'ini taşır. Core properties sınırlı ve secret-maskeli metadata olarak alınır. Başlık seçimi
core title → H1 → ilk görünür body paragraph → dosya adı sırasındadır.

## Güvenlik modeli

- ZIP açılmadan önce file size; ardından entry count, toplam decompressed byte, XML part ve
  compression-ratio limitleri uygulanır. Unsafe path ve encrypted entry fail-closed reddedilir.
- XML güvenli `defusedxml` incelemesinden geçer. Dış ilişki/template/image ve hyperlink hedefleri
  yalnız bounded metadata olarak kaydedilir; hiçbir hedef fetch edilmez.
- Macro, OLE/embedded object, comments, tracked changes ve hidden text warning üretir. Macro/OLE
  çalıştırılmaz; embedded object çıkarılmaz. Deleted ve hidden run görünür metne alınmaz.
- Parser subprocess, shell, network, render, OCR, chunking veya scanner çağırmaz. Timeout işlem
  sınırlarında cooperative'dir; process-level hard kill değildir.
- Block separator metinde geçerse collision oluşmaması için deterministik biçimde escape edilir.

## Destek ve sınırlamalar

`.doc`, `.docm`, OLE/encrypted ve malformed paketler typed parser error ile reddedilir. Standart ve
yerelleştirilmiş heading style'ları, outline level, doğrudan Word numbering ve yaygın list style'ları
algılanır. Table cell koordinatları, merged sinyali ve repeated header row tutulur; nested table
recursive çıkarılmaz ve warning üretir. Header/footer body akışından sonra section/region kimliğiyle
verilir; bu nedenle Word'ün sayfa bazlı görsel sırası yeniden oluşturulmaz. Fields, drawings,
text-box, footnote/endnote, comment body ve pixel-perfect layout fidelity garanti edilmez.

Parser güvenlik taraması değildir. Üretilen görünür metin ve yapı metadata'sı sonraki milestone'larda
normalization, chunking ve static RAG Security Scan tarafından tüketilecektir.

Referanslar: [python-docx Document API](https://python-docx.readthedocs.io/en/latest/api/document.html),
[tables](https://python-docx.readthedocs.io/en/latest/user/tables.html),
[sections](https://python-docx.readthedocs.io/en/stable/api/section.html).
