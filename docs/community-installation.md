# User installation

Requirements: Python 3.12 or 3.13 and [`uv`](https://docs.astral.sh/uv/).

Install the current alpha directly from GitHub without cloning the repository:

```powershell
uv tool install git+https://github.com/atakaneser/RAGScanner.git
ragscanner doctor
ragscanner
```

Upgrade, repair, or remove the installed tool with one command:

```powershell
ragscanner update
ragscanner repair
ragscanner uninstall
```

Uninstall asks for confirmation; automation may use `ragscanner uninstall --yes`.

After the first PyPI release, the installation command will become `uv tool install ragscanner`.
No package or release tag has been published yet. RAGScanner requires no API key for local static
scans and does not transmit documents or invoke a remote model.

Contributor installation remains separate:

```bash
git clone https://github.com/atakaneser/RAGScanner.git
cd RAGScanner
uv sync --frozen
uv run ragscanner doctor
```
