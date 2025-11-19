#!/usr/bin/env python3
"""
运维诊断助手高级API启动脚本
"""
import uvicorn
import os
from dotenv import load_dotenv

load_dotenv()

if __name__ == "__main__":
    print("🚀 启动运维智能诊断助手高级API...")
    print("📍 API文档地址: http://localhost:8000/docs")
    print("📍 健康检查: http://localhost:8000/health")
    print("🔐 API密钥: default_secret_key (请在.env中配置)")
    
    uvicorn.run(
        "src.api.advanced_main:app",
        host=os.getenv("API_HOST", "0.0.0.0"),
        port=int(os.getenv("API_PORT", 8000)),
        reload=True,
        log_level="info",
        access_log=True
    )