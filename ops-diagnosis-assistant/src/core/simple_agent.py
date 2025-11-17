import os
from typing import Annotated, TypedDict
from dotenv import load_dotenv
from langchain_ollama import ChatOllama
from langgraph.graph import StateGraph, START, END
from langchain_core.messages import HumanMessage, AIMessage

# 加载环境变量
load_dotenv()

# 定义状态结构 - 使用新版TypedDict
class DiagnosisState(TypedDict):
    messages: Annotated[list, "对话消息历史"]
    problem_type: str
    needs_solution: bool
    response: str

class SimpleDiagnosisAgent:
    def __init__(self):
        # 初始化模型
        self.llm = ChatOllama(
            model=os.getenv("OLLAMA_MODEL", "llama3.1:8b"),
            base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
            temperature=0.1  # 降低随机性，更适合诊断场景
        )
        
        # 构建工作流
        self.graph = self._build_graph()
    
    def _build_graph(self):
        """构建工作流图 - 新版API"""
        workflow = StateGraph(DiagnosisState)
        
        # 添加节点
        workflow.add_node("identify_problem", self._identify_problem_node)
        workflow.add_node("provide_solution", self._provide_solution_node)
        
        # 设置入口点
        workflow.add_edge(START, "identify_problem")
        
        # 添加条件边
        workflow.add_conditional_edges(
            "identify_problem",
            self._route_after_identification,
            {
                "needs_solution": "provide_solution",
                "end": END
            }
        )
        
        workflow.add_edge("provide_solution", END)
        
        return workflow.compile()
    
    def _identify_problem_node(self, state: DiagnosisState) -> DiagnosisState:
        """问题识别节点"""
        # 获取最新用户消息
        user_message = state["messages"][-1] if state["messages"] else None
        user_input = user_message.content if user_message else ""
        
        print(f"🔍 正在识别问题: {user_input}")
        
        # 扩展关键词识别
        cpu_keywords = ["cpu", "CPU", "cpu高", "cpu使用率", "负载高", "卡顿", "响应慢"]
        memory_keywords = ["内存", "memory", "内存不足", "out of memory", "oom", "内存泄漏"]
        network_keywords = ["网络", "network", "访问慢", "延迟", "ping", "丢包", "连接失败"]
        disk_keywords = ["磁盘", "disk", "空间满", "存储", "硬盘", "no space"]
        website_keywords = ["网站", "web", "打不开", "无法访问", "404", "502"]
        
        user_input_lower = user_input.lower()
        
        if any(keyword in user_input_lower for keyword in cpu_keywords):
            state["problem_type"] = "cpu_high"
            state["needs_solution"] = True
        elif any(keyword in user_input_lower for keyword in memory_keywords):
            state["problem_type"] = "memory_issue"
            state["needs_solution"] = True
        elif any(keyword in user_input_lower for keyword in network_keywords):
            state["problem_type"] = "network_issue"
            state["needs_solution"] = True
        elif any(keyword in user_input_lower for keyword in disk_keywords):
            state["problem_type"] = "disk_issue"
            state["needs_solution"] = True
        elif any(keyword in user_input_lower for keyword in website_keywords):
            state["problem_type"] = "website_down"
            state["needs_solution"] = True
        else:
            state["problem_type"] = "unknown"
            state["needs_solution"] = True  # 即使是未知问题也提供基础帮助
        
        return state
    
    def _provide_solution_node(self, state: DiagnosisState) -> DiagnosisState:
        """解决方案提供节点"""
        problem_type = state.get("problem_type", "unknown")
        
        print(f"💡 正在为 {problem_type} 问题提供解决方案")
        
        # 扩展解决方案模板
        solution_templates = {
            "cpu_high": """[原有CPU排查步骤]""",
            "memory_issue": """[原有内存排查步骤]""", 
            "network_issue": """[原有网络排查步骤]""",
            "disk_issue": """
            磁盘空间不足排查步骤：
            1. 使用 `df -h` 查看磁盘使用情况
            2. 使用 `du -sh /* | sort -rh | head -10` 查找占用空间最大的目录
            3. 检查日志文件：`find /var/log -type f -size +100M`
            4. 清理缓存：`apt clean` 或 `yum clean all`
            5. 查找大文件：`find / -type f -size +100M 2>/dev/null`
            """,
            "website_down": """
            网站无法访问排查步骤：
            1. 检查Web服务状态：`systemctl status nginx` 或 `systemctl status apache2`
            2. 检查端口监听：`netstat -tulpn | grep :80` 或 `ss -tulpn | grep :80`
            3. 检查防火墙设置：`iptables -L` 或 `firewall-cmd --list-all`
            4. 查看Web服务日志：`tail -f /var/log/nginx/error.log`
            5. 检查DNS解析：`nslookup 你的域名`
            """,
            "unknown": """
            通用故障排查步骤：
            1. 查看系统日志：`journalctl -xe` 或 `tail -f /var/log/syslog`
            2. 检查服务状态：`systemctl list-units --type=service --state=failed`
            3. 查看最近系统变化：检查/var/log/apt/history.log或yum日志
            4. 监控系统资源：使用 `htop` 或 `glances` 全面查看系统状态
            
            请提供以下信息以便进一步诊断：
            - 具体的错误信息
            - 故障发生的时间点
            - 影响的范围（全部用户/部分用户）
            - 最近的系统变更
            """
        }
        
        template = solution_templates.get(problem_type, solution_templates["unknown"])
        
        # 使用LLM生成专业回复
        user_desc = state['messages'][-1].content if state['messages'] else '无描述'
        
        prompt = f"""
        你是一个专业的运维工程师。用户报告了以下问题：
        
        用户描述：{user_desc}
        识别的问题类型：{problem_type}
        
        请基于以下排查步骤，生成一个专业、友好的中文回复：
        {template}
        
        要求：
        - 用清晰的中文解释问题可能的原因
        - 提供具体的命令和排查步骤
        - 语气专业但友好
        - 如果信息不足，请询问更多细节
        - 针对"{user_desc}"这个具体问题给出建议
        """
        
        try:
            response = self.llm.invoke([HumanMessage(content=prompt)])
            state["response"] = response.content
        except Exception as e:
            print(f"❌ LLM调用失败: {e}")
            state["response"] = f"基于{problem_type}问题的建议：{template}"
        
        return state
    
    def _route_after_identification(self, state: DiagnosisState) -> str:
        """识别后的路由逻辑"""
        return "needs_solution" if state.get("needs_solution", False) else "end"
    
    def diagnose(self, user_input: str) -> str:
        """执行诊断"""
        print(f"🎯 开始诊断用户输入: {user_input}")
        
        # 初始化状态 - 新版状态管理
        initial_state = DiagnosisState(
            messages=[HumanMessage(content=user_input)],
            problem_type="unknown",
            needs_solution=False,
            response=""
        )
        
        # 执行图
        result = self.graph.invoke(initial_state)
        
        print("✅ 诊断完成")
        return result.get("response", "抱歉，无法提供诊断建议。")