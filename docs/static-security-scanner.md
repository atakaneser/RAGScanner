# Static RAG security scanner

Static scanner belge, normalized metin, chunk, metadata, parser warning ve normalization
annotation'larını tamamen yerel ve deterministik olarak inceler. Çalışan endpoint'e istek gönderen
active scan'den ayrıdır. Static bulgu bir uygulamanın payload'ı gerçekten takip ettiğini kanıtlamaz;
knowledge source içinde riskli içerik bulunduğunu gösterir.

Scanner içerik execute/render etmez, URL takip etmez, network veya subprocess kullanmaz. Encoded
içerik yalnız bounded inspection için en fazla yapılandırılmış byte/depth sınırında decode edilir;
decode edilen veri hiçbir zaman çalıştırılmaz.

## İlk rule pack

`rules/static/` altındaki 1.0.0 JSON paketleri şunları kapsar:

- Prompt injection — İngilizce/Türkçe hierarchy override kalıpları
- System prompt extraction — direct, partial ve bounded encoded disclosure istekleri
- Tool abuse — model/agent bağlamında tool/function/mesaj/kayıt talimatları
- Suspicious commands — agent bağlamında shell, PowerShell, SQL, delete/privilege/download-execute
- Encoded payloads — Base64, ROT13, Unicode escape ve hex içindeki instruction göstergeleri
- Hidden content — invisible/bidi annotation, hidden DOCX warning ve instruction-bearing HTML comment
- Secret exposure — credential assignment, bearer, private key, connection string ve cloud key
- PII — optional email/phone/Türkiye kimlik checksum/card Luhn/IP şekilleri
- Suspicious URLs — userinfo, local/metadata host, IP host, shortener, suspicious scheme ve riskli HTTP
- Metadata poisoning — title/document/chunk/source metadata içindeki override talimatları

PII rule varsayılan kapalıdır ve `--include-pii` ile açılır. Pattern eşleşmesi kişinin kimliğini veya
verinin gerçekten hassas olduğunu kanıtlamaz.

## Deterministik ve heuristic sonuçlar

Severity etkiyi, confidence kanıt gücünü gösterir. Deterministic eşleşme otomatik olarak çalışan RAG
vulnerability'si değildir. Secret veya hidden-content varlığı yüksek güvenle `confirmed` olabilir;
prompt/command/tool/URL/encoded/PII içerik çoğunlukla `probable` kalır. Documentation, security
article, quoted example, canary/no-op ve “do not follow” bağlamı confidence düşürüp `ambiguous`/
manual-review üretir. Teknik command/API dokümantasyonu agent-instruction context yoksa command/tool
finding üretmez.

## Evidence ve secret güvenliği

Evidence rule window ve global maximum ile bounded, HTML-escaped ve common secret pattern'leri için
maskelidir. Private key, bearer, connection string, cloud key ve assignment değeri finding'e ham
olarak yazılmaz. Finding source; normalized/original mapping üzerinden page/line/chunk ile bağlanır.
Rule/scope/matcher/range, decoded-inspection ve fetch/execute=false provenance metadata'dadır.

## Rule formatı ve katkı

Her JSON pack `schema_version`, `pack_id`, `version`, `description`, `rules` içerir. Her rule şunları
tanımlar: stable ID/version, ad/category/description, severity, default confidence, detection type,
scope, restricted matcher, exclusion/context requirement, evidence window, remediation, reference,
enabled, tag/language ve metadata.

Desteklenen matcher'lar: `exact`, `substring_ci`, `regex`, `token_sequence`, `metadata_field`,
`annotation_type`, `warning_code`, `decoded_content`, `entropy_heuristic`, `url_property`,
`secret_pattern`, `pii_pattern`. Python, shell, template veya expression çalıştırılamaz. Regex 512
karakterle sınırlı; backreference, lookaround ve nested/repeated quantifier gibi yüksek riskli
construct'lar loader tarafından reddedilir. Yeni rule TP, FP, boundary, multilingual ve limit
fixture'ları olmadan eklenmemelidir. ID semantiği değişirse rule version artırılmalıdır.

## CLI

```bash
uv run ragscanner security scan ./knowledge --offline
uv run ragscanner security scan file.pdf --format json --category prompt_injection
uv run ragscanner security scan file.docx --rules STATIC-PI-001 --fail-on high
uv run ragscanner security scan ./knowledge --include-pii --max-findings 100
```

Desteklenen girişler `.txt`, `.md`, `.markdown`, text-based `.pdf` ve `.docx` dosyalarıdır. Directory
girdisi desteklenen dosyaları deterministic path sırasıyla işler. `--no-offline` reddedilir. Terminal
ve versioned typed JSON model çıktısı vardır; HTML report yoktur.

## Limitler ve bilinen riskler

Rule/match/finding, decoded byte/depth, evidence, metadata-field, regex-input ve cooperative süre
limitleri vardır. Base64/obfuscation tek başına vulnerability değildir. Entropy ve pattern scanner
adversarial encoding'i eksiksiz yakalayamaz. Context heuristic'leri false positive veya false
negative üretebilir. `not detected` güvenlik garantisi değildir. Static sonuç, active behavior veya
retrieval authorization testi yerine geçmez.
