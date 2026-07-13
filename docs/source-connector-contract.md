# SourceConnector sözleşmesi

`SourceConnector`, statik bilgi kaynaklarından belge envanteri, içerik ve değişiklik bilgisi
okuyan vendor-neutral, salt-okunur porttur. Dosya sistemi, OpenWebUI, vektör veritabanı veya
nesne deposu gibi somut entegrasyonlar bu portu daha sonra uygular; hiçbiri ürün çekirdeği
değildir.

## Sınırlar

- `SourceConnector` içerik okur; çalışan bir uygulamaya güvenlik isteği gönderen
  `TargetAdapter` veya iç analiz modeli sağlayan `ModelProvider` değildir.
- Bir LLM endpoint'i tek başına RAG hedefi sayılmaz. RAG etiketi yalnız test edilen uygulama
  gerçekten retrieval yapıyorsa kullanılmalıdır.
- Statik kaynak taraması ile aktif black-box tarama ayrı modlardır.
- Sözleşme async'tir. Somut bağlayıcılar çağıran task'ın iptalini geciktirmeden taşımalı,
  zaman aşımı ve kaynak limitlerini uygulamalıdır.
- `get_content(..., max_bytes)` zorunlu byte bütçesidir. Limit aşıldığında bağlayıcı güvenli
  şekilde `content_too_large` üretmeli veya açıkça `truncated` içerik döndürmelidir.

## Modeller

`SourceDescriptor` ve `SourceCapabilities` kaynağı ve desteklenen davranışları bildirir.
`SourceItem` içerik taşımayan envanter kaydıdır. `SourceContent` byte içeriği, hesaplanmış
boyutu, istenen limiti ve yapılandırılmış uyarıları taşır. `SourceCursor` değeri scanner core
için opaktır. `SourceChange` ekleme, değiştirme, silme, değişmeme ve bilinmeyen değişimleri
temsil eder. `SourceHealth`, dört durumlu sağlık sonucudur. Sayfalama `SourcePage` ve
`SourceChangePage` ile yapılır.

## Hatalar ve gizlilik

`SourceError`, sabit kategorili yapılandırılmış hata ayrıntısı taşır. Hata mesajları,
`repr`, log ve raporlar credential içeremez. Yapılandırma yalnız `env:`, `keychain:`,
`secret-manager:`, `vault:` veya `file-secret:` referanslarıyla gösterilir. İçerik byte'ları
doğası gereği hassas veri içerebilir; bunlar metadata'ya, loglara veya hata mesajlarına
kopyalanmamalıdır. Cursor değerleri ayrıştırılmadan ve raporlanmadan bağlayıcıya geri verilir.

Milestone içindeki `FakeSourceConnector` yalnız test desteğidir: deterministik, bellek içi ve
ağ/dosya sistemi erişimsizdir. Üretim bağlayıcısı değildir.

İlk concrete source implementasyonunun symlink, path, limit, encoding ve snapshot davranışı
[`filesystem-connector.md`](filesystem-connector.md) içindedir.
