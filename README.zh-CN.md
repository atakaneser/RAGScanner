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

数据源和任务表单只列出上方已实现的内容路径。仅凭产品名或容器名无法扫描向量数据库：
真正的连接器必须枚举已授权的集合，并读取有限的 payload 文本及稳定的文档/分块来源信息。
目前尚无通过验收的向量库连接器，因此 Qdrant、Chroma、Weaviate、Milvus、pgvector
及类似平台不会作为可扫描数据源提供。

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

任务创建采用四步引导流程：选择已连接或手动数据源、仅填写该数据源所需信息、设置单次或周期
运行时间，并按需启用 AI。周期任务可指定首次本地日期和时间。本地 AI 提供商会自动检查；已验证
模型集中显示在一个选择框中，端点、凭据和手动模型名称保留在可选连接设置内。

远程网站扫描拒绝重定向和跨源站点地图项，不执行脚本，并限制页面数、响应大小和超时。
经过身份验证的 Microsoft Graph 站点/库发现是另行规划的连接器。

## RAG 配置与验证

每份新报告都会记录所选工作负载配置，并将当前分块设置与观测到的分块统计进行比较。系统会针对
事实检索、通用问答、政策/流程、长上下文研究、代码或表格给出可解释的起始范围、重叠量和初始
检索 top-k。不存在通用的最佳分块大小；报告始终列出需要通过代表性查询验证的检索、回答、引用、
延迟和成本指标。

直接或排队的 CLI 扫描可使用 `--rag-profile` 及可选的模型上下文/top-k 参数，也可在
`ragscanner.toml` 中设置 `[rag]`。详情见 [RAG configuration advice](docs/rag-configuration-advice.md)。
使用 `ragscanner quality calibrate` 可评估本地标注语料；见
[Quality calibration](docs/quality-calibration.md)。内置六语言语料仅用于回归检查，并不能证明生产准确率。

## AI 辅助报告

AI 分析是可选建议，不替代确定性发现。设置会从 Ollama、LM Studio、LocalAI 或 vLLM 中检测
已安装模型，不会继续保留过期模型名。远程提供商需要 HTTPS、外部凭据引用和每次扫描的明确同意。

系统只发送有界且已脱敏的报告上下文，不发送原始文档。静态安全发现及同一受影响来源中其他发现的
原始证据会被省略，但保留规则、文件/页/行、影响和确定性修复建议。上下文全局限制为 18,000 个字符，
先按最高严重性、再按受影响分块数选择组；每个选中组最多包含四个证据位置，覆盖说明会指出仍保留在
完整确定性报告中的低优先级组。这样可避免文档中的指令变成模型指令。

首次输出必须通过版本化架构验证。RAGScanner 可从常见本地模型包装（JSON 代码块、推理前缀或序列化
JSON 字符串）中接受一个无歧义的分析对象。若响应无效，系统会用不含证据片段、最多 6,500 个字符的
紧凑上下文重试一次，并请求纯文本而非再次要求同一模型生成 JSON。可用文本会在本地放入经过验证的结果
封装。空白、损坏、语言错误或与已验证严重性冲突的恢复响应，只会依据已验证报告事实生成所选语言的
摘要；报告会显示此限制，而不会以 `ai_output_invalid` 终止。Ollama 为分析预留 16,384 token 的
上下文窗口。详细 AI 操作仅从结构化响应接受，并且只能绑定真实规则 ID。

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
变体测试还会避免生成的标题、列表、表格、代码、重叠、无大小写文字和过小词汇样本在缺少源证据时
产生发现项。

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
