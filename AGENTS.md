# AGENTS.md

本文件供 Codex 和其他 AI 编程助手在本仓库中工作时阅读。它记录了本项目从 0 到 1 建设过程中已经确定的产品范围、技术约束、本地命令、部署方式和用户偏好。

## 项目概述

本仓库是公司测试团队内部使用的接口自动化测试平台。

第一版 MVP 的目标是打通完整的接口回归测试闭环：

1. 管理项目和环境。
2. 手工维护接口定义。
3. 配置单接口用例和场景用例。
4. 在请求中渲染变量。
5. 手动触发接口测试执行。
6. 执行页面化配置的断言。
7. 使用 JSONPath 从响应中提取变量。
8. 保存执行结果并生成 HTML 报告。
9. 查询操作日志、执行日志和异常日志。

平台第一版服务公司内部测试团队，不做复杂组织架构、审批流、定时任务、CI/CD 触发等能力，除非用户后续明确要求。

## 正式项目路径

当前正式项目根目录是：

```text
D:\workspace_aicoding\APITestPlatform
```

项目最初创建在 Codex 的 C 盘工作目录：

```text
C:\Users\Lenovo\Documents\Codex\2026-07-26\wge
```

之后已经整体迁移到 D 盘。后续开发、测试、部署都应以 D 盘路径为准。

## 技术栈

后端：

- Python
- FastAPI
- SQLAlchemy 2.x
- Pydantic
- PyMySQL
- httpx
- jsonpath-ng
- passlib + bcrypt

前端：

- Vue 3
- TypeScript
- Vite
- Ant Design Vue
- @ant-design/icons-vue
- axios

数据库：

- MySQL 8.4

部署：

- Docker Compose
- 目标服务为 backend、frontend、mysql
- 第一版目标架构不使用 Redis 和 RQ

## 重要架构决策

### 仅使用 MySQL

项目方案已经调整为移除 Redis 和 RQ。MySQL 是第一版唯一外部运行依赖。

后续开发必须遵守：

- 不要重新引入 Redis。
- 不要重新引入 RQ。
- 不要要求部署独立 Redis 服务。
- 执行任务存储在 MySQL 的 `execution_task` 表中。
- 执行结果存储在 MySQL 的 `execution_result` 表中。
- HTML 报告从 MySQL 相关执行记录中保存或读取。

如果当前代码或 Docker 配置中还存在 Redis、RQ、`worker`、`task_queue_worker` 等内容，优先视为历史遗留待清理项，除非用户明确要求保留。

### 角色和权限

平台只包含两类角色：

- 管理员：`admin`
- 测试人员：`tester`

测试人员拥有以下功能：

- 项目配置
- 平台管理
- 接口管理
- 用例管理
- 执行中心
- 报告查看
- 日志查看

管理员拥有测试人员的全部功能，并且只额外拥有“创建账号”权限。

重要规则：

- 管理员不是拥有大量额外业务权限的超级角色。
- 管理员和测试人员在业务功能上基本一致。
- 管理员只比测试人员多账号创建权限。
- 测试人员不能创建账号。
- 测试人员账号由管理员创建后下发给公司测试团队成员。

### 登录和认证

第一版使用平台自建账号体系。

不要在第一版中主动引入：

- LDAP
- OAuth
- SSO
- JWT 扩展方案

登录态可以采用后端 Session 或内部 Token 机制，保持简单可控。

本地默认管理员账号：

```text
用户名：admin
密码：admin123
```

### 接口管理

接口定义仅支持手工录入。

不要添加以下导入能力，除非用户后续明确要求：

- Swagger 导入
- OpenAPI 导入
- Postman 导入

接口定义字段应包含：

- 所属项目
- 所属模块
- 接口名称
- 请求方法
- 接口路径
- headers
- query 参数
- body 参数
- 接口描述

接口定义和测试用例要保持分离：

- 接口定义描述 API 本身。
- 测试用例描述具体入参、变量、断言、提取规则和执行配置。

### query 和 body 的含义

`query` 是 URL 后面的查询参数，也就是 `?` 后面的内容。

示例：

```text
/users?page=1&size=20
```

`body` 是请求体，常见于 `POST`、`PUT`、`PATCH` 请求。

示例：

```json
{"name":"张三"}
```

### 断言规则

断言必须通过页面配置，不开放任意脚本断言。

第一版支持以下断言类型：

- HTTP 状态码断言，例如 `status_code == 200`
- JSONPath 字段值断言，例如 `$.code == 0`
- JSONPath 字段存在断言，例如 `$.data.id exists`
- JSONPath 字段非空断言，例如 `$.data.token not_empty`
- 响应时间断言，例如 `duration < 1000ms`
- 响应文本包含断言，例如 body contains `success`

断言结果应逐条展示：

- 是否通过
- 实际值
- 期望值
- 失败原因

### 变量和数据依赖

平台支持在请求 URL、headers、query、body 中引用变量。

变量语法：

```text
${变量名}
```

变量类型：

- 环境级全局变量，例如 host、默认账号、公共 appId
- 执行过程临时变量，只在当前执行链路中有效

响应提取使用 JSONPath。

示例：

```text
$.data.token -> token
```

场景用例中，上一步提取的变量应能传递给后续步骤使用。

### 测试报告

测试报告只保留 HTML 格式。

不要添加 PDF 导出，除非用户明确要求。

报告应包含：

- 任务信息
- 项目
- 环境
- 执行人
- 开始时间
- 结束时间
- 总耗时
- 通过率
- 请求快照
- 响应快照
- 断言明细
- 错误信息
- 场景用例步骤明细
- 失败步骤和失败原因

### 日志管理

公司没有统一日志系统，平台自行管理日志。

