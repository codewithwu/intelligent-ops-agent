import os
import time
from celery import current_task
from src.celery_app import celery_app
from src.core.advanced_agent import AdvancedDiagnosisAgent
from src.core.session_manager import RedisSessionManager
import logging

logger = logging.getLogger(__name__)

# 初始化组件
session_manager = RedisSessionManager()
diagnosis_agent = AdvancedDiagnosisAgent(debug_mode=True)

@celery_app.task(bind=True, name='diagnosis.process_diagnosis')
def process_diagnosis_task(self, user_input: str, session_id: str = None):
    """处理诊断任务的Celery任务"""
    try:
        logger.info(f"🎯 开始处理诊断任务: {session_id}")
        
        # 更新任务状态
        self.update_state(
            state='PROGRESS',
            meta={
                'current': 1,
                'total': 5,
                'status': '正在初始化诊断会话...',
                'session_id': session_id
            }
        )
        
        # 从Redis加载或创建会话
        if session_id and session_manager.session_exists(session_id):
            session_data = session_manager.load_session(session_id)
        else:
            session_data = None

        # 更新任务状态 - 症状收集
        self.update_state(
            state='PROGRESS',
            meta={
                'current': 2,
                'total': 5,
                'status': '正在分析症状信息...',
                'session_id': session_id
            }
        )
        
        # 执行诊断
        response = diagnosis_agent.diagnose(user_input, session_id or "new_session")

        logger.info(f"🎯 wx 诊断的结果response为 : {response}")
        
        # 更新任务状态 - 知识检索
        self.update_state(
            state='PROGRESS',
            meta={
                'current': 3,
                'total': 5,
                'status': '正在检索相关知识库...',
                'session_id': session_id
            }
        )
        
        # 获取当前会话状态并保存
        current_session_id = session_id or list(diagnosis_agent.session_states.keys())[-1]
        session_data = diagnosis_agent.session_states.get(current_session_id, {})
        
        # 更新任务状态 - 根因分析
        self.update_state(
            state='PROGRESS',
            meta={
                'current': 4,
                'total': 5,
                'status': '正在分析根本原因...',
                'session_id': current_session_id
            }
        )
        
        # 保存会话到Redis
        session_manager.save_session(current_session_id, session_data)
        
        # 更新任务状态 - 完成
        self.update_state(
            state='PROGRESS',
            meta={
                'current': 5,
                'total': 5,
                'status': '生成最终解决方案...',
                'session_id': current_session_id
            }
        )
        
        logger.info(f"✅ 诊断任务完成: {current_session_id}")
        
        return {
            'status': 'SUCCESS',
            'result': {
                'response': response,
                'session_id': current_session_id,
                'diagnosis_stage': session_data.get('diagnosis_stage', 'unknown')
            },
            'session_id': current_session_id
        }
        
    except Exception as e:
        logger.error(f"❌ 诊断任务失败: {e}")
        self.update_state(
            state='FAILURE',
            meta={
                'current': 5,
                'total': 5,
                'status': f'任务失败: {str(e)}',
                'session_id': session_id
            }
        )
        raise

@celery_app.task(name='diagnosis.cleanup_old_sessions')
def cleanup_old_sessions_task():
    """清理过期会话的定时任务"""
    try:
        logger.info("🧹 开始清理过期会话...")
        # Redis会自动清理过期的会话，这里可以添加额外的清理逻辑
        session_manager = RedisSessionManager()
        # 可以添加特定的清理逻辑，比如清理特定模式的会话
        logger.info("✅ 会话清理完成")
        return {'status': 'SUCCESS', 'cleaned_count': 0}
    except Exception as e:
        logger.error(f"❌ 会话清理失败: {e}")
        return {'status': 'FAILURE', 'error': str(e)}