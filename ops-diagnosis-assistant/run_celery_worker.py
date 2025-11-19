#!/usr/bin/env python3
"""
Celery Worker启动脚本
"""
import os
from dotenv import load_dotenv

load_dotenv()

if __name__ == "__main__":
    print("👷 启动Celery Worker...")
    print("📍 Broker: ", os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0"))
    print("📍 并发数: 2")
    
    os.system("celery -A src.celery_app worker --loglevel=info --concurrency=2")