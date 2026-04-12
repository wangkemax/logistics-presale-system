@echo off
chcp 65001 >nul
REM ============================================================
REM 物流售前系统 - Docker 镜像离线打包 (Windows)
REM 用法：在项目根目录双击运行此脚本
REM 输出：docker-images 文件夹（拷贝到服务器）
REM ============================================================

echo =========================================
echo   物流售前系统 - 镜像离线打包
echo =========================================
echo.

REM 创建输出目录
if not exist docker-images mkdir docker-images

REM ── 1. 构建业务镜像 ──
echo [1/5] 构建 Backend 镜像...
docker build -t logistics-backend:latest -f backend/Dockerfile backend/
if %errorlevel% neq 0 (echo ❌ Backend 构建失败！ & pause & exit /b 1)
echo   ✅ Backend 构建完成
echo.

echo [2/5] 构建 Frontend 镜像（生产版）...
docker build -t logistics-frontend:latest -f frontend/Dockerfile.prod frontend/
if %errorlevel% neq 0 (echo ❌ Frontend 构建失败！ & pause & exit /b 1)
echo   ✅ Frontend 构建完成
echo.

REM ── 2. 拉取基础设施镜像 ──
echo [3/5] 拉取基础设施镜像...
docker pull postgres:16-alpine
docker pull redis:7-alpine
docker pull minio/minio:latest
echo   ✅ 基础设施镜像就绪
echo.

REM ── 3. 导出所有镜像 ──
echo [4/5] 导出镜像为 tar 文件...

docker save logistics-backend:latest -o docker-images\logistics-backend.tar
echo   ✅ logistics-backend.tar

docker save logistics-frontend:latest -o docker-images\logistics-frontend.tar
echo   ✅ logistics-frontend.tar

docker save postgres:16-alpine -o docker-images\postgres.tar
echo   ✅ postgres.tar

docker save redis:7-alpine -o docker-images\redis.tar
echo   ✅ redis.tar

docker save minio/minio:latest -o docker-images\minio.tar
echo   ✅ minio.tar

echo.

REM ── 4. 复制配置文件 ──
echo [5/5] 复制部署配置文件...
copy /Y .env.production docker-images\.env.example >nul
echo   ✅ .env.example

REM 写入离线版 docker-compose
(
echo # 离线部署版 Docker Compose（使用预构建镜像）
echo.
echo services:
echo   backend:
echo     image: logistics-backend:latest
echo     env_file: .env
echo     environment:
echo       - APP_ENV=production
echo       - APP_DEBUG=false
echo     volumes:
echo       - upload_data:/app/uploads
echo     depends_on:
echo       db:
echo         condition: service_healthy
echo       redis:
echo         condition: service_healthy
echo     deploy:
echo       resources:
echo         limits:
echo           cpus: "2.0"
echo           memory: 2G
echo     healthcheck:
echo       test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
echo       interval: 30s
echo       timeout: 10s
echo       retries: 3
echo       start_period: 40s
echo     restart: always
echo     command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
echo.
echo   frontend:
echo     image: logistics-frontend:latest
echo     ports:
echo       - "3000:3000"
echo     environment:
echo       - NEXT_PUBLIC_API_URL=
echo       - BACKEND_INTERNAL_URL=http://backend:8000
echo     depends_on:
echo       backend:
echo         condition: service_healthy
echo     restart: always
echo.
echo   db:
echo     image: postgres:16-alpine
echo     environment:
echo       POSTGRES_DB: logistics_presale
echo       POSTGRES_USER: ${DB_USER:-postgres}
echo       POSTGRES_PASSWORD: ${DB_PASSWORD:-changeme}
echo     volumes:
echo       - postgres_data:/var/lib/postgresql/data
echo     healthcheck:
echo       test: ["CMD-SHELL", "pg_isready -U ${DB_USER:-postgres}"]
echo       interval: 10s
echo       timeout: 5s
echo       retries: 5
echo     restart: always
echo.
echo   redis:
echo     image: redis:7-alpine
echo     command: redis-server --maxmemory 256mb --maxmemory-policy allkeys-lru --requirepass ${REDIS_PASSWORD:-changeme}
echo     volumes:
echo       - redis_data:/data
echo     healthcheck:
echo       test: ["CMD", "redis-cli", "-a", "${REDIS_PASSWORD:-changeme}", "ping"]
echo       interval: 10s
echo       timeout: 5s
echo       retries: 5
echo     restart: always
echo.
echo   minio:
echo     image: minio/minio:latest
echo     environment:
echo       MINIO_ROOT_USER: ${S3_ACCESS_KEY:-minioadmin}
echo       MINIO_ROOT_PASSWORD: ${S3_SECRET_KEY:-changeme}
echo     volumes:
echo       - minio_data:/data
echo     command: server /data
echo     restart: always
echo.
echo volumes:
echo   postgres_data:
echo   redis_data:
echo   minio_data:
echo   upload_data:
) > docker-images\docker-compose.server.yml
echo   ✅ docker-compose.server.yml

REM 写入服务器导入脚本
(
echo #!/bin/bash
echo set -e
echo echo "导入 Docker 镜像..."
echo docker load -i logistics-backend.tar
echo docker load -i logistics-frontend.tar
echo docker load -i postgres.tar
echo docker load -i redis.tar
echo docker load -i minio.tar
echo echo ""
echo echo "✅ 全部导入完成！"
echo echo ""
echo echo "下一步："
echo echo "  cp .env.example .env"
echo echo "  nano .env"
echo echo "  docker compose -f docker-compose.server.yml up -d"
) > docker-images\import.sh
echo   ✅ import.sh

echo.
echo =========================================
echo   打包完成！
echo =========================================
echo.
echo   输出目录：docker-images\
echo.
echo   部署步骤：
echo   1. 把 docker-images 整个文件夹拷到服务器
echo   2. cd docker-images
echo   3. bash import.sh
echo   4. cp .env.example .env ^&^& nano .env
echo   5. docker compose -f docker-compose.server.yml up -d
echo.
pause
