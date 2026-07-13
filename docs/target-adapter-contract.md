# TargetAdapter sözleşmesi

`TargetAdapter`, hedef sahibinin açıkça yetkilendirdiği çalışan bir RAG veya LLM uygulamasına
aktif black-box test isteği hazırlayan ve taşıyan vendor-neutral async porttur. HTTP istemcisi,
somut platform adaptörü ve tarama runner'ı bu milestone kapsamında değildir.

## Rol ayrımı

- `SourceConnector` statik belge, chunk ve metadata okur; çalışan uygulamaya test göndermez.
- `TargetAdapter` yetkili test isteğini taşır; belge kaynağı veya dahili analiz modeli değildir.
- `ModelProvider` yalnız RAGScanner'ın opsiyonel ileri analiz modelidir; taranan hedef değildir.

Bir LLM endpoint'i otomatik olarak RAG sistemi değildir. `retrieval_present` varsayılan olarak
`false` değerindedir ve yalnız hedef retrieval davranışını açıkça bildiriyor veya gösteriyorsa
etkinleştirilir. Citation ve source-document gözlemleri de opsiyoneldir.

## Prepare ve invoke

`prepare_invocation`, test case ve payload'ı normalize edilmiş `TargetInvocation` modeline
dönüştürür ve ağ çağrısı yapmaz. Yetki süresi, safe-mode, capability ve bütçe burada kontrol
edilebilir. `invoke`, gelecekteki somut adaptörlerde timeout ve request budget uygulayarak
hazırlanmış isteği taşır. Adaptör vulnerability değerlendirmez; aynı response farklı test
bağlamlarında farklı anlama gelebileceğinden değerlendirme ayrı response-evaluation katmanına
aittir.

Session oluşturma, model discovery ve cancellation opsiyoneldir. Capability bulunmadığında
adaptör `unsupported` döndürebilir veya sözleşmede tanımlanan boş sonucu verir. Cancellation
desteği hedef capability'sine bağlıdır.

## Güvenlik ve bütçe

Varsayılan `SafetyMode.SAFE` değeridir. Destructive mod açık seçim ve hedefte açık
`destructive_test_mode` capability'si gerektirir. Production için güvensiz payload safe modda
engellenir. Safe tool/function testleri canary, dry-run veya no-op davranışı kullanmalıdır.
Invocation hazırlamak ve göndermek geçerli, süresi dolmamış target-owner authorization ister.

`TargetBudget`; request, süre, hata ve rate-limit delay sınırlarını taşır. Tükenmiş bütçe yeni
hazırlama veya invoke işlemini engeller. Somut adaptörler timeout, rate limit ve iptali uygular.

Credential yalnız harici secret/config referansıyla gösterilir. Authorization/cookie header'ları,
secret query değerleri, response body, citation/source excerpt ve tool/function argümanları
sınırlandırılıp redakte edilmeden serialize edilmez. Transport hatası bir güvenlik bulgusu
değildir.

`FakeTargetAdapter` yalnız test desteğidir; sabit saat ve önceden tanımlı observation kullanır,
bellek içidir ve ağ/dosya sistemi erişimi yapmaz.

İlk concrete implementasyonun template, mapping, secret ve SSRF politikası
[`generic-rest-target-adapter.md`](generic-rest-target-adapter.md) içinde belgelenmiştir.
