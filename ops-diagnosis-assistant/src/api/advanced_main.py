import os
import uuid
import time
from typing import Dict, Any, Optional
from fastapi import FastAPI, HTTPException, BackgroundTasks, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import uvicorn
from dotenv import load_dotenv

from src.tasks.diagnosis_tasks import process_diagnosis_task, cleanup_old_sessions_task
from src.core.session_manager import RedisSessionManager

load_dotenv()

# 请求和响应模型
class DiagnosisRequest(BaseModel):
    message: str = Field(..., description="用户输入的诊断问题")
    session_id: Optional[str] = Field(None, description="会话ID（可选）")

class DiagnosisResponse(BaseModel):
    task_id: str = Field(..., description="任务ID")
    session_id: str = Field(..., description="会话ID")
    status: str = Field(..., description="任务状态")
    message: str = Field(..., description="状态消息")

class TaskStatusResponse(BaseModel):
    task_id: str = Field(..., description="任务ID")
    status: str = Field(..., description="任务状态")
    result: Optional[Dict[str, Any]] = Field(None, description="任务结果")
    error: Optional[str] = Field(None, description="错误信息")
    progress: Optional[Dict[str, Any]] = Field(None, description="进度信息")

class SessionInfoResponse(BaseModel):
    session_id: str = Field(..., description="会话ID")
    created_at: Optional[str] = Field(None, description="创建时间")
    diagnosis_stage: Optional[str] = Field(None, description="诊断阶段")
    message_count: int = Field(..., description="消息数量")
    history: Optional[list] = Field(None, description="对话历史")

# API密钥验证（简单实现）
async def verify_api_key(x_api_key: str = Header(...)):
    expected_key = os.getenv("API_KEY", "default_secret_key")
    if x_api_key != expected_key:
        raise HTTPException(status_code=401, detail="无效的API密钥")
    return x_api_key

