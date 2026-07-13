# ADR-0007: SQLite-backed tek worker ve APScheduler

- Status: Accepted
- Date: 2026-07-12

## Karar

FastAPI in-process task yerine SQLite `Job` tablosunu claim/lease eden tek worker kullanılacak. APScheduler yalnızca due schedule’lardan idempotent job üretecek. RQ, Celery ve Dramatiq ilk sürümde kullanılmayacak.

## Gerekçe

Uzun tarama, restart recovery, progress, cancellation ve status için durable job gerekir; ek Redis/RabbitMQ servisi tek makine hedefinde gereksizdir.

## Sonuçlar

Tek aktif worker ve bounded concurrency sınırı vardır. Birden çok worker ihtiyacı ölçülürse PostgreSQL/queue kararı yeniden açılır. Worker henüz uygulanmamıştır.

