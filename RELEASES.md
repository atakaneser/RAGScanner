# Release strategy

No version has been published. The first prepared PEP 440 candidate is `0.1.0a1`; its intended
public release title is `v0.1.0-alpha.1`. Apache-2.0 licensing, the canonical repository, and the
GitHub Security Advisory channel are approved. No tag or package will be published until clean-commit
review and release verification are complete.

Public API, report, and SDK contracts will follow Semantic Versioning, a changelog, and public
release notes. Rule packs, report schemas, fingerprints, scoring policies, and connector
compatibility are versioned independently where appropriate.

## Distribution

- Public Python packages, open container images, and documentation will be released from protected
  `main`.
- Dashboard, API, and workers remain in the same open repository and compatibility set.
- Delivery proceeds from Core to contract tests to public artifacts.
- Security fixes may use coordinated private disclosure before release; the corrected source will
  still be published openly.

Pre-release review covers tests, installation, schema compatibility, SBOM/provenance,
supported-platform matrix, upgrade/rollback, and known limitations. Publishing always requires
explicit user approval.
