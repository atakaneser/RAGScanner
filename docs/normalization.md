# Document normalization

Normalizasyon parser'ın ürettiği `Document.content` değerini değiştirmez. Ayrı bir
`NormalizationResult` içinde deterministik `normalized_content`, hash, source mapping segmentleri,
annotation, warning ve istatistik üretir. **Normalizasyon sanitizasyon değildir:** şüpheli talimat,
URL, kod veya invisible Unicode sessizce güvenliymiş gibi silinmez; içerik daha sonraki güvenlik
scanner'larının inceleyebileceği biçimde korunur veya görünür marker ve annotation ile temsil edilir.
Render, execute, fetch, network veya subprocess davranışı yoktur.

## Aşama sırası

1. CRLF/CR → LF dönüşümü
2. Unicode normalization
3. Control/invisible karakter gösterimi ve annotation
4. Protected region belirleme
5. Conservative horizontal whitespace, trailing whitespace ve blank-line normalizasyonu
6. PDF high-confidence hyphenated line repair
7. PDF explainable visual-wrap repair
8. Markdown/DOCX/page/table/list/heading structure annotation
9. Repeated header/footer/page-number candidate detection
10. Segment tabanlı source mapping, limit uygulaması ve hash/istatistik üretimi

## Unicode kararı

Varsayılan `NFC`'dir. Bu biçim combining sequence'leri canonical olarak birleştirirken full-width
karakter, circled number veya compatibility glyph gibi güvenlik/semantik açıdan anlamlı farkları
eşitlemez. `NFKC` açık configuration ile kullanılabilir ve değişiklik sayısı kaydedilir; güvenlik
scanner'ı original ile normalized görünümü birlikte değerlendirmelidir. Transliteration yapılmaz;
Türkçe ve diğer diller ile emoji korunur.

NUL, bidi override/isolate, zero-width, replacement ve soft-hyphen karakterleri warning ve
annotation üretir. Varsayılan olarak `<NUL>`, `<BIDI:RLO>`, `<ZWSP>`, `<REPLACEMENT>` ve
`<SOFT_HYPHEN>` gibi deterministik marker kullanılır. Emoji grapheme'lerinde kullanılan ZWJ emoji
görünümünü bozmamak için karakter olarak korunur fakat yine annotation/warning taşır. Original
content her durumda değişmez.

## Whitespace ve yapı

Normal satırlarda trailing whitespace kaldırılır ve yatay whitespace run'ı tek space'e iner.
Varsayılan en fazla iki ardışık boş satır korunur. Markdown fenced/indented code, table-like satır,
preformatted/ASCII diagram görünümündeki satırlar korunur. Markdown render edilmez. DOCX block
separator ve PDF page separator content olarak korunur; structure ayrıca typed annotation'dır.
Heading, list, table cell, section, header/footer ve page boundary metadata'sı scanner/chunker için
kaybolmaz.

## PDF repair heuristikleri

Yalnız `application/pdf` belgelerde çalışır. Visual wrap; önceki satır yeterince uzunsa, terminal
punctuation ile bitmiyorsa ve sonraki satır lowercase başlıyorsa space ile birleştirilir. Heading,
liste, table-like row, URL/path, code-like satır ve page marker sınırında uygulanmaz. Sayfalar arası
birleştirme varsayılan olarak yoktur.

Hyphen repair yalnız en az üç harfli iki parçanın `informa-\ntion` biçimindeki yüksek güvenli
durumunda hyphen/newline'ı kaldırır. URL, path, code, liste ve page sınırlarında uygulanmaz. Her iki
repair sayılır, transformation type taşır ve mapping yaklaşık olarak işaretlenir. Bu kurallar dil
modeli veya sözlük kullanmaz; bazı gerçek wrap'ları kaçırmak, yanlış kelime üretmekten tercih edilir.

## Boilerplate ve mapping

PDF page metadata'sı varsa ilk/son görünür satırlar karşılaştırılır. En az iki sayfada tekrar eden
header/footer ile page-number biçimleri candidate annotation olur. Confidence, occurrence ve pages
kaydedilir; metin varsayılan olarak **asla kaldırılmaz**.

`NormalizationSegment`, normalized range'i original parsed range'e ve `SourceLocation`'a bağlar.
Page, line, section ve DOCX parser block bilgisi mevcut metadata'dan eklenir. Birden fazla original
karakter tek output karakterine dönüşürse, wrap/hyphen onarılırsa veya segment limiti nedeniyle
coalescing yapılırsa `approximate=true` olur. Segment ve annotation sayıları bounded'dır; segment
limiti güvenli coalescing warning'i, annotation limiti deterministic truncation warning'i üretir.
Output-size limiti aşılırsa kısmi/metni sessizce kesmek yerine typed error oluşur.

## Sınırlamalar

- Grapheme-cluster mapping canonical combining sequence dışında per-code-point yaklaşımındadır.
- PDF wrap repair linguistic doğrulama yapmaz ve conservative false-negative üretebilir.
- Boilerplate detection yalnız güvenilir page metadata'sı olan belgelerde çalışır.
- Header/footer candidate olmak removal kararı değildir.
- Segment mapping dönüşümlerde exact karakter eşlemesi yerine bounded original range gösterebilir.
- Normalizer doğrudan chunk üretmez; ayrı [chunking pipeline](chunking.md) onun result/segment
  sözleşmesini tüketir. Normalization annotation'ları ayrı
  [static security scanner](static-security-scanner.md) tarafından incelenebilir. Normalizer finding,
  duplicate, persistence veya report üretmez. Ayrı [duplicate detection](duplicate-detection.md)
  servisi normalized hash/content sözleşmesini salt okunur biçimde tüketir.
