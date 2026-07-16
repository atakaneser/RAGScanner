# OpenWebUI

RAGScanner supports two separate OpenWebUI workflows:

1. Guided, consent-based local discovery and metadata inventory across Docker, Podman, nerdctl,
   Finch, and bounded loopback candidates.
2. A production, read-only `SourceConnector` that retrieves accessible files from one selected
   knowledge base and runs the normal static pipeline.

The content connector requires explicit content consent and an external credential reference. The
credential value is resolved only in worker memory and is not written to the job database or
report. Non-loopback endpoints require HTTPS; HTTP is accepted only for loopback development.
Redirects and environment proxies are disabled, and metadata/content responses are bounded.

Knowledge-base discovery accepts both current paginated responses and older list responses. If an
installation rejects the optional pagination parameter, RAGScanner retries the same read-only list
request once without it. An HTTP 400 message includes the bounded, redacted server diagnostic when
one is supplied; it never includes the API key.

```bash
export OPENWEBUI_API_KEY="your-local-runtime-secret"
ragscanner jobs enqueue-openwebui \
  --base-url http://127.0.0.1:3000 \
  --knowledge-id KNOWLEDGE_ID \
  --credential-ref env:OPENWEBUI_API_KEY \
  --consent-content
ragscanner worker
```

The connector currently enumerates knowledge-linked files and reads their content. It does not
mutate OpenWebUI, retrieve model credentials, scan chat endpoints, provide incremental change
detection, or automatically include every standalone/chat attachment. Container metadata
discovery and content retrieval remain separate consent boundaries.

In the guided CLI, option 3 lists accessible knowledge bases first. The user can then choose one
and explicitly consent to an immediate local content scan; the supplied API key exists only in that
process memory and is removed when the scan completes. Durable job commands remain available for
automation and workers.

See [OPENWEBUI_INTEGRATION.md](../OPENWEBUI_INTEGRATION.md) and
[ADR-0023](decisions/0023-consent-gated-openwebui-content-source.md).
