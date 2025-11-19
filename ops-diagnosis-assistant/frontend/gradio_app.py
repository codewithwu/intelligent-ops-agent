import gradio as gr
import requests
import json
import time
import uuid
from typing import List, Tuple, Dict, Any
import os
from dotenv import load_dotenv

load_dotenv()

class DiagnosisChatInterface:
    def __init__(self):
        self.api_base_url = os.getenv("API_BASE_URL", "http://localhost:8000")
        self.api_key = os.getenv("API_KEY", "default_secret_key")
        self.session_id = None
        self.current_task_id = None
        
        self.headers = {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json"
        }
    
    def _check_api_health(self) -> bool:
        """检查API健康状态"""
        try:
            response = requests.get(f"{self.api_base_url}/health", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def _wait_for_task_completion(self, task_id: str, max_wait: int = 30) -> Dict[str, Any]:
        """等待任务完成"""
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            try:
                response = requests.get(
                    f"{self.api_base_url}/tasks/{task_id}",
                    headers=self.headers,
                    timeout=5
                )
                
                if response.status_code == 200:
                    status_data = response.json()

                    
                    if status_data["status"] == "SUCCESS":
                        return {"status": "success", "data": status_data.get("result").get("result")}
                    elif status_data["status"] == "FAILURE":
                        return {"status": "error", "message": status_data.get("error", "任务执行失败")}
                    # elif status_data["status"] == "PROGRESS":
                    #     progress = status_data.get("progress", {})
                    #     yield {"status": "progress", "message": progress.get("status", "处理中...")}
                    # else:
                    #     yield {"status": "progress", "message": "任务排队中..."}
                
                time.sleep(1)
                
            except Exception as e:
                return {"status": "error", "message": f"查询任务状态失败: {str(e)}"}
                
        
        return {"status": "error", "message": "任务执行超时"}
    
    def send_message(self, message: str, chat_history: List[Tuple[str, str]]) -> Tuple[str, List[Tuple[str, str]]]:
        """发送消息并获取回复"""
        if not message.strip():
            return "", chat_history
        
        # 添加到聊天历史
        chat_history.append((message, ""))
        
        try:
            # 提交诊断任务
            data = {
                "message": message
            }
            if self.session_id:
                data["session_id"] = self.session_id
            
            response = requests.post(
                f"{self.api_base_url}/diagnose/async",
                json=data,
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code != 200:
                error_msg = f"❌ 请求失败: {response.text}"
                chat_history[-1] = (message, error_msg)
                return "", chat_history
            
            task_info = response.json()
            self.current_task_id = task_info["task_id"]
            self.session_id = task_info["session_id"]
            
            # 等待任务完成并流式更新
            # for update in self._wait_for_task_completion(self.current_task_id):
            #     if update["status"] == "progress":
            #         chat_history[-1] = (message, f"⏳ {update['message']}...")
            #         yield "", chat_history
            #     elif update["status"] == "error":
            #         chat_history[-1] = (message, f"❌ {update['message']}")
            #         yield "", chat_history
            #         return
            
            final_result = self._wait_for_task_completion(self.current_task_id)
            print(f"wx final_result {final_result}")
            if final_result["status"] == "success":
                result_data = final_result["data"]
                assistant_response = result_data.get("response", "抱歉，没有获取到回复。")
                
                # 格式化回复
                formatted_response = self._format_response(assistant_response)
                chat_history[-1] = (message, formatted_response)
            else:
                chat_history[-1] = (message, f"❌ {final_result['message']}")
            
        except requests.exceptions.Timeout:
            chat_history[-1] = (message, "❌ 请求超时，请检查API服务是否正常")
        except requests.exceptions.ConnectionError:
            chat_history[-1] = (message, "❌ 无法连接到API服务，请检查服务状态")
        except Exception as e:
            chat_history[-1] = (message, f"❌ 发生错误: {str(e)}")
        
        yield "", chat_history
    
    def _format_response(self, response: str) -> str:
        """格式化助手回复"""
        # 简单的Markdown样式格式化
        formatted = response
        
        # 代码块格式化
        if "```" in response:
            formatted = formatted.replace("```", "\n```")
        
        # 步骤格式化
        lines = formatted.split('\n')
        formatted_lines = []
        for line in lines:
            if line.strip().startswith(('1.', '2.', '3.', '4.', '5.', '6.', '7.', '8.', '9.')):
                formatted_lines.append(f"**{line}**")
            elif line.strip().startswith('- '):
                formatted_lines.append(f"• {line[2:]}")
            else:
                formatted_lines.append(line)
        
        return '\n'.join(formatted_lines)
    
    def clear_chat(self) -> Tuple[str, str, List]:
        """清空聊天"""
        self.session_id = None
        self.current_task_id = None
        return "", "", []
    
    def get_session_info(self) -> str:
        """获取会话信息"""
        if not self.session_id:
            return "当前没有活跃会话"
        
        try:
            response = requests.get(
                f"{self.api_base_url}/sessions/{self.session_id}",
                headers=self.headers,
                timeout=5
            )
            
            if response.status_code == 200:
                session_info = response.json()
                return f"""
**会话信息**
- 会话ID: {session_info['session_id']}
- 诊断阶段: {session_info.get('diagnosis_stage', '未知')}
- 消息数量: {session_info.get('message_count', 0)}
                """
            else:
                return f"获取会话信息失败: {response.text}"
                
        except Exception as e:
            return f"获取会话信息时出错: {str(e)}"

def create_gradio_interface():
    """创建Gradio界面"""
    chat_interface = DiagnosisChatInterface()
    
    with gr.Blocks(
        title="运维智能诊断助手",
        theme=gr.themes.Soft(),
        css="""
        .diagnosis-header {
            text-align: center;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border-radius: 10px;
            margin-bottom: 20px;
        }
        .diagnosis-title {
            font-size: 2.5em;
            font-weight: bold;
            margin: 0;
        }
        .diagnosis-subtitle {
            font-size: 1.2em;
            opacity: 0.9;
            margin: 10px 0 0 0;
        }
        .chat-container {
            border: 2px solid #e0e0e0;
            border-radius: 10px;
            padding: 20px;
            background: white;
        }
        """
    ) as interface:
        
        # 头部
        gr.HTML("""
        <div class="diagnosis-header">
            <h1 class="diagnosis-title">🔧 运维智能诊断助手</h1>
            <p class="diagnosis-subtitle">基于AI的智能运维故障诊断系统</p>
        </div>
        """)
        
        with gr.Row():
            with gr.Column(scale=3):
                # 聊天界面
                with gr.Group():
                    chatbot = gr.Chatbot(
                        label="诊断对话",
                        height=500,
                        show_copy_button=True,
                        avatar_images=(
                            "https://api.dicebear.com/7.x/bottts/svg?seed=user", 
                            "https://api.dicebear.com/7.x/bottts/svg?seed=assistant"
                        )
                    )
                    
                    with gr.Row():
                        msg = gr.Textbox(
                            label="输入您遇到的运维问题",
                            placeholder="例如：我的服务器CPU使用率很高，系统响应很慢...",
                            scale=4,
                            lines=2
                        )
                        submit_btn = gr.Button("发送", variant="primary", scale=1)
                
                with gr.Row():
                    clear_btn = gr.Button("🧹 清空对话", variant="secondary")
                    session_info_btn = gr.Button("📊 会话信息", variant="secondary")
            
            with gr.Column(scale=1):
                # 侧边栏信息
                gr.Markdown("### 💡 使用说明")
                gr.Markdown("""
                欢迎使用运维智能诊断助手！我可以帮助您：
                
                - 🔍 **诊断服务器故障**
                - 📊 **分析性能问题**  
                - 🛠️ **提供解决方案**
                - 📚 **基于知识库建议**
                
                **示例问题：**
                - CPU使用率很高怎么办？
                - 内存不足出现OOM错误
                - 磁盘空间满了无法写入
                - 网络访问很慢延迟高
                """)
                
                # API状态指示器
                status_indicator = gr.HTML("""
                <div style="text-align: center; padding: 10px; border-radius: 5px; background: #f0f0f0;">
                    <h4>🔌 系统状态</h4>
                    <p>API服务: <span id="api-status">检查中...</span></p>
                </div>
                """)
                
                session_info = gr.Textbox(
                    label="会话信息",
                    interactive=False,
                    lines=6,
                    max_lines=6
                )
        
        # 事件处理
        submit_event = msg.submit(
            chat_interface.send_message,
            [msg, chatbot],
            [msg, chatbot]
        )
        
        submit_btn.click(
            chat_interface.send_message,
            [msg, chatbot],
            [msg, chatbot]
        )
        
        clear_btn.click(
            chat_interface.clear_chat,
            outputs=[msg, session_info, chatbot]
        )
        
        session_info_btn.click(
            chat_interface.get_session_info,
            outputs=session_info
        )
        
        # 自动检查API状态
        def update_status():
            if chat_interface._check_api_health():
                return """
                <div style="text-align: center; padding: 10px; border-radius: 5px; background: #e8f5e8;">
                    <h4>🔌 系统状态</h4>
                    <p>API服务: <span style="color: green;">✅ 正常</span></p>
                </div>
                """
            else:
                return """
                <div style="text-align: center; padding: 10px; border-radius: 5px; background: #ffe8e8;">
                    <h4>🔌 系统状态</h4>
                    <p>API服务: <span style="color: red;">❌ 异常</span></p>
                </div>
                """
        
        interface.load(update_status, outputs=status_indicator)
    
    return interface

if __name__ == "__main__":
    # 创建并启动Gradio应用
    app = create_gradio_interface()
    app.queue()  # 允许并发处理
    app.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        show_error=True,
        debug=True
    )