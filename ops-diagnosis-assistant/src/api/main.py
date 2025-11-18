import os
import uuid
from typing import Dict, Any
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# 导入我们之前创建的智能体
import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from core.simple_agent import SimpleDiagnosisAgent
from core.rag_agent import RAGDiagnosisAgent

# 定义请求和响应模型
class DiagnosisRequest(BaseModel):
    message: str
    session_id: str = None

class DiagnosisResponse(BaseModel):
    response: str
    session_id: str
    status: str = "success"

# 初始化FastAPI应用
app = FastAPI(
    title="运维智能诊断助手 API",
    description="基于LangGraph和LLM的运维故障诊断助手",
    version="1.0.0"
)

# 添加CORS中间件（方便前端调用）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应该限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局变量（后续会用Redis替换）
class SessionManager:
    def __init__(self):
        self.sessions: Dict[str, Any] = {}
        # self.agent = SimpleDiagnosisAgent()
        self.agent = RAGDiagnosisAgent()  # 使用RAG增强智能体
    
    def get_or_create_session(self, session_id: str = None):
        if session_id is None:
            session_id = str(uuid.uuid4())
        
        if session_id not in self.sessions:
            self.sessions[session_id] = {
                "history": [],
                "created_at": os.times().elapsed
            }
        
        return session_id, self.sessions[session_id]
    
    def add_to_history(self, session_id: str, user_message: str, assistant_response: str):
        if session_id in self.sessions:
            self.sessions[session_id]["history"].extend([
                {"role": "user", "content": user_message},
                {"role": "assistant", "content": assistant_response}
            ])

session_manager = SessionManager()

# API路由
@app.get("/")
async def root():
    """根路径，返回API信息"""
    return {
        "message": "运维智能诊断助手 API 正在运行",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "diagnose": "/diagnose (POST)",
            "session_history": "/session/{session_id} (GET)"
        }
    }

@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {
        "status": "healthy",
        "service": "ops-diagnosis-assistant",
        "timestamp": os.times().elapsed
    }

@app.post("/diagnose", response_model=DiagnosisResponse)
async def diagnose(request: DiagnosisRequest):
    """
    诊断接口 - 接收用户问题并返回诊断建议
    """
    try:
        print(f"🎯 收到诊断请求: {request.message}")
        
        # 获取或创建会话
        session_id, session_data = session_manager.get_or_create_session(request.session_id)
        
        # 调用智能体进行诊断
        diagnosis_response = session_manager.agent.diagnose(request.message)
        
        # 保存到历史记录
        session_manager.add_to_history(session_id, request.message, diagnosis_response)
        
        print(f"✅ 诊断完成，会话ID: {session_id}")
        
        return DiagnosisResponse(
            response=diagnosis_response,
            session_id=session_id,
            status="success"
        )
        
    except Exception as e:
        print(f"❌ 诊断过程出错: {e}")
        raise HTTPException(status_code=500, detail=f"诊断失败: {str(e)}")

@app.get("/session/{session_id}")
async def get_session_history(session_id: str):
    """获取会话历史记录"""
    if session_id not in session_manager.sessions:
        raise HTTPException(status_code=404, detail="会话不存在")
    
    return {
        "session_id": session_id,
        "history": session_manager.sessions[session_id]["history"],
        "message_count": len(session_manager.sessions[session_id]["history"]) // 2
    }

@app.get("/sessions")
async def list_sessions():
    """列出所有活跃会话（仅用于调试）"""
    return {
        "active_sessions": len(session_manager.sessions),
        "sessions": list(session_manager.sessions.keys())
    }

# 启动应用
if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # 开发时自动重载
        log_level="info"
    )