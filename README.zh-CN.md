# RAGScanner

> 在用户发现问题之前扫描您的 RAG。

[English](README.md) · [Türkçe](README.tr.md) · [Deutsch](README.de.md) · [Français](README.fr.md) ·
**简体中文** · [Italiano](README.it.md)

RAGScanner 是一个免费、开源、本地优先的工具，用于检查 RAG 知识源中的安全和内容质量风险。
当前技术 Alpha 版本可扫描 TXT、Markdown、基于文本的 PDF 和 DOCX 文件，并生成终端、JSON 或
独立 HTML 报告。

当前静态流水线不会将文档传输到远程服务，不需要 LLM，不运行遥测，不跟踪链接，也绝不会执行
检测到的命令。

> [!WARNING]
> 这是一个技术 Alpha 版本。静态扫描无法证明正在运行的 RAG 应用是安全的，也不能提供完整的
> 提示注入防护。扫描结果仅供审查，不构成安全保证。

## 当前可用功能

| 功能 | Alpha 状态 |
|---|---|
| 单个本地文件和文件夹扫描 | 可用 |
| TXT、Markdown、基于文本的 PDF 和 DOCX | 可用 |
| 确定性规范化和源映射 | 可用 |
| 结构、段落和令牌窗口分块 | 可用 |
| 版本化静态 RAG 安全规则 | 可用 |
| 精确和词法近似重复分析 | 可用 |
| 分块质量检查 | 可用 |
| 终端、JSON 和独立 HTML 报告 | 可用 |
| 离线静态扫描 | 默认行为 |
| 统一机器安装和 dashboard 启动 | `ragscanner install`；裸 `ragscanner` 打开 dashboard |
| 经同意的容器 OpenWebUI 发现和知识库/文件元数据清单 | 可用 |
| OCR 和语义重复分析 | 尚不可用 |
| 可选 SQLite 历史记录和覆盖范围感知比较 | 可通过 CLI 使用 |
| localhost 历史记录 API | 可通过 `ragscanner serve` 使用 |
| 持久 SQLite 静态扫描作业和 worker | 可用 |
| 具有作用域身份验证的异步扫描/作业 API | 可在回环地址使用 |
| 本地概览和队列仪表板 | 可通过 `ragscanner serve` 使用 |
| 支持日期/来源筛选、详情和比较的仪表板报告存档 | 可用 |
| 不含密钥的持久来源配置及 Sources/Settings 管理 | 可用 |
| 每用户本地 Agent | 已停用；由机器服务取代 |
| 具有本地管理员初始化的机器本地 Host Service | 可用 |
| Docker、Podman、nerdctl、Finch、Kubernetes 和 localhost 元数据发现 | 可用 |
| 经明确同意的 OpenWebUI 知识内容连接器 | 可用 |
| 调度器和向量存储内容连接器 | 尚不可用 |
| 每次扫描可选的本地/远程 AI 辅助报告分析 | 可用，默认关闭 |
| 主动端点扫描 CLI | 不可用；仅有核心契约 |

`ragscanner scan` 运行本地发现 → 解析 → 规范化 → 分块 → 静态安全 → 重复分析 → 分块质量
→ 评分 → 报告流水线。

## 用户快速入门

