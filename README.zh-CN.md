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
| 英文引导式上手流程 | 使用裸 `ragscanner` 命令可用 |
| OCR 和语义重复分析 | 尚不可用 |
| 持久化、API、仪表板、历史记录和调度器 | 尚不可用 |
| OpenWebUI 和向量存储内容连接器 | 尚不可用 |
| ModelProvider/BYOM 集成 | 尚不可用 |
| 主动端点扫描 CLI | 不可用；仅有核心契约 |

`ragscanner scan` 运行本地发现 → 解析 → 规范化 → 分块 → 静态安全 → 重复分析 → 分块质量
→ 评分 → 报告流水线。

## 用户快速入门

要求：Python 3.12 或 3.13，以及 [`uv`](https://docs.astral.sh/uv/)。

直接从 GitHub 安装 Alpha 版本：

```powershell
uv tool install git+https://github.com/atakaneser/RAGScanner.git
ragscanner doctor
ragscanner
```

裸命令会打开英文引导流程。它会询问您使用的源，建议范围受限的附近本地源，并可启动扫描。
OpenWebUI 发现功能仅在明确同意后检查固定的回环健康端点；目前尚不获取 OpenWebUI 内容。

使用一个 RAGScanner 命令维护或移除安装：

```powershell
ragscanner update
ragscanner repair
ragscanner uninstall
```

`uninstall` 会要求确认。自动化可使用 `ragscanner uninstall --yes`。这些命令不启动 shell，
而是委托给官方 `uv tool` 环境；`repair` 会完整重新安装，同时保留原始安装源和设置。

发布到 PyPI 后，安装将使用 `uv tool install ragscanner`。目前尚未发布 PyPI 包或版本标签。

## 直接扫描

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

默认情况下，RAGScanner 不会覆盖现有输出文件。

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

远程连接器和可选模型在明确配置并同意之前将保持禁用。OpenWebUI 是计划中的一个集成，并非
产品核心。

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

1. PDF/路径韧性，以及安装、报告和终端用户体验
2. SQLite 扫描历史和持久化
3. 应用 API 和扫描比较
4. OpenWebUI 源连接器
5. 本地仪表板和调度器
6. 其他源连接器、目标适配器和可选模型提供者
7. 打包和部署加固

计划中的功能绝不会被描述为已经可用。详情请参阅 [ROADMAP.md](ROADMAP.md)。

## 贡献和许可证

贡献前请阅读 [CONTRIBUTING.md](CONTRIBUTING.md)、[SECURITY.md](SECURITY.md) 和
[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)。不要在公开 issue 中发布密钥、利用代码或客户内容。

RAGScanner 采用 [Apache License 2.0](LICENSE)。项目只有一个免费、开源产品：没有
Community/Pro 拆分、付费规则源、订阅、授权或闭源模块。
