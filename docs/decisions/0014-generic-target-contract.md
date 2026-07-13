# ADR-0014: Generic TargetAdapter contract

- Status: Accepted
- Date: 2026-07-12

## Bağlam

Platformlar farklı auth, payload, streaming ve response şemalarına sahiptir; core’un vendor koşulları içermemesi gerekir.

## Karar

Target contract capability discovery, healthcheck, authorized `send_test`, cancellation, timeout, rate limit, request/token budget, correlation/session, bounded response ve structured tool/citation observations içerir. Credential yalnız opaque secret reference’tır.

Evaluation sonucu `confirmed`, `probable`, `ambiguous` veya `not_detected` olur. Transport error, timeout veya malformed response vulnerability değildir; failed/skipped test olarak kaydedilir.

İlk concrete adapter generic REST’tir. Adapter request/response mapping’i config/schema ile yapar ve custom code çalıştırmaz.

## Sonuçlar

Platform adapter’ları aynı fake/contract suite’ini kullanır. Generic esneklik SSRF ve şema riskini artırdığı için allowed host ve bounded parsing zorunludur.