# 初始化FastAPI应用
app = FastAPI(
    title="运维智能诊断助手 API - 高级版",
    description="基于LangGraph和Celery的异步运维故障诊断助手",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应该限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局组件
session_manager = RedisSessionManager()

# API路由
@app.get("/")
async def root():
    """根路径，返回API信息"""
    return {
        "message": "运维智能诊断助手 API v2.0 正在运行",
        "version": "2.0.0",
        "features": [
            "异步诊断任务处理",
            "Redis会话持久化", 
            "任务状态查询",
            "API密钥认证"
        ],
        "endpoints": {
            "health": "/health",
            "diagnose_async": "/diagnose/async (POST)",
            "task_status": "/tasks/{task_id} (GET)",
            "session_info": "/sessions/{session_id} (GET)",
            "sessions": "/sessions (GET)"
        }
    }

@app.get("/health")
async def health_check():
    """健康检查端点"""
    try:
        # 测试Redis连接
        redis_health = session_manager.session_exists("health_check")
        
        # 测试Celery连接（简单版本）
        celery_health = True
        
        return {
            "status": "healthy",
            "service": "ops-diagnosis-assistant-v2",
            "timestamp": time.time(),
            "redis": "connected" if redis_health is not False else "disconnected",
            "celery": "connected" if celery_health else "disconnected"
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"服务不健康: {str(e)}")

@app.post("/diagnose/async", response_model=DiagnosisResponse)
async def diagnose_async(
    request: DiagnosisRequest,
    background_tasks: BackgroundTasks,
    api_key: str = Depends(verify_api_key)
):
    """
    异步诊断接口 - 接收用户问题并返回任务ID
    """
    try:
        # 生成或使用现有会话ID
        session_id = request.session_id or str(uuid.uuid4())
        
        print(f"🎯 收到异步诊断请求: {request.message}, 会话: {session_id}")
        
        # 提交Celery任务
        task = process_diagnosis_task.apply_async(
            args=[request.message, session_id],
            task_id=str(uuid.uuid4())
        )
        
        # 添加后台任务清理（可选）
        background_tasks.add_task(cleanup_old_sessions_task)
        
        return DiagnosisResponse(
            task_id=task.id,
            session_id=session_id,
            status="PENDING",
            message="诊断任务已提交，请使用task_id查询状态"
        )
        
    except Exception as e:
        print(f"❌ 异步诊断请求失败: {e}")
        raise HTTPException(status_code=500, detail=f"诊断任务提交失败: {str(e)}")

@app.get("/tasks/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str, api_key: str = Depends(verify_api_key)):
    """
    查询任务状态
    """
    try:
        from src.celery_app import celery_app
        
        # 获取任务结果
        task_result = celery_app.AsyncResult(task_id)

        print(f"wx task_result {task_result}")
        
        response_data = {
            "task_id": task_id,
            "status": task_result.status,
            "result": task_result.result
        }

        print(f"wx response_data {response_data}")
        
        if task_result.status == 'SUCCESS':
            response_data["result"] = task_result.result
        elif task_result.status == 'FAILURE':
            response_data["error"] = str(task_result.result)
        elif task_result.status == 'PROGRESS':
            response_data["progress"] = task_result.result
        
        return TaskStatusResponse(**response_data)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询任务状态失败: {str(e)}")

@app.get("/sessions/{session_id}", response_model=SessionInfoResponse)
async def get_session_info(session_id: str, api_key: str = Depends(verify_api_key)):
    """
    获取会话信息
    """
    try:
        session_data = session_manager.load_session(session_id)
        
        if not session_data:
            raise HTTPException(status_code=404, detail="会话不存在")
        
        # 计算消息数量
        messages = session_data.get('messages', [])
        message_count = len(messages) // 2  # 用户和助手交替
        
        return SessionInfoResponse(
            session_id=session_id,
            diagnosis_stage=session_data.get('diagnosis_stage'),
            message_count=message_count,
            history=messages[-10:]  # 返回最近10条消息
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取会话信息失败: {str(e)}")

@app.get("/sessions")
async def list_sessions(api_key: str = Depends(verify_api_key)):
    """
    列出所有活跃会话（仅用于调试）
    """
    try:
        sessions = session_manager.get_all_sessions()
        
        session_list = []
        for session_id, session_data in sessions.items():
            messages = session_data.get('messages', [])
            session_list.append({
                "session_id": session_id,
                "diagnosis_stage": session_data.get('diagnosis_stage'),
                "message_count": len(messages) // 2,
                "last_activity": "最近活动时间"  # 可以添加时间戳字段
            })
        
        return {
            "active_sessions": len(session_list),
            "sessions": session_list
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取会话列表失败: {str(e)}")

@app.delete("/sessions/{session_id}")
async def delete_session(session_id: str, api_key: str = Depends(verify_api_key)):
    """
    删除会话
    """
    try:
        success = session_manager.delete_session(session_id)
        
        if success:
            return {"message": f"会话 {session_id} 已删除"}
        else:
            raise HTTPException(status_code=404, detail="会话不存在或删除失败")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除会话失败: {str(e)}")

@app.post("/cleanup/sessions")
async def trigger_cleanup(background_tasks: BackgroundTasks, api_key: str = Depends(verify_api_key)):
    """
    手动触发会话清理
    """
    try:
        background_tasks.add_task(cleanup_old_sessions_task)
        return {"message": "会话清理任务已触发"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"触发清理任务失败: {str(e)}")

# 错误处理
@app.exception_handler(500)
async def internal_server_error_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"detail": "服务器内部错误", "error": str(exc)}
    )

@app.exception_handler(404)
async def not_found_handler(request, exc):
    return JSONResponse(
        status_code=404,
        content={"detail": "资源未找到"}
    )

# 启动应用
if __name__ == "__main__":
    uvicorn.run(
        "advanced_main:app",
        host=os.getenv("API_HOST", "0.0.0.0"),
        port=int(os.getenv("API_PORT", 8000)),
        reload=True,
        log_level="info"
    )