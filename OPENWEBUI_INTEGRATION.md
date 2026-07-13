# OpenWebUI entegrasyonu

OpenWebUI entegrasyonu planlanmıştır fakat henüz uygulanmamıştır. Mevcut repository yalnız gelecekteki connector için `packages/connectors/` sınırını ayırır.

Gelecekte OpenWebUI document source ve OpenWebUI model provider ayrı yapılandırılacaktır. Core doğrudan OpenWebUI SDK/API tiplerine bağımlı olmayacak; API key loglanmayacak veya browser’a gönderilmeyecektir. Endpoint, SSRF, timeout, response-size ve permission kontrolleri RS-028 kapsamında uygulanacaktır.

Şu anda connection test, model/knowledge discovery, content retrieval veya scan komutu yoktur.

