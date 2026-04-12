#!/bin/bash
# ============================================================
# 物流售前系统 - Docker 镜像离线打包脚本
# 用法：在有 Docker 的机器上执行此脚本
# 输出：logistics-images.tar.gz（拷贝到服务器导入）
# ============================================================

set -e

echo "========================================="
echo "  物流售前系统 - 镜像离线打包"
echo "========================================="
echo ""

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

OUTPUT_DIR="$SCRIPT_DIR/docker-images"
mkdir -p "$OUTPUT_DIR"

# ── 1. 构建业务镜像 ──
echo "[1/5] 构建 Backend 镜像..."
docker build -t logistics-backend:latest -f backend/Dockerfile backend/
echo "  ✅ Backend 构建完成"

echo ""
echo "[2/5] 构建 Frontend 镜像（生产版）..."
docker build -t logistics-frontend:latest -f frontend/Dockerfile.prod frontend/
echo "  ✅ Frontend 构建完成"

# ── 2. 拉取基础设施镜像 ──
echo ""
echo "[3/5] 拉取基础设施镜像..."
docker pull postgres:16-alpine
docker pull redis:7-alpine
docker pull minio/minio:latest
echo "  ✅ 基础设施镜像就绪"

# ── 3. 导出所有镜像 ──
echo ""
echo "[4/5] 导出镜像为 tar 文件..."

docker save logistics-backend:latest -o "$OUTPUT_DIR/logistics-backend.tar"
echo "  ✅ logistics-backend.tar"

docker save logistics-frontend:latest -o "$OUTPUT_DIR/logistics-frontend.tar"
echo "  ✅ logistics-frontend.tar"

docker save postgres:16-alpine -o "$OUTPUT_DIR/postgres.tar"
echo "  ✅ postgres.tar"

docker save redis:7-alpine -o "$OUTPUT_DIR/redis.tar"
echo "  ✅ redis.tar"

docker save minio/minio:latest -o "$OUTPUT_DIR/minio.tar"
echo "  ✅ minio.tar"

# ── 4. 打包成一个压缩文件 ──
echo ""
echo "[5/5] 压缩打包..."

# 复制部署所需的配置文件
cp docker-compose.server.yml "$OUTPUT_DIR/"
cp .env.production "$OUTPUT_DIR/.env.example"

# 创建服务器端导入脚本
cat > "$OUTPUT_DIR/import.sh" << 'IMPORT_EOF'
#!/bin/bash
# ============================================================
# 服务器端镜像导入脚本
# 用法：将 docker-images 文件夹拷贝到服务器后执行此脚本
# ============================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "========================================="
echo "  导入 Docker 镜像"
echo "========================================="

echo "[1/5] 导入 Backend..."
docker load -i logistics-backend.tar
echo "  ✅ Done"

echo "[2/5] 导入 Frontend..."
docker load -i logistics-frontend.tar
echo "  ✅ Done"

echo "[3/5] 导入 PostgreSQL..."
docker load -i postgres.tar
echo "  ✅ Done"

echo "[4/5] 导入 Redis..."
docker load -i redis.tar
echo "  ✅ Done"

echo "[5/5] 导入 MinIO..."
docker load -i minio.tar
echo "  ✅ Done"

echo ""
echo "========================================="
echo "  所有镜像导入完成！"
echo "========================================="
echo ""
echo "下一步操作："
echo ""
echo "  1. 编辑 .env 文件："
echo "     cp .env.example .env"
echo "     nano .env"
echo ""
echo "  2. 启动所有服务："
echo "     docker compose -f docker-compose.server.yml up -d"
echo ""
echo "  3. 检查状态："
echo "     docker compose -f docker-compose.server.yml ps"
echo ""
IMPORT_EOF

chmod +x "$OUTPUT_DIR/import.sh"

# 创建离线版 docker-compose（使用 image 而非 build）
cat > "$OUTPUT_DIR/docker-compose.server.yml" << 'COMPOSE_EOF'
# ============================================================
# 离线部署版 Docker Compose（使用预构建镜像，无需 build）
# ============================================================

services:
  # ── Backend API ──
  backend:
    image: logistics-backend:latest
    env_file: .env
    environment:
      - APP_ENV=production
      - APP_DEBUG=false
    volumes:
      - upload_data:/app/uploads
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    deploy:
      resources:
        limits:
          cpus: "2.0"
          memory: 2G
        reservations:
          cpus: "0.5"
          memory: 512M
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    restart: always
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4

  # ── Frontend ──
  frontend:
    image: logistics-frontend:latest
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=
      - BACKEND_INTERNAL_URL=http://backend:8000
    depends_on:
      backend:
        condition: service_healthy
    restart: always

  # ── PostgreSQL ──
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: logistics_presale
      POSTGRES_USER: ${DB_USER:-postgres}
      POSTGRES_PASSWORD: ${DB_PASSWORD:-changeme}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    deploy:
      resources:
        limits:
          cpus: "1.0"
          memory: 1G
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DB_USER:-postgres}"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: always

  # ── Redis ──
  redis:
    image: redis:7-alpine
    command: redis-server --maxmemory 256mb --maxmemory-policy allkeys-lru --requirepass ${REDIS_PASSWORD:-changeme}
    volumes:
      - redis_data:/data
    deploy:
      resources:
        limits:
          cpus: "0.5"
          memory: 512M
    healthcheck:
      test: ["CMD", "redis-cli", "-a", "${REDIS_PASSWORD:-changeme}", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: always

  # ── MinIO ──
  minio:
    image: minio/minio:latest
    environment:
      MINIO_ROOT_USER: ${S3_ACCESS_KEY:-minioadmin}
      MINIO_ROOT_PASSWORD: ${S3_SECRET_KEY:-changeme}
    volumes:
      - minio_data:/data
    command: server /data
    restart: always

volumes:
  postgres_data:
  redis_data:
  minio_data:
  upload_data:
COMPOSE_EOF

# 打包整个 docker-images 文件夹
cd "$SCRIPT_DIR"
tar -czf logistics-images.tar.gz docker-images/

SIZE=$(du -h logistics-images.tar.gz | cut -f1)

echo ""
echo "========================================="
echo "  打包完成！"
echo "========================================="
echo ""
echo "  输出文件：logistics-images.tar.gz ($SIZE)"
echo ""
echo "  部署步骤："
echo "  ─────────────────────────────────────"
echo "  1. 把 logistics-images.tar.gz 拷贝到服务器"
echo "  2. 在服务器上解压："
echo "     tar -xzf logistics-images.tar.gz"
echo "     cd docker-images"
echo ""
echo "  3. 导入镜像："
echo "     bash import.sh"
echo ""
echo "  4. 配置环境变量："
echo "     cp .env.example .env"
echo "     nano .env"
echo ""
echo "  5. 启动服务："
echo "     docker compose -f docker-compose.server.yml up -d"
echo ""
echo "  6. 检查状态："
echo "     docker compose -f docker-compose.server.yml ps"
echo ""
echo "  你的反代指向 localhost:3000 即可"
echo "========================================="
