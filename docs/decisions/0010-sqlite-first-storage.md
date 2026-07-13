# ADR-0010: İlk sürümde SQLite

- Status: Accepted
- Date: 2026-07-12

## Karar

Scan history, findings/occurrences, documents/chunks, schedules, connector config, score snapshots ve job metadata SQLite’ta tutulur. WAL, busy timeout, kısa transaction ve migration kullanılır. Raw artifacts dosya sisteminde kalır.

## Gerekçe

Tek kullanıcı/tek makine deployment için güvenilir ve operasyon gerektirmeyen en basit çözümdür. PostgreSQL servisi ilk sürüm için kanıtlanmış ihtiyaç değildir.

## Migration

Storage portu DB’den bağımsız kalır. Şema migration’ları sürümlenir. Eşzamanlı worker, yoğun write contention veya çok kullanıcılı uzaktan deployment ölçülürse PostgreSQL’e veri taşıma aracı ve yeni ADR hazırlanır.

