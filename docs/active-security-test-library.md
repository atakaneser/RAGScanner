# Active security test library

The active library contains deterministic data definitions that may later be transported through a
`TargetAdapter`. Loading a case neither executes a payload nor performs network/evaluation. Every
active scan still requires explicit target-owner authorization.

Packs live under `rules/active/*.json`. Schema, pack, and case have separate semantic versions;
unsupported schema versions fail closed. JSON avoids another parser dependency and matches the
published schema representation.

Safe mode is default. `safe_for_production` means the fixture contains no real credential, target,
email, destructive command/SQL, or intended real side effect; it does not guarantee zero risk or a
secure target. Destructive content is rejected from the initial library. Tool tests use canary,
dry-run, simulated, or no-op behavior. High/critical cases include controls where practical.

Allowed placeholders are `CANARY_TOKEN`, `TEST_SESSION_ID`, `SAFE_TOOL_NAME`,
`FAKE_DOCUMENT_NAME`, and `AUTHORIZED_TEST_USER`. Literal replacement is the only rendering;
unknown, missing, extra, or nested placeholders fail closed.

Contributions require stable IDs, semantic versions, expected safe behavior, explicit indicators,
remediation, language/tags, controls for high-risk cases, multilingual/boundary tests, and no real
person/system/data or executable content. Conservative validation is not perfect dangerous-text
detection; review remains mandatory.
