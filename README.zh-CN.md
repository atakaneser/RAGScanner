# RAGScanner

> 在用户之前扫描你的 RAG。

[English](README.md) · [Türkçe](README.tr.md) · [Deutsch](README.de.md) · [Français](README.fr.md) ·
**简体中文** · [Italiano](README.it.md)

RAGScanner 是一个免费、开源、本地优先的扫描器，用于发现 RAG 知识源中的安全和内容质量风险。
它在机器本地的 dashboard 中整合确定性扫描、持久任务、报告历史、周期监控和可选 AI 建议。

> [!WARNING]
> RAGScanner 仍是技术 alpha。静态报告只用于辅助审查，不能证明正在运行的 RAG 系统安全，
> 也不能保证抵御所有提示注入方式。

## 当前可用

| 领域 | 当前能力 |
|---|---|
| 本地内容 | 单个文件和限制在明确根目录内的文件夹 |
| 格式 | Markdown、TXT、HTML、PDF、DOCX、PPTX、XLSX、ODT、EPUB、RST、AsciiDoc、CSV/TSV、JSON/JSONL、YAML、XML 和日志 |
| 远程来源 | OpenWebUI 知识库；HTTPS 页面、文档、同源站点地图和可访问的 SharePoint URL |
| 分析 | 静态安全规则、精确/词法重复和分块质量检查 |
| 报告 | 终端/JSON，以及本地化的独立 HTML、Excel 和 PDF 下载 |
| 历史 | 易读 ID、筛选、详情、比较、健康趋势和永久删除 |
| 任务 | 持久单次任务、周期任务、取消、重试、进度和安全日志 |
| AI | 可选本地或明确授权的远程建议；默认关闭 |
| 语言 | 英语、土耳其语、德语、法语、简体中文和意大利语界面标签 |
| 安装 | Windows、macOS 和 Linux 的机器本地 Host Service |

OCR、语义重复分析、经过身份验证的 Microsoft Graph 库发现、向量库内容连接器、cron/日历、
可配置保留策略、多用户身份验证和 Docker 部署尚不可用。检测到平台不代表获得内容访问权或完成评估。

## 安装并打开

从官方仓库安装，然后创建机器服务：

```bash
uv tool install git+https://github.com/atakaneser/RAGScanner.git
ragscanner doctor
ragscanner install
```

安装程序会打开本地 dashboard。之后可使用：

```bash
ragscanner
ragscanner open
ragscanner status
ragscanner paths
```

机器安装和生命周期命令需要管理员权限。dashboard 仅绑定 `127.0.0.1`，固定地址为
`http://localhost:8765`。它不会修改 hosts 文件，也不接受自定义主机名或端口。可在“设置”中
更改本地管理员密码；更改后会关闭所有其他 dashboard 会话。

## 更新、修复和卸载

```bash
ragscanner update
ragscanner repair
ragscanner uninstall
ragscanner uninstall --purge-data --yes
```

`update` 安装最新的官方 `main` 运行时，并保留设置、密钥、任务和报告。`repair` 重建运行时与
服务注册。`uninstall` 默认保留本地数据；`--purge-data` 会永久删除数据。

## 扫描内容

推荐使用 dashboard。自动化或直接本地扫描可使用：

```bash
ragscanner scan PATH
ragscanner scan PATH --save-history
ragscanner scan PATH --format html --output report.html
ragscanner serve
```

“创建任务”抽屉支持：

- 本地文件和文件夹；
- 明确同意内容访问后的 OpenWebUI 知识库；
- 一个 HTTPS 页面或受支持文档；
- 同源 URL 站点地图和一层嵌套站点地图索引；
- 可直接访问的 SharePoint URL，可选 Bearer 令牌环境变量引用；
- 单次执行或固定间隔周期监控。

远程网站扫描拒绝重定向和跨源站点地图项，不执行脚本，并限制页面数、响应大小和超时。
经过身份验证的 Microsoft Graph 站点/库发现是另行规划的连接器。

## AI 辅助报告

AI 分析是可选建议，不替代确定性发现。设置会从 Ollama、LM Studio、LocalAI 或 vLLM 中检测
已安装模型，不会继续保留过期模型名。远程提供商需要 HTTPS、外部凭据引用和每次扫描的明确同意。

系统只发送有界且已脱敏的发现摘要，不发送原始文档或发现证据。输出必须通过架构验证。如果兼容的
本地服务器以 HTTP 400 拒绝结构化输出字段，RAGScanner 会以 JSON 兼容模式重试一次；仍失败时记录
可操作的错误代码。
常见的架构偏差会被规范化，模型虚构的发现引用会被安全丢弃；通过验证的分析可以为每个真实发现附加
修复和验证步骤。

## 报告和运维

概览健康状态始终基于剩余报告中最新的已完成报告。报告可筛选、按日期比较、查看详情，或确认后永久
删除。单次任务与周期定义分开显示。活动区显示稳定的成功/失败代码和安全原因，不暴露提供商原始响应
或凭据。
周期计划可修改下次运行时间和间隔。报告显示安全、内容质量、效率评分以及文件/页/行位置和高亮证据；
所有界面采用相同阈值：低于 85 为黄色，低于 70 为橙色，低于 55 为红色。对于较慢的本地模型，
AI 分析默认等待 180 秒；提供商错误和报告数据遵循所选界面语言。
每份已保存报告都可从详情页下载为无需网络的独立 HTML、多工作表结构化 Excel 工作簿或分页 PDF。
导出内容使用所选界面语言，同时保留源证据的原始语言。
新扫描会在仪表板和 PDF 证据中正确保留撇号等源标点。自然较短的单文档答案以及仅由规范化产生的
近似位置不会被报告为分块缺陷。

常用运维命令：

```bash
ragscanner jobs list
ragscanner history list
ragscanner worker
```

高级选项请参阅[完整 CLI 参考](docs/cli.md)、[dashboard 指南](docs/dashboard.md)和
[故障排除指南](docs/troubleshooting.md)。

## 隐私和安全

- 本地静态扫描默认离线，不需要 LLM。
- 远程文档或模型访问需要可见配置和明确同意。
- API 密钥存放在 SQLite 之外的受保护机器文件或 `env:` 引用中。
- 持久任务和报告只包含不透明密钥引用。
- 解析内容、模型输出、URL 和报告证据均视为不可信且受到限制。
- 产品生成的界面标签会本地化；来源证据保留原始语言。

公开新集成前，请阅读 [PRIVACY.md](PRIVACY.md)、[SECURITY.md](SECURITY.md) 和
[SourceConnector 契约](docs/source-connector-contract.md)。

## 贡献者

```bash
git clone https://github.com/atakaneser/RAGScanner.git
cd RAGScanner
uv sync --frozen
uv run pytest
```

提交更改前，请按 [CONTRIBUTING.md](CONTRIBUTING.md) 运行 Ruff、格式检查、mypy、测试和
`uv build`。架构边界见 [ARCHITECTURE.md](ARCHITECTURE.md)，当前状态见
[docs/status/current.md](docs/status/current.md)。

## 许可证

Apache-2.0。参见 [LICENSE](LICENSE)。
