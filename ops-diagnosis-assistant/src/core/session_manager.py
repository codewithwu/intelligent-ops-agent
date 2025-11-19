import json
import redis
import os
from typing import Optional, Dict, Any
from dotenv import load_dotenv
import logging

load_dotenv()

logger = logging.getLogger(__name__)

class RedisSessionManager:
    def __init__(self):
        self.redis_client = redis.Redis(
            host=os.getenv('REDIS_HOST', 'localhost'),
            port=int(os.getenv('REDIS_PORT', 6379)),
            db=int(os.getenv('REDIS_DB', 0)),
            password=os.getenv('REDIS_PASSWORD', None),
            decode_responses=True
        )
        self.session_prefix = "diagnosis_session:"
        self.session_ttl = 3600  # 1小时过期
        self.redis_ping()
    
    def redis_ping(self):
        if self.redis_client.ping():
            print(f"redis 连接成功")
        else:
            raise ValueError("redis 连接失败")

    def _get_session_key(self, session_id: str) -> str:
        return f"{self.session_prefix}{session_id}"

    def save_session(self, session_id: str, session_data: Dict[str, Any]) -> bool:
        """保存会话数据到Redis"""
        try:
            key = self._get_session_key(session_id)
            serialized_data = json.dumps(session_data, default=str)
            self.redis_client.setex(key, self.session_ttl, serialized_data)
            logger.info(f"✅ 会话保存成功: {session_id}")
            return True
        except Exception as e:
            logger.error(f"❌ 会话保存失败 {session_id}: {e}")
            return False

    def load_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """从Redis加载会话数据"""
        try:
            key = self._get_session_key(session_id)
            data = self.redis_client.get(key)
            if data:
                session_data = json.loads(data)
                # 更新TTL
                self.redis_client.expire(key, self.session_ttl)
                logger.info(f"✅ 会话加载成功: {session_id}")
                return session_data
            else:
                logger.info(f"🔍 会话不存在: {session_id}")
                return None
        except Exception as e:
            logger.error(f"❌ 会话加载失败 {session_id}: {e}")
            return None

    def delete_session(self, session_id: str) -> bool:
        """删除会话"""
        try:
            key = self._get_session_key(session_id)
            result = self.redis_client.delete(key)
            logger.info(f"🗑️ 会话删除: {session_id}, 结果: {result}")
            return result > 0
        except Exception as e:
            logger.error(f"❌ 会话删除失败 {session_id}: {e}")
            return False

    def session_exists(self, session_id: str) -> bool:
        """检查会话是否存在"""
        try:
            key = self._get_session_key(session_id)
            return self.redis_client.exists(key) > 0
        except Exception as e:
            logger.error(f"❌ 会话检查失败 {session_id}: {e}")
            return False

    def get_all_sessions(self) -> Dict[str, Dict[str, Any]]:
        """获取所有会话（仅用于调试）"""
        try:
            pattern = f"{self.session_prefix}*"
            keys = self.redis_client.keys(pattern)
            sessions = {}
            for key in keys:
                session_id = key.replace(self.session_prefix, "")
                session_data = self.load_session(session_id)
                if session_data:
                    sessions[session_id] = session_data
            return sessions
        except Exception as e:
            logger.error(f"❌ 获取所有会话失败: {e}")
            return {}