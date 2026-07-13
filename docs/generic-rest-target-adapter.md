# Generic REST Target Adapter

İlk concrete `TargetAdapter`, kullanıcı tarafından yapılandırılan JSON tabanlı REST hedeflerini
provider varsayımı olmadan test eder. Yalnız yetkili active black-box transport sağlar;
vulnerability değerlendirmez ve scan orchestration yapmaz.

## Yapılandırma ve mapping

Config; base URL, endpoint path, method, non-secret header, secret-header reference, JSON request
template, dotted response mapping, timeout/delay/request limiti, TLS, allowed host/port, redirect,
response byte limiti ve opsiyonel health path içerir. Secret değerleri yalnız `env:`, `keychain:`,
`secret-manager:`, `vault:` veya `file-secret:` referansıdır. Gerçek secret backend henüz yoktur.

```json
{"messages": [{"role": "user", "content": "{{PAYLOAD}}"}], "session": "{{SESSION_ID}}"}
```

Yalnız `PAYLOAD`, `SESSION_ID`, `CANARY_TOKEN`, `TEST_CASE_ID` ve `PAYLOAD_ID` kullanılabilir.
Renderer literal replacement yapar; Jinja, Python, shell, environment expansion, expression ve
recursive template çalıştırmaz. Response mapping `answer`, `response.text` veya
`choices.0.message.content` biçiminde restricted dotted path kullanır. Response text zorunlu;
citation, source, tool/function, model, finish reason ve session alanları opsiyoneldir.

## SSRF ve transport güvenliği

- Yalnız HTTP/HTTPS; TLS verification varsayılan açıktır.
- URL credential ve fragment reddedilir; host/port açık allowlist gerektirir.
- Loopback, link-local, multicast, unspecified ve bilinen metadata IP'leri daima bloklanır.
- Private IP varsayılan blokludur; self-hosted hedef hem allowed host hem explicit opt-in ister.
- DNS sonuçlarının tamamı isteğin hemen öncesinde doğrulanır.
- Redirect varsayılan kapalıdır. Açıldığında her destination yeniden doğrulanır, sayı sınırlıdır
  ve credential sızıntısını önlemek için cross-host redirect bloklanır.
- Response stream edilir ve byte sınırı aşılırsa fail-closed hata üretilir.
- Otomatik retry yoktur; total timeout, cancellation ve budget uygulanır.
- User-Agent `RAGScanner/<version>` biçimindedir; payload veya secret loglanmaz.

DNS kontrolü ile HTTP client çözümlemesi arasında teorik TOCTOU/DNS-rebinding penceresi kalır.
Production hardening aşamasında validated-IP pinning değerlendirilmelidir. Private opt-in bu
riski tamamen ortadan kaldırmaz.

Health path yoksa yalnız config/destination kontrol edilir ve istek gitmez. Path açıkça
yapılandırılırsa payload içermeyen GET yapılır; her endpoint GET destekler varsayımı yoktur.
Active hazırlama/gönderme geçerli ve süresi dolmamış authorization ister. Safe mode varsayılandır;
unsafe payload ve destructive mod bloklanır. Adaptör vulnerability değerlendirmez.
