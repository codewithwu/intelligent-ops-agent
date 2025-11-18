import os
from typing import Annotated, TypedDict
from dotenv import load_dotenv
from langchain_ollama import ChatOllama
from langgraph.graph import StateGraph, START, END
from langchain_core.messages import HumanMessage, AIMessage

from .knowledge_retriever import KnowledgeRetriever

load_dotenv()

# 定义增强的状态结构
class DiagnosisState(TypedDict):
    messages: Annotated[list, "对话消息历史"]
    user_input: str
    problem_type: str
    needs_solution: bool
    retrieved_knowledge: str
    response: str

class RAGDiagnosisAgent:
    def __init__(self):
        # 初始化模型
        self.llm = ChatOllama(
            model=os.getenv("OLLAMA_MODEL", "llama3.1:8b"),
            base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
            temperature=0.1
        )
        
        # 初始化知识检索器
        self.retriever = KnowledgeRetriever()
        
        # 构建工作流
        self.graph = self._build_graph()
    
    def _build_graph(self):
        """构建RAG增强的工作流图"""
        workflow = StateGraph(DiagnosisState)
        
        # 添加节点
        workflow.add_node("retrieve_knowledge", self._retrieve_knowledge_node)
        workflow.add_node("analyze_problem", self._analyze_problem_node)
        workflow.add_node("provide_solution", self._provide_solution_node)
        
        # 设置入口点
        workflow.add_edge(START, "retrieve_knowledge")
        
        # 添加条件边
        workflow.add_conditional_edges(
            "retrieve_knowledge",
            self._route_after_retrieval,
            {
                "analyze": "analyze_problem",
                "direct_solution": "provide_solution"
            }
        )
        
        workflow.add_conditional_edges(
            "analyze_problem",
            self._route_after_analysis,
            {
                "needs_solution": "provide_solution",
                "end": END
            }
        )
        
        workflow.add_edge("provide_solution", END)
        
        return workflow.compile()
    
    def _retrieve_knowledge_node(self, state: DiagnosisState) -> DiagnosisState:
        """知识检索节点"""
        user_input = state.get("user_input", "")
        
        print(f"🔍 正在从知识库检索相关信息: {user_input}")
        
        # 从Elasticsearch检索相关知识
        retrieved_knowledge = self.retriever.get_related_knowledge(user_input)
        state["retrieved_knowledge"] = retrieved_knowledge
        
        print(f"📚 检索到 {retrieved_knowledge.count('案例')} 个相关案例")
        
        # 如果有高度相关的知识，可以直接提供解决方案
        if "没有找到相关的故障案例" not in retrieved_knowledge:
            state["needs_solution"] = True
        else:
            state["needs_solution"] = False
            
        return state
    
    def _analyze_problem_node(self, state: DiagnosisState) -> DiagnosisState:
        """问题分析节点 - 使用检索到的知识进行分析"""
        user_input = state.get("user_input", "")
        retrieved_knowledge = state.get("retrieved_knowledge", "")
        
        print(f"🤔 正在结合知识库分析问题...")
        
        # 使用LLM结合检索到的知识分析问题
        prompt = f"""
        你是一个专业的运维工程师。请基于以下知识库信息和用户描述，分析问题的根本原因。

        用户描述的问题：
        {user_input}

        知识库中的相关案例：
        {retrieved_knowledge}

        请分析：
        1. 这个问题与知识库中哪个案例最相似？
        2. 可能的根本原因是什么？
        3. 是否需要更多信息来准确诊断？

        请用简洁的专业语言回复你的分析。
        """
        
        try:
            response = self.llm.invoke([HumanMessage(content=prompt)])
            analysis = response.content
            
            # 简单的关键词识别问题类型（可以进一步用LLM增强）
            if any(keyword in user_input.lower() for keyword in ["cpu", "负载", "使用率"]):
                state["problem_type"] = "cpu_high"
            elif any(keyword in user_input.lower() for keyword in ["内存", "oom", "memory"]):
                state["problem_type"] = "memory_issue"
            elif any(keyword in user_input.lower() for keyword in ["磁盘", "空间", "disk"]):
                state["problem_type"] = "disk_issue"
            elif any(keyword in user_input.lower() for keyword in ["网络", "延迟", "network"]):
                state["problem_type"] = "network_issue"
            else:
                state["problem_type"] = "unknown"
            
            print(f"✅ 问题分析完成: {state['problem_type']}")
            
        except Exception as e:
            print(f"❌ 问题分析失败: {e}")
            state["problem_type"] = "unknown"
        
        return state
    
    def _provide_solution_node(self, state: DiagnosisState) -> DiagnosisState:
        """解决方案提供节点 - 基于检索的知识生成解决方案"""
        user_input = state.get("user_input", "")
        retrieved_knowledge = state.get("retrieved_knowledge", "")
        problem_type = state.get("problem_type", "unknown")
        
        print(f"💡 正在基于知识库生成解决方案...")
        
        # 使用LLM结合检索到的知识生成解决方案
        prompt = f"""
        你是一个专业的运维工程师。请基于知识库中的最佳实践和用户的具体问题，提供专业的解决方案。

        用户描述的问题：
        {user_input}

        问题类型分析：{problem_type}

        知识库中的相关案例和解决方案：
        {retrieved_knowledge}

        请提供：
        1. 针对这个具体问题的分步解决方案
        2. 具体的命令和操作步骤
        3. 注意事项和可能的风险
        4. 如果需要更多信息，请明确询问

        要求：
        - 基于知识库中的最佳实践
        - 提供具体可操作的命令
        - 用专业但友好的中文回复
        - 如果知识库中的方案不完全匹配，请结合你的专业知识进行补充
        """
        
        try:
            response = self.llm.invoke([HumanMessage(content=prompt)])
            state["response"] = response.content
            print("✅ 解决方案生成完成")
        except Exception as e:
            print(f"❌ 解决方案生成失败: {e}")
            state["response"] = "抱歉，生成解决方案时出现错误。"
        
        return state
    
    def _route_after_retrieval(self, state: DiagnosisState) -> str:
        """检索后的路由逻辑"""
        if state.get("needs_solution", False):
            # 如果有相关知识，可以直接提供解决方案
            if "案例 1" in state.get("retrieved_knowledge", ""):
                return "direct_solution"
            return "analyze"
        return "analyze"  # 即使没有相关知识也进行分析
    
    def _route_after_analysis(self, state: DiagnosisState) -> str:
        """分析后的路由逻辑"""
        return "needs_solution"  # 总是提供解决方案
    
    def diagnose(self, user_input: str) -> str:
        """执行诊断"""
        print(f"🎯 开始RAG增强诊断: {user_input}")
        
        # 初始化状态
        initial_state = DiagnosisState(
            messages=[HumanMessage(content=user_input)],
            user_input=user_input,
            problem_type="unknown",
            needs_solution=False,
            retrieved_knowledge="",
            response=""
        )
        
        # 执行图
        result = self.graph.invoke(initial_state)
        
        print("✅ RAG诊断完成")
        return result.get("response", "抱歉，无法提供诊断建议。")

# 测试函数
def test_rag_agent():
    """测试RAG增强智能体"""
    print("🤖 测试RAG增强诊断智能体...")
    
    agent = RAGDiagnosisAgent()
    
    # 测试用例
    test_cases = [
        "我的服务器CPU使用率一直保持在95%以上，系统很卡",
        "内存不足，经常出现OutOfMemoryError错误",
        "磁盘空间满了，无法创建新文件",
        "网络延迟很高，ping响应时间超过200ms",
        "数据库连接池满了，无法获取新连接"
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{'='*60}")
        print(f"测试用例 {i}: {test_case}")
        print(f"{'='*60}")
        try:
            response = agent.diagnose(test_case)
            print(f"💬 助手回复:\n{response}")
        except Exception as e:
            print(f"❌ 测试失败: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    test_rag_agent()