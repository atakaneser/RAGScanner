# Duplicate detection

RAGScanner iki tamamen offline ve deterministik duplicate görünümü sağlar. Servisler original belge
ve chunk içeriğini değiştirmez, hiçbir içeriği silmez ve ağ/model/embedding kullanmaz.

## Exact duplicate

`ExactDuplicateScanner`, normalizer çıktısındaki belge metni ile chunk'ların normalized içeriğinin
SHA-256 özetini ayrı kapsamlar halinde gruplar. Boş içerik duplicate sayılmaz. Aynı belgedeki tekrar
eden chunk'lar, belgeler arası aynı chunk'lar ve aynı normalized belge ayrı kategorilerdir.

Her grup kaynak yolu ve item ID ile kararlı biçimde sıralanmış tek bir canonical temsilci içerir.
Canonical burada yalnız raporlama referansıdır; otomatik saklama/silme kararı değildir. Gruplar
tahmini redundant karakter/token miktarını ve bounded, HTML-escaped, secret-masked kanıtı taşır.
Normalizasyon öncesi byte eşitliği bu ilk sürümde ayrıca raporlanmaz.

## Near duplicate

`NearDuplicateScanner`, Unicode token'larından sabit boyutlu shingles üretir ve bounded candidate
bucket'ları içinde Jaccard/containment benzerliği değerlendirir. Varsayılan eşik `0.82`, shingle
boyutu `5` ve minimum karşılaştırma uzunluğu `120` karakterdir. Exact eşleşmeler bu sonuçtan çıkar;
onların sahibi exact scanner'dır.

Boilerplate/page-number annotation'ları yalnız karşılaştırma imzasından çıkarılabilir; original veya
normalized içerikten silinmez. Kısa içerik, boilerplate baskınlığı ve lexical benzerliğin semantik
eşdeğerliği kanıtlamaması nedeniyle near-duplicate bulguları `probable` ve manual-review niteliğindedir.
Türkçe dahil çok dilli metin desteklenir fakat dilsel stemming veya anlam analizi yapılmaz.

## Sınırlar ve determinism

Belge, chunk, grup, finding, shingle, bucket, candidate comparison, evidence ve cooperative çalışma
süresi sınırları typed warning üretir. Sınır nedeniyle değerlendirilmemiş item kimlikleri sonuçta
görünür. Aynı input, config ve scanner sürümü; aynı sıralama, grup/fingerprint, istatistik ve warning
üretir.

CLI örneği:

```bash
uv run ragscanner quality scan ./knowledge --format json
uv run ragscanner quality scan ./knowledge --similarity-threshold 0.9 --fail-on medium
```

`--no-exact-duplicates`, `--no-near-duplicates` ve `--no-chunk-quality` tek tek analizleri kapatır.
En az bir analiz açık kalmalıdır.

