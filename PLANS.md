# Planlar ve açık kararlar

Ürün tek ve ücretsizdir; Community/Pro ayrımı, ödeme, abonelik, entitlement ve ticari paket kararı bulunmaz.

| ID | Açık karar | Engellediği iş |
|---|---|---|
| OD-001 | **Çözüldü:** Apache-2.0; `LICENSE_DECISION.md` | — |
| OD-002 | Paket adı ve tek-repo modül yapısı | RS-003 |
| OD-003 | Yerel geçmiş için varsayılan saklama/temizleme davranışı | RS-016 |
| OD-005 | Health score formülü, kritik güvenlik tavanı, coverage ve kalibrasyon | RS-017 |
| OD-006 | RAG Rot formülü, baseline/window ve eksik veri davranışı | RS-027 |
| OD-007 | SQLAlchemy veya SQLModel | RS-004/016 |
| OD-008 | Self-hosted queue/scheduler teknolojisi ve minimum topoloji | RS-035 |
| OD-009 | Çok kullanıcılı modun auth/session yaklaşımı; yerel mod auth’suz kalacak | RS-030 |
| OD-010 | Connector secret şifreleme/reference ve key rotation | Connector’lar |
| OD-011 | Evidence/artifact retention, silme ve opsiyonel object storage | İzleme/gizlilik |
| OD-012 | Desteklenen OpenWebUI sürümleri ve change-detection fallback | RS-028 |
| OD-013 | Model provider compatibility contract ve offline model paketleme | M2 |
| OD-014 | Bildirim kanalları, retry/dedup politikası | RS-036 |
| OD-016 | İmzalı rapor gerçekten gerekli mi; gerekliyse teknik anlamı | Raporlama |
| OD-017 | Telemetry tamamen kapalı mı, açık onaylı mı olacak? | Sürüm |
| OD-018 | Güvenlik iletişim adresi, desteklenen sürümler, disclosure politikası | Açık sürüm |
| OD-019 | Accessibility/browser hedefi | Dashboard/docs |
| OD-021 | API/OpenWebUI modüllerinin tek repo içindeki yerleşimi | M3 |
| OD-022 | Rule-pack formatı, imzalama, update ve rollback | M1/M4 |
| OD-023 | Tek kullanıcı modu ile isteğe bağlı organizasyon modelinin ilişkisi | RS-030 |
| OD-024 | Connector değişikliklerinde source/chunk kimliği | RS-004/006/028 |
| OD-025 | Parser kaynak limitleri ve izolasyon yöntemi | Parser işleri |
| OD-026 | Active Scan için varsayılan güvenli payload profili ve destructive-test politikası | Active Security Scan |
| OD-027 | Generic TargetAdapter request/response/capability sözleşmesi | RS-046 |
| OD-028 | Platformların Tier 1/2/Experimental uyumluluk kriterleri ve version matrix | Connector/target işleri |
| OD-029 | Active response analyzer kalibrasyon datası ve confirmed/suspected semantiği | Active Security Scan |
| OD-030 | OpenAI Responses ile Chat Completions target önceliği | OpenAI adapter |

Önerilen sıralama: kalan OD-002, 007, 022, 024 ve 025 kararlarını ilgili işler sırasında çöz;
ardından güvenli input → normalize document → security/quality finding → versioned JSON report
dikey dilimini koru.
