# ADR-0002: Python modüler monolith ve server-rendered dashboard

- Status: Accepted
- Date: 2026-07-12

## Karar

Python scanner core, Typer CLI, FastAPI API ve Jinja2/HTMX dashboard seçildi. Next.js ilk sürümde kullanılmayacak. API ve worker aynı dağıtımın farklı process’leri olabilir; bu microservice ayrımı değildir.

## Gerekçe

Tek dil/toolchain, doğrudan Pydantic view modelleri, düşük Docker/RAM maliyeti ve scan/finding ağırlıklı UI için yeterli etkileşim sağlar. Next.js ancak ölçülen UI karmaşıklığı server-rendered yaklaşımı yetersiz bırakırsa yeni ADR ile değerlendirilir.

## Sonuçlar

Frontend ekosistemi daha sınırlıdır fakat ilk sürümün bakım ve deployment maliyeti düşer. Raw HTML/model evidence template’e güvenilir markup olarak geçirilemez.

