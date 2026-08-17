# 测试平台

面向公司测试团队的测试平台 MVP。平台支持项目/环境配置、接口手工录入、用例管理、变量提取、页面化断言、手动执行和 HTML 报告。

## 技术栈

- 后端：FastAPI、SQLAlchemy、Pydantic、httpx
- 前端：Vue 3、TypeScript、Vite、Element Plus
- 数据库：MySQL
- 部署：Docker Compose

## 本地启动

```powershell
docker compose up --build
```

服务地址：

- 前端：http://localhost:5173
- 后端：http://localhost:8000
- API 文档：http://localhost:8000/docs

默认管理员账号：

- 用户名：`admin`
- 密码：`admin123`

常用 Docker 环境变量可通过命令行或 `.env` 覆盖：

- `FRONTEND_PORT`：前端端口，默认 `5173`
- `BACKEND_PORT`：后端端口，默认 `8000`
- `MYSQL_PORT`：MySQL 端口，默认 `3306`
- `MYSQL_ROOT_PASSWORD`、`MYSQL_DATABASE`、`MYSQL_USER`、`MYSQL_PASSWORD`
- `APP_SECRET`、`ADMIN_USERNAME`、`ADMIN_PASSWORD`

## 权限模型

- 测试人员：项目配置、平台管理、接口管理、用例管理、执行中心、报告查看、日志查看。
- 管理员：拥有测试人员全部功能，并额外拥有创建账号权限。

## 关键规则

- 接口定义仅支持手工录入。
- 测试报告仅保留 HTML 格式。
- 断言通过页面配置，不开放脚本断言。
- 所有业务表最后两个字段为 `create_date`、`update_date`，展示格式为 `yyyy-MM-dd HH:mm:ss`。
