# 可信人格记忆Agent

当前项目使用 Docker Compose 启动 Next.js 前端、FastAPI 后端、PostgreSQL、Redis、MinIO 和 mock worker。完整范围、验证入口和交接记录见 `docs/README.md`、`docs/feature-list.json` 和 `docs/progress.md`。

## 本地调试

```powershell
docker compose up --build
```

- 前端：http://localhost:3000
- 后端健康检查：http://localhost:8000/health

## ECS 直连端口部署

当前云服务器方案不加 Nginx、域名或 HTTPS，直接对外提供：

- 网页：`http://<ECS公网IP>:3000`
- 后端健康检查：`http://<ECS公网IP>:8000/health`

部署前在 ECS 仓库根目录创建未提交的 `.env/runtime.env`，并把 `<ECS公网IP>` 替换成阿里云 ECS 实际公网 IPv4，不要保留尖括号：

```env
FRONTEND_URL=http://<ECS公网IP>:3000
BACKEND_URL=http://<ECS公网IP>:8000
NEXT_PUBLIC_API_BASE_URL=http://<ECS公网IP>:8000
JWT_SECRET=<生成强随机字符串>
```

阿里云 ECS 安全组放行入站 TCP `3000` 和 `8000`。不要对公网放行 `15432`、`6379`、`9000` 或 `9001`；Compose 默认把数据库、Redis 和 MinIO 宿主端口绑定到 `127.0.0.1`。

```bash
docker compose --env-file .env/runtime.env up --build -d
```

如果公网 IP 或后端端口变化，需要重新执行带 `--build` 的 Compose 命令，因为 `NEXT_PUBLIC_API_BASE_URL` 会在 Next.js 构建期写入客户端包。
