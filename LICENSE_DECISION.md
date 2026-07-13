# License decision

**Decision:** On July 13, 2026, the repository owner approved Apache License 2.0 for the complete
RAGScanner repository. The root [`LICENSE`](LICENSE) covers source code, CLI, rule packs,
documentation, and future free product components.

The objective is to keep the complete product—including Core, CLI, dashboard, scheduler,
connectors, and security rules—free and open to contribution. There will be no paid feature boundary
or closed module.

| Option | Advantage | Risk |
|---|---|---|
| Apache-2.0 | Simple, permissive, and includes an explicit patent grant | Allows third-party commercial use |
| MPL-2.0 | Requires file-level modifications to remain open | More complex license compatibility |
| AGPL-3.0 | Covers modified software offered over a network | May add adoption and integration friction |

Apache-2.0 was selected for permissive reuse, its patent grant, and broad ecosystem compatibility.
It does not create a paid edition or closed module. Because Apache-2.0 grants no trademark rights, a
separate trademark policy will be considered only if a concrete need appears.