要求：Python 3.12 或 3.13，以及 [`uv`](https://docs.astral.sh/uv/)。

直接从 GitHub 安装 Alpha 版本：

```powershell
uv tool install git+https://github.com/atakaneser/RAGScanner.git
ragscanner doctor
ragscanner install
```

`ragscanner install` 会一次性安装机器级服务、隔离运行时和本地 dashboard 地址，并默认打开
dashboard。使用 `ragscanner install --mode terminal` 可在 CLI 中完成设置。之后直接运行
`ragscanner` 将始终打开 dashboard。自动发现仅建议名称与 RAG 相关的
直接文件夹，不会将 Documents 等通用文件夹视为 RAG 源。明确同意后，OpenWebUI 发现功能会检查可用 Docker、Podman、nerdctl 或 Finch 运行时的有限
元数据以及常见回环地址。单独提供且仅保存在内存中的 API 密钥可清点有权访问的知识库，以及
关联或独立/聊天文件的元数据。选项 2 允许用户选择一个列出的 OpenWebUI 知识库，并在单独明确
同意读取内容后，在同一本地进程中运行静态流水线。

使用一个 RAGScanner 命令维护或移除安装：

```powershell
ragscanner update
ragscanner repair
ragscanner uninstall
ragscanner status
ragscanner open
```

这些命令需要管理员权限。`update` 和 `repair` 会替换机器级运行时并重启 Host Service。
自动化可使用 `ragscanner uninstall --yes`。除非指定 `--purge-data`，`uninstall` 会保留机器级报告和历史记录。

发布到 PyPI 后，安装将使用 `uv tool install ragscanner`。目前尚未发布 PyPI 包或版本标签。

## 直接扫描

每个直接扫描或 dashboard 任务都可以单独选择是否启用 AI 辅助分析。本地提供方包括
Ollama、LM Studio、LocalAI 和 vLLM；远程选项包括 OpenRouter、OpenAI、NVIDIA NIM、
Anthropic、Google Gemini、Groq、Mistral AI、Together AI 以及自定义 OpenAI 兼容端点。
AI 默认关闭；远程使用需要对该次扫描明确同意。系统只发送有界且已脱敏的报告摘要，
不会发送原始文档或发现证据。提供方失败不会影响确定性报告。

```bash
ragscanner scan ./knowledge-base --ai-provider ollama --ai-model llama3.1:8b
```

包含空格、括号或其他 shell 敏感字符的路径应使用引号包围。

```powershell
ragscanner scan "C:\Users\Example\Documents\Knowledge Base"
ragscanner scan "C:\Users\Example\Downloads\Manual (2026).pdf"
```

```bash
ragscanner scan ./knowledge-base
ragscanner scan ./knowledge-base/manual.pdf
```

创建报告：

```bash
ragscanner scan ./knowledge-base --format json --output report.json
ragscanner scan ./knowledge-base --format html --output ragscanner-report.html
```

仅在明确请求时保存和比较本地扫描历史记录：

```bash
ragscanner scan ./knowledge-base --save-history
ragscanner history list
ragscanner history compare BASELINE_HISTORY_ID CANDIDATE_HISTORY_ID
ragscanner serve
```

将持久扫描加入队列并运行 worker：

```bash
ragscanner jobs enqueue-scan ./knowledge-base
ragscanner jobs list
ragscanner worker
```

对于经同意的 OpenWebUI 扫描，请将凭据保留在 SQLite 之外：

```bash
export OPENWEBUI_API_KEY="your-local-runtime-secret"
ragscanner jobs enqueue-openwebui --base-url http://127.0.0.1:3000 \
  --knowledge-id KNOWLEDGE_ID --credential-ref env:OPENWEBUI_API_KEY --consent-content
ragscanner worker
```

`ragscanner serve` 会打开本地仪表板。设置 `RAGSCANNER_API_KEY` 可通过 API 启用具有作用域的
Bearer 身份验证扫描创建和作业控制。服务器仅绑定到 `127.0.0.1`。

默认情况下，RAGScanner 不会覆盖现有输出文件。

## 完整 CLI 命令参考

运行 `ragscanner COMMAND --help` 可查看已安装版本的权威语法。以下内容覆盖全部公开接口；
内部兼容命令会有意隐藏。

### 调用与诊断

| 命令 | 详细用途 |
| --- | --- |
| `ragscanner` | 已安装时打开 dashboard；否则显示安装命令。 |
| `ragscanner --version` | 显示已安装的 CLI 版本。 |
| `ragscanner --help` / `ragscanner COMMAND --help` | 显示全局或命令专用帮助，不改变机器状态。 |
| `ragscanner --install-completion` / `--show-completion` | 安装 shell 补全或显示 Typer 支持的补全脚本。 |
| `ragscanner doctor` | 离线诊断安装、路径、配置、解析器和运行时。 |
| `ragscanner paths` | 显示当前系统的机器配置、数据、报告、临时及旧版路径。 |

### 机器安装与生命周期

| 命令 | 详细用途 |
| --- | --- |
| `ragscanner install` | 安装隔离运行时和系统服务，配置 `local.ragscanner.com`，初始化机器数据并打开 dashboard；需要时请求管理员权限。 |
| `ragscanner install --yes` | 为无人值守安装接受常规提示；仍可能需要系统提权。 |
| `ragscanner install --mode terminal` | 使用终端配置而非默认 dashboard；有效模式为 `dashboard` 和 `terminal`。 |
| `ragscanner install --no-open-dashboard` | 完整安装，但结束后不打开浏览器。 |
| `ragscanner open` | 在默认浏览器打开已安装 dashboard，不启动第二个前台服务器。 |
| `ragscanner status` | 显示机器安装、服务、dashboard、运行时和数据路径状态。 |
| `ragscanner update` | 替换隔离运行时并重启机器服务；需要管理员权限。 |
| `ragscanner repair` | 修复缺失的运行时、服务、主机名、目录和配置；需要管理员权限。 |
| `ragscanner uninstall` | 确认后删除服务、运行时和主机名映射，同时保留报告与历史。 |
| `ragscanner uninstall --yes --purge-data` | 无交互删除，并清除机器配置、报告历史和托管数据；此操作具有破坏性。 |

### 直接本地扫描

```text
ragscanner scan PATH [OPTIONS]
```

`PATH` 可以是受支持的文件或目录。含空格或 shell 特殊字符的路径须加引号。扫描在本地
运行，除非明确选择，否则 AI 增强关闭。

| 选项 | 详细用途 |
| --- | --- |
| `--format terminal|json|html`, `--output PATH` | 选择终端或显式 JSON/HTML 导出；导出需要路径，且不会覆盖现有文件。 |
| `--include GLOB`, `--exclude GLOB` | 用可重复的 glob 模式限制目录发现。 |
| `--recursive` / `--no-recursive` | 开关子目录递归；默认开启。 |
| `--max-file-size BYTES`, `--max-files COUNT` | 对输入大小和文件数量设置正数安全上限。 |
| `--category NAME`, `--exclude-rule ID` | 包含类别或排除规则；多个值可重复传入。 |
| `--include-pii` / `--no-include-pii` | 开关有效扫描策略中的 PII 规则。 |
| `--min-severity LEVEL`, `--fail-on LEVEL`, `--max-findings COUNT` | 过滤显示、设定非零退出阈值并限制发现数量。 |
| `--config FILE` | 从显式文件加载扫描策略，而非仅使用默认值和机器配置。 |
| `--security-only`, `--quality-only` | 仅运行安全或仅运行质量规则；不要同时使用。 |
| `--quiet`, `--verbose`, `--no-color` | 控制终端详情和 ANSI 颜色，不改变扫描结果。 |
| `--save-history`, `--history-db FILE` | 保存版本化报告，并可选择非默认 SQLite 历史数据库。 |
| `--ai-provider NAME`, `--ai-model NAME`, `--ai-base-url URL` | 使用所选提供商、模型及可选兼容端点启用报告增强。 |
| `--ai-credential-ref REF`, `--consent-remote-ai` | 从外部解析如 `env:OPENROUTER_API_KEY` 的凭据，并记录远程使用同意。 |

### AI 报告增强

| 命令或选项 | 详细用途 |
| --- | --- |
| `ragscanner analyze-report REPORT_FILE --model MODEL --output FILE` | 增强现有受支持报告；模型和输出均为必填。 |
| `--provider NAME` | 选择分析提供商，默认为 `ollama`；可配置本地和远程兼容提供商。 |
| `--base-url URL`, `--credential-ref REF` | 覆盖端点，并在报告/历史内容之外解析密钥。 |
| `--consent-remote` | 明确允许发送受限且脱敏的报告摘要；原始文档和证据不会发送。 |

### 持久作业与 worker

| 命令 | 详细用途 |
| --- | --- |
| `ragscanner jobs enqueue-scan PATH` | 排队持久文件/目录扫描；支持 `--database`、`--config`、`--idempotency-key`、`--max-attempts` 和 AI 选项。 |
| `ragscanner jobs enqueue-openwebui` | 排队 OpenWebUI 扫描；必须提供 `--base-url`、`--knowledge-id`、`--credential-ref`、`--consent-content`，也支持数据库、幂等、重试和 AI 选项。 |
| `ragscanner jobs list` | 用 `--database`、`--limit`（1–200）、`--offset` 和 `--format` 列出作业。 |
| `ragscanner jobs show JOB_ID` | 显示尝试、时间、结果引用和错误；`--database` 选择存储。 |
| `ragscanner jobs cancel JOB_ID` | 取消尚未终止的作业；`--database` 选择存储。 |
| `ragscanner jobs retry JOB_ID` | 为符合条件的失败/取消作业创建新尝试。 |
| `ragscanner worker` | 持续租用并执行机器作业数据库中的持久作业。 |
| `ragscanner worker --once` | 处理一次可用工作后退出。 |
| `--database FILE`, `--poll-interval SECONDS`, `--lease-seconds SECONDS`, `--worker-id ID` | 控制存储、轮询（0.1–60）、租约（5–3600）和 worker 身份。 |

### 已存报告历史

| 命令 | 详细用途 |
| --- | --- |
| `ragscanner history list` | 用 `--database`、`--limit`（1–200）、`--offset` 和 `--format` 列出扫描。 |
| `ragscanner history show SCAN_ID` | 用 `--database`、`--format` 和可选 `--verbose` 渲染一份报告。 |
| `ragscanner history compare BASELINE_ID CANDIDATE_ID` | 比较新增、已解决和未变化发现；支持 `--database` 与 `--format`。 |
| `ragscanner history delete SCAN_ID` | 确认后删除报告；仅在有意自动化时使用 `--yes`，`--database` 选择存储。 |

### 渲染与前台服务

| 命令 | 详细用途 |
| --- | --- |
| `ragscanner report SCAN_RESULT` | 使用 `--format`、`--output`、`--verbose`、发现过滤器、`--max-findings`、`--include-info`/`--exclude-info` 及可选 `--show-absolute-paths` 重新渲染。 |
| `ragscanner serve` | 在 loopback 前台运行 dashboard/API 供开发或诊断；正常安装使用机器服务。 |
| `ragscanner serve --port PORT --history-db FILE` | 选择 loopback 端口（1–65535）和替代历史数据库。 |

### 专用扫描器

| 命令 | 详细用途 |
| --- | --- |
| `ragscanner security scan PATH` | 仅运行安全规则；支持规则/类别/严重性过滤、`--format`、`--fail-on`、`--max-findings`、`--include-pii`、`--offline`/`--no-offline`；默认离线。 |
| `ragscanner quality scan PATH` | 用独立开关、`--similarity-threshold`（0.5–1.0）、chunk token 上限、`--fail-on` 和 `--format` 检查精确/近似重复与 chunk 质量。 |

### 运行规则

| 规则 | 含义 |
| --- | --- |
| 退出状态 | 无效输入、运行错误或达到 `--fail-on` 的发现会产生适合 CI 的非零退出码。 |
| 同意 | OpenWebUI 内容访问和远程 AI 需要明确开关；仅发现元数据不授予内容访问。 |
| 凭据 | 将密钥存于外部，只传递凭据引用。 |
| 存储 | 未指定的路径解析为 `ragscanner paths` 显示的系统机器位置。 |
| 服务 | 已安装 dashboard/worker 为机器级；前台 `serve` 和 `worker` 可用于诊断。 |
| 输出安全 | 不覆盖文件，默认隐藏绝对路径，并限制和转义报告证据。 |
| 兼容性 | 选项名和命令输出为英语；所有受支持语言的 RAG 内容保持原生 Unicode。 |

## 多语言输入

产品生成的 UI 标签、状态文本、错误消息、修复建议、元数据和规范文档均为英文。RAG 源保持
Unicode 原生，可包含土耳其语、德语、法语、中文、意大利语、阿拉伯语、西里尔文字、CJK、
表情符号以及 NFC/NFD 文件名变体。

源派生证据会保留原始语言，以保持审计保真度。本地化 README 文件是项目中唯一有意使用非英文
的文档。

## 理解报告

报告会区分：

- 扫描完成状态和部分覆盖；
- 严重性和置信度；
- `confirmed`、`probable`、`ambiguous` 和 `not_detected` 分类；
- 已评估、部分、失败和 `not_assessed` 检查；
- 可用时的文档、页面、分块和源位置；
- 扫描器、规则包和策略版本。

`not_assessed` 并不表示健康或零风险。安全评分不是安全保证。静态扫描和经授权的主动端点测试是
不同模式。

## 隐私和安全模型

- 静态扫描在本地运行，不进行隐藏的网络调用。
- 文档或分块内容不会发送到外部 AI 服务。
- URL 可以被解析，但不会被获取。
- 可疑载荷、宏、shell 命令和嵌入对象不会被执行。
- 不跟踪 DOCX 外部关系；不提取 PDF 附件。
- 证据长度受限、经过 HTML 转义，并对类似密钥的模式进行遮蔽。
- 默认在报告中隐藏绝对源路径。
- 不存在遥测、计费、订阅、授权或许可证服务器。

远程连接器和可选模型在明确配置并同意之前保持禁用。OpenWebUI 内容访问需要选定知识库、
外部凭据引用和明确同意；它只是一个集成，而不是产品核心。

## 贡献者安装

```bash
git clone https://github.com/atakaneser/RAGScanner.git
cd RAGScanner
uv sync --frozen
uv run ragscanner --version
uv run ragscanner doctor
uv run ragscanner scan ./examples/sample-kb
```

质量门禁：

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run pytest
uv build
```

所有测试夹具必须是合成数据。绝不要添加真实凭据、客户文档或个人数据。

## 架构

核心保持独立于 UI 框架、数据库、连接器、模型供应商和 MCP。集成角色有意分离：

- `SourceConnector` 读取文档、分块、元数据或知识库内容。
- `TargetAdapter` 向正在运行的 RAG/聊天应用发送经授权的黑盒测试。
- `ModelProvider` 为 RAGScanner 自身提供可选分析模型。

使用 OpenAI、Hugging Face 或 OpenWebUI 并不能证明存在检索。只有验证了文档/向量/索引检索，
目标才称为 RAG 目标。

有关详细边界和当前状态，请参阅 [ARCHITECTURE.md](ARCHITECTURE.md)、
[PRODUCT.md](PRODUCT.md) 和 [docs/status/current.md](docs/status/current.md)。

## 路线图

近期顺序如下：

1. 剩余的持久化恢复和 API 规模历史记录/比较工作
2. 按能力分级的 SharePoint、Web、SaaS、Git、对象存储和向量连接器
3. OpenWebUI 兼容性、增量变更检测、源身份和密钥提供程序
4. 调度、保留策略、周期任务和报告界面本地化
5. 调度器、保留策略和通知
6. 打包和部署加固

计划中的功能绝不会被描述为已经可用。详情请参阅 [ROADMAP.md](ROADMAP.md)。

## 贡献和许可证

贡献前请阅读 [CONTRIBUTING.md](CONTRIBUTING.md)、[SECURITY.md](SECURITY.md) 和
[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)。不要在公开 issue 中发布密钥、利用代码或客户内容。

RAGScanner 采用 [Apache License 2.0](LICENSE)。项目只有一个免费、开源产品：没有
Community/Pro 拆分、付费规则源、订阅、授权或闭源模块。
