# RAGScanner

[English](README.md) · [Türkçe](README.tr.md) · [Deutsch](README.de.md) ·
[Français](README.fr.md) · **简体中文** · [Italiano](README.it.md)

RAGScanner 是一个免费、开源、以本地优先为原则的工具，用于检查 RAG 知识源中的安全与内容质量
风险。当前技术 Alpha 版本可扫描 TXT、Markdown、文本型 PDF 和 DOCX 文件，并生成终端、JSON 或
独立 HTML 报告。

> [!WARNING]
> 当前版本属于技术 Alpha。静态扫描不能证明正在运行的 RAG 应用是安全的。扫描结果仅供审查，
> 不构成安全保证。

## 当前可用功能

- 扫描单个本地文件或文件夹
- 支持 TXT、Markdown、文本型 PDF 和 DOCX
- 确定性的规范化、分块和源位置映射
- 带版本的静态安全规则
- 精确重复与词法近似重复分析
- Chunk 质量检查
- 终端、JSON 和独立 HTML 报告
- 默认完全在本地离线执行静态扫描
- 通过 `ragscanner` 命令使用英文引导流程

OCR、持久化、API、仪表板、调度器、OpenWebUI 内容连接器和 ModelProvider 尚未提供。

## 安装与首次扫描

需要 Python 3.12/3.13 和 [`uv`](https://docs.astral.sh/uv/)。

```powershell
uv tool install git+https://github.com/atakaneser/RAGScanner.git
ragscanner doctor
ragscanner
```

直接扫描：

```powershell
ragscanner scan "C:\Users\Example\Documents\Knowledge Base"
```

```bash
ragscanner scan ./knowledge-base --format html --output ragscanner-report.html
```

包含空格或括号的路径必须使用引号。RAGScanner 默认不会覆盖已有报告。

## 语言与隐私

产品界面、错误消息、修复建议和生成的技术元数据均使用英文。被扫描的 RAG 文档可以使用任何
Unicode 语言。为了保持审计真实性，来源证据会保留原始语言。

静态扫描不会把文档发送到外部服务，不需要 LLM，不运行遥测，不访问链接，也不会执行检测到的
命令。未来的远程连接器和模型只有在明确配置并获得同意后才会启用。

## 架构与路线图

`SourceConnector`、`TargetAdapter` 和 `ModelProvider` 是彼此独立的角色。OpenWebUI 是计划支持的
集成之一，并非产品核心。

下一步包括 PDF/路径稳健性与报告体验、SQLite 历史记录、API、OpenWebUI 连接器、本地仪表板和
调度器。详情请参阅[英文规范 README](README.md) 和 [ROADMAP.md](ROADMAP.md)。

RAGScanner 使用 [Apache License 2.0](LICENSE)，并将保持完全免费。
