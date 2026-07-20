# ADR-0035: Bounded website and SharePoint URL scans

## Status

Accepted

## Context

RAG knowledge may live on documentation websites, in sitemap-listed files, or at SharePoint URLs.
Fetching arbitrary web content from the machine service introduces consent, SSRF, redirect,
credential, unbounded-crawl, and active-content risks.

## Decision

Add a read-only `WebsiteSourceConnector` outside Core. A job may target one HTTP(S) URL or a sitemap.
Remote targets require HTTPS and explicit content consent. Sitemap entries must remain on the exact
scheme, host, and port of the configured URL. Redirects and proxy environment variables are disabled;
responses, inventories, and timeouts are bounded. Retrieved bytes pass through the existing static
parser pipeline and no page script is executed.

Accessible SharePoint page or document URLs use this connector. An optional bearer token is resolved
at execution time from an approved external secret reference and is never persisted in the job or
report. Microsoft Graph tenant/site/library discovery is not implied by this adapter.

## Consequences

- Public documentation and directly accessible SharePoint content can be assessed once or on an
  interval without coupling Core to an HTTP vendor.
- Cross-origin sitemap URLs, redirects, private literal network addresses, oversized content, and
  malformed XML fail safely.
- Authenticated SharePoint library enumeration remains unavailable until an OAuth/Graph connector
  defines tenant consent, token refresh, and least-privilege scopes.
