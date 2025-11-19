#!/bin/bash

set -e

echo "🚀 开始部署运维智能诊断助手..."

# 检查Docker是否安装
if ! command -v docker &> /dev/null; then
    echo "❌ Docker未安装，请先安装Docker"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose未安装，请先安装Docker Compose"
    exit 1
fi

# 创建环境文件
if [ ! -f .env ]; then
    echo "📝 创建环境配置文件..."
    cat > .env << EOF
# 数据库配置
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=ops_knowledge
POSTGRES_USER=postgres
POSTGRES_PASSWORD=password

# Elasticsearch配置
ELASTICSEARCH_HOST=elasticsearch
ELASTICSEARCH_PORT=9200

# Redis配置
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=

# Celery配置
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0

# Ollama配置
OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_MODEL=llama3.1:8b

# 应用配置
LOG_LEVEL=INFO
API_HOST=0.0.0.0
API_PORT=8000

# 安全配置
API_KEY=default_secret_key

# 前端配置
API_BASE_URL=http://localhost:8000
EOF
    echo "✅ 环境配置文件创建完成"
fi

# 构建和启动服务
echo "🐳 启动Docker服务..."
docker-compose down  # 停止现有服务
docker-compose up -d --build

# 等待服务启动
echo "⏳ 等待服务启动..."
sleep 30

# 检查服务状态
echo "🔍 检查服务状态..."
services=("postgres" "elasticsearch" "redis" "api" "celery-worker" "frontend")

for service in "${services[@]}"; do
    if docker-compose ps | grep -q "$service.*Up"; then
        echo "✅ $service 服务运行正常"
    else
        echo "❌ $service 服务启动失败"
        docker-compose logs "$service"
        exit 1
    fi
done

# 显示访问信息
echo ""
echo "🎉 部署完成！"
echo ""
echo "📊 服务访问信息："
echo "   🔧 前端界面: http://localhost:7860"
echo "   📚 API文档: http://localhost:8000/docs"
echo "   ❤️  健康检查: http://localhost:8000/health"
echo ""
echo "🔑 默认API密钥: default_secret_key"
echo ""
echo "📝 日志查看："
echo "   docker-compose logs -f api          # API服务日志"
echo "   docker-compose logs -f celery-worker # Celery Worker日志"
echo "   docker-compose logs -f frontend     # 前端日志"
echo ""
echo "🛑 停止服务："
echo "   docker-compose down"
echo ""
echo "🔧 故障排除："
echo "   如果Ollama连接失败，请确保Ollama服务在主机上运行"
echo "   并检查 .env 文件中的 OLLAMA_BASE_URL 配置"

# 初始化数据库（如果需要）
echo ""
echo "🗃️ 初始化知识库..."
docker-compose exec api python -c "
import sys
sys.path.append('/app/src')
from data.sample_data import init_database, insert_sample_data, verify_data
if init_database() and insert_sample_data():
    verify_data()
    print('✅ 知识库初始化完成')
else:
    print('❌ 知识库初始化失败')
"

echo ""
echo "✨ 运维智能诊断助手部署完成！"