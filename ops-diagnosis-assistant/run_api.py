#!/usr/bin/env python3
"""
运维诊断助手API启动脚本
"""
import uvicorn
import os

if __name__ == "__main__":
    print("🚀 启动运维智能诊断助手 API...")
    print("📍 API文档地址: http://localhost:8000/docs")
    print("📍 健康检查: http://localhost:8000/health")
    
    uvicorn.run(
        "src.api.main:app",
        host="0.0.0.0",  # 允许外部访问
        port=8000,
        reload=True,      # 开发模式，代码变更自动重启
        log_level="info",
        access_log=True
    )