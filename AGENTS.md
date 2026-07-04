# AGENTS.md

本文件约束 agent 在可信人格记忆Agent仓库中的阅读顺序、编辑边界和验证方式。除非用户明确要求，否则不要把待填写模板内容当作已确认事实。

## Read First

- 先读 [docs/README.md](docs/README.md)，了解文档地图、当前状态和验证入口。
- 再读 [docs/可信人格记忆Agent_mvp_prd.md](docs/可信人格记忆Agent_mvp_prd.md)，确认产品范围、MVP 边界和验收标准。
- 再读 [docs/feature-list.json](docs/feature-list.json)，确认当前功能状态、依赖和证据。
- 再读 [docs/progress.md](docs/progress.md)，继承当前会话状态、风险、下一步和验证记录。
- 如需面向用户解释操作流程，读 [docs/平台说明.md](docs/平台说明.md)。
- 如需核对 PRD 与代码事实，读 [docs/prd-checklist.md](docs/prd-checklist.md)。

## Constraint Workflow

- 将 `feature-list.json` 视为功能范围账本。新增、完成、阻塞或重开功能切片时，同步更新状态、依赖和证据。
- 将 `progress.md` 视为交接账本。每次会话收尾前更新当前状态、活跃风险、验证证据、改动文件和下一步。
- 将 `docs/init.sh` 视为统一验证入口。当前它会校验 JSON，并在依赖已安装时运行后端测试、前端 test/lint/build 和 `docker compose config`。
- 如果任务改变产品范围、验收标准、运行命令或 agent 规则，同步检查 `docs/README.md`、PRD、`feature-list.json`、`progress.md`、`prd-checklist.md` 和本文件是否需要更新。
- 不要新建平行的范围说明或交接文档，除非用户明确要求。优先维护现有 harness。

## Non-Negotiable Boundaries

- 不要从其他项目复制领域内容、运行命令、密钥说明、数据源说明、模型链路或业务术语。
- 不要声明尚未由代码、配置、测试或用户确认支持的能力。
- 不要把 `待填写` 项改成推断事实。
- 不要扩大产品范围；如发现需要新增能力，先更新 PRD 和 `feature-list.json`。
- 不要删除用户已有内容，除非本次任务明确要求并且已经确认该内容属于本次改动范围。

## Repository Map

当前已确认的仓库结构：

- [docs/README.md](docs/README.md)：文档地图、维护流程和当前验证入口。
- [docs/可信人格记忆Agent_mvp_prd.md](docs/可信人格记忆Agent_mvp_prd.md)：MVP PRD 模板。
- [docs/feature-list.json](docs/feature-list.json)：功能范围账本。
- [docs/progress.md](docs/progress.md)：会话进度和 handoff。
- [docs/prd-checklist.md](docs/prd-checklist.md)：PRD 与代码事实对照清单。
- [docs/平台说明.md](docs/平台说明.md)：Milestone 0 使用与验证说明。
- [docs/init.sh](docs/init.sh)：Milestone 0 统一验证脚本。
- [backend/](backend/)：FastAPI 后端、SQLAlchemy/Alembic 模型迁移、认证 API、Provider Gateway 骨架和测试。
- [backend/docker-entrypoint.sh](backend/docker-entrypoint.sh)：Compose 后端容器启动前执行 Alembic 迁移，再启动 Uvicorn。
- [frontend/](frontend/)：Next.js 前端页面骨架、API 路径配置和前端测试/lint/build 脚本。
- [docker-compose.yml](docker-compose.yml)：frontend、backend、postgres、redis、minio 和 mock worker 的本地开发拓扑。
- [backend/.dockerignore](backend/.dockerignore)、[frontend/.dockerignore](frontend/.dockerignore)：隔离 Docker build context，避免本地依赖、缓存或环境文件进入镜像构建。

后续业务功能目录随里程碑推进补充，不要提前声明未实现能力。

## Commands Agents Should Prefer

- Windows Git Bash 自检入口：`& "C:\Program Files\Git\bin\bash.exe" ./docs/init.sh`
- Bash 自检入口：`bash ./docs/init.sh`
- JSON 校验：`python -m json.tool docs/feature-list.json`
- 后端测试：`python -m pytest backend/tests -q`
- 前端依赖安装：`npm.cmd --prefix frontend install`
- 前端测试：`npm.cmd --prefix frontend run test`
- 前端 lint：`npm.cmd --prefix frontend run lint`
- 前端构建：`npm.cmd --prefix frontend run build`
- Compose 配置校验：`docker compose config`
- 本地开发拓扑：`docker compose up --build`
- 内容清洗检查示例：`rg "<不应出现的项目专有词>" docs AGENTS.md`

PowerShell 中运行 npm 命令时使用 `npm.cmd`，不要使用 PowerShell 解析到的 `npm` 脚本。不要提交 `.env/runtime.env`、真实密钥、`node_modules`、`__pycache__` 或其他生成缓存。

## Editing Guidance

- 优先做小而明确的改动。每一行修改都应能追溯到用户请求或当前任务。
- 保持模板语气中立，不把假设包装成事实。
- 修改文档时优先链接已有文档，不重复大段复制。
- 修改 `feature-list.json` 后必须运行 JSON 校验。
- 修改启动、验证或交接规则后必须检查 `docs/README.md`、`docs/progress.md` 和 `docs/prd-checklist.md` 是否一致。
- 修改 Compose、Dockerfile 或 harness 后至少运行 `docker compose config` 和 `docs/init.sh`；如果依赖已安装，还要运行后端与前端单项验证。
- 发现无关问题时记录在交接或回复中，不要顺手重构或删除。

## Validation Expectations

- 文档或 harness 变化至少运行：
  - `python -m json.tool docs/feature-list.json`
  - `bash ./docs/init.sh` 或 Windows Git Bash 等价命令
- 后端、前端或 Compose 变化还要运行对应单项命令：
  - `python -m pytest backend/tests -q`
  - `npm.cmd --prefix frontend run test`
  - `npm.cmd --prefix frontend run lint`
  - `npm.cmd --prefix frontend run build`
  - `docker compose config`
- 任何新增命令都要同步写入 `docs/README.md`、`docs/init.sh` 和必要的 `progress.md` 记录。
