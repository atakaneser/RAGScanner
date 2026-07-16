# ADR-0027: Guided OpenWebUI in-process scan

**Date:** 2026-07-16

## Context

The guided CLI previously discovered authenticated OpenWebUI knowledge-base metadata and then
ended. Users had to infer that a later menu number was not accepted by the shell and manually
construct a durable job command before they could scan selected content.

## Decision

Option 2 presents a numbered selection after metadata discovery. A separately explicit content
consent starts one selected knowledge-base scan in the same CLI process. The supplied API key is
stored in a unique temporary environment variable only for the duration of that scan, is not written
to a report or database, and is removed in a final cleanup block.

Durable job commands continue to require a user-managed environment reference because a separate
worker cannot safely inherit an in-memory prompt value.

## Consequences

- The guided path is usable without manual job construction.
- Content retrieval remains opt-in and scoped to one selected knowledge base.
- The existing durable worker remains the automation path.