第一版方向：

- 关键操作日志落库。
- 执行异常日志落库。
- 服务运行日志可以写本地文件。
- 日志支持按时间、用户、模块、任务 ID 查询。

## 数据库规则

所有数据库表最后两个字段统一为：

```text
create_date
update_date
```

展示格式：

```text
yyyy-MM-dd HH:mm:ss
```

SQLAlchemy 模型中应保持统一的创建时间和更新时间自动写入逻辑。新增业务表时，不要随意使用 `created_at`、`updated_at` 等其他字段名，除非为了兼容已有表结构并明确说明原因。

核心表包括：

- `user`
- `project`
- `environment`
- `api_definition`
- `test_case`
- `scenario_case`
- `test_suite`
- `execution_task`
- `execution_result`
- `operation_log`

## 修复bug与需求变更开发规则

每次有新修改（需求或bug修复）后，都需要重构docker以供测试。如果仅前端有改动则重构前端docker并重启，如果仅后端有改动则重构后端docker并重启，保证最小原则。如果都有改动则都需要重构并重启。

## 本地常用命令

后端测试：

```powershell
D:\workspace_aicoding\APITestPlatform\.venv\Scripts\python.exe -m pytest D:\workspace_aicoding\APITestPlatform\backend\tests -q
```

后端语法检查：

```powershell
D:\workspace_aicoding\APITestPlatform\.venv\Scripts\python.exe -m compileall D:\workspace_aicoding\APITestPlatform\backend\app
```

前端构建：

```powershell
cd D:\workspace_aicoding\APITestPlatform\frontend
pnpm rebuild esbuild
pnpm build
```

Docker Compose 启动：

```powershell
cd D:\workspace_aicoding\APITestPlatform
docker compose up --build
```

Docker Compose 停止：

```powershell
cd D:\workspace_aicoding\APITestPlatform
docker compose down
```

查看正在运行的容器：

```powershell
docker ps
```

## Docker 和 MySQL 说明

Docker Desktop 计划安装在 Windows 上，使用 WSL 2 后端。

Docker Desktop 程序安装目录：

```text
D:\Program Files\Docker\Docker
```

注意：Docker 程序安装目录和镜像、容器、数据卷实际占用目录不是一回事。镜像和容器数据可能仍在 WSL 或 Docker 自己的数据目录中。

项目默认 MySQL 配置：

```text
数据库：api_test_platform
用户名：api_test
密码：api_test
本地 root 密码：root
```

Docker Compose 默认值应与这些配置保持一致，除非用户通过 `.env` 或环境变量覆盖。

## 已知项目历史和注意事项

- 本项目是通过 Codex 从 0 到 1 建设的接口自动化测试平台 MVP。
- 项目已经从 C 盘 Codex 工作目录迁移到 `D:\workspace_aicoding\APITestPlatform`。
- 迁移完成后，原 C 盘项目文件已经按用户确认删除。
- 用户已经手动安装 MySQL 8.4，并完成过连接验证。
- 项目方案后续调整为移除 Redis，仅使用 MySQL。
- 如果当前代码中还存在 Redis/RQ、`worker`、`task_queue_worker`，在继续开发前应确认是否为遗留状态。
- 之前部分中文文档曾出现编码乱码，新写入文档请尽量使用 UTF-8。

## 编码和实现规范

- 优先遵循当前项目已有 FastAPI router、service、SQLAlchemy model、Vue component 写法。
- 修改范围要聚焦用户当前需求，不做无关重构。
- 对请求体、断言配置、响应提取等结构化数据，优先使用 JSON/结构化解析，不要用脆弱的字符串拼接和截取。
- 前端是内部测试平台，界面应偏实用、清晰、信息密度合理，不要做成营销页。
- 前端组件统一使用 Ant Design Vue，图标统一使用 @ant-design/icons-vue；不要重新引入 Element Plus。
- 页面视觉遵循 Ant Design Pro 的组件语义和 Vben Admin 的后台布局组织：深色侧栏、清晰操作层级、紧凑查询表单、表格工具栏和克制的内容分区。
- 不引入完整 Vben Admin、Pinia、Vue Router 或 Tailwind，除非用户后续明确要求进行工程架构重构。
- API 行为要明确、稳定、方便前端调用。
- 未经用户确认，不要新增额外基础设施依赖。

## 验证要求

后端改动后至少运行：

```powershell
D:\workspace_aicoding\APITestPlatform\.venv\Scripts\python.exe -m pytest D:\workspace_aicoding\APITestPlatform\backend\tests -q
```

前端改动后至少运行：

```powershell
cd D:\workspace_aicoding\APITestPlatform\frontend
pnpm build
```

Docker 可用时，完整本地验证：

```powershell
cd D:\workspace_aicoding\APITestPlatform
docker compose up --build
```

然后验证：

- 前端页面可以打开。
- 后端 `/health` 返回正常。
- 默认管理员可以登录。
- 主要页面可以加载。
- 可以完成创建项目、配置环境、录入接口、创建用例、执行测试、查看 HTML 报告的基本流程。

## 用户偏好和明确约束

- 使用 MySQL，不使用 Redis。
- 角色只有管理员和测试人员。
- 管理员只比测试人员多“创建账号”权限。
- 测试人员拥有平台主要业务功能，但不能创建账号。
- 接口定义仅支持手工录入。
- 测试报告只保留 HTML。
- 第一版不接 LDAP、OAuth、SSO，也不把 JWT 扩展方案作为规划内容。
- 平台自行管理日志。
- 所有数据库表最后两个字段必须是 `create_date` 和 `update_date`。
- 正式项目目录是 `D:\workspace_aicoding\APITestPlatform`。
