# ADR-0013: Safe active-scanning policy

- Status: Accepted
- Date: 2026-07-12

## Bağlam

Active testler tool, email, shell, dosya veya database yan etkisi oluşturabilir ve izinsiz kullanım hukuki/operasyonel risk taşır.

## Karar

Active Scan açık target-owner authorization gerektirir ve varsayılan `safe` profildir. Destructive/side-effect-capable payload hiçbir zaman default değildir ve safe profile’a dahil edilemez. Tool-use testleri canary, dry-run veya no-op action kullanır.

TargetAdapter; allowed-host/SSRF policy, TLS, timeout, rate limit, request/token budget, cancellation, response-size ve credential-reference alanlarını desteklemek zorundadır. Secret değeri log, report veya artifact’a yazılmaz.

## Sonuçlar

Bazı gerçek tool-abuse açıkları safe profile ile tam kanıtlanamayabilir ve `probable/ambiguous` kalır. Güvenlik ve yetki, coverage’dan önceliklidir.

