import os
import json
from typing import Annotated, TypedDict, List, Optional
from dotenv import load_dotenv
from langchain_ollama import ChatOllama
from langgraph.graph import StateGraph, START, END
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field
from langchain_core.prompts import PromptTemplate


class SymptomAnalysis(BaseModel):
    symptoms: List[str] = Field(description="主要症状（如CPU高、内存不足、磁盘满等）")
    error_messages: List[str] = Field(description="错误信息或日志内容")
    time_pattern: str = Field(description="问题发生的时间和频率")
    impact_scope: str = Field(description="影响的范围")
    problem_type: str = Field(description="推测的问题类型")

class AnalyzeRootCauseNode(BaseModel):
    affected_components: List[str] = Field(description="受影响组件")
    verification_steps: List[str] = Field(description="验证步骤")
    root_cause: str = Field(description="根本原因分析")


import sys
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from core.knowledge_retriever import KnowledgeRetriever

load_dotenv()

class AdvancedDiagnosisState(TypedDict):
    # 对话相关
    messages: Annotated[List, "完整的对话历史"]
    current_user_input: str
    session_id: str
    
    # 诊断状态
    diagnosis_stage: str  # greeting, symptom_collection, analysis, solution, confirmation
    confirmed_symptoms: Annotated[List, "已确认的症状列表"]
    collected_info: Annotated[dict, "收集到的额外信息"]
    missing_info: Annotated[List, "还需要收集的信息"]
    
    # 分析结果
    problem_type: str
    root_cause_analysis: str
    retrieved_knowledge: str
    solution_steps: Annotated[List, "解决方案步骤"]
    
    # 对话控制
    needs_more_info: bool
    problem_solved: bool
    final_response: str
    generate_solution: str = "生成的解决方案"



class AdvancedDiagnosisAgent:
    def __init__(self, debug_mode=True):
        self.debug_mode = debug_mode
        self.output_parser_collect_symptoms_node = PydanticOutputParser(pydantic_object=SymptomAnalysis)
        self.output_parser_analyze_root_cause_node = PydanticOutputParser(pydantic_object=AnalyzeRootCauseNode)
        
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
        
        # 定义需要收集的关键信息模板
        self.info_templates = {
            "cpu_high": ["发生时间", "影响范围", "具体错误信息", "最近系统变更"],
            "memory_issue": ["OOM发生时间", "内存使用趋势", "Java堆配置", "应用日志"],
            "disk_issue": ["磁盘使用率", "增长最快的目录", "日志文件大小", "清理历史"],
            "network_issue": ["延迟具体数值", "影响的服务", "网络拓扑", "ISP信息"],
            "general": ["错误信息", "发生时间", "影响范围", "最近变更"]
        }

    def _debug_print(self, node_name: str, message: str, data=None):
        """统一的调试信息输出"""
        if not self.debug_mode:
            return
            
        print(f"\n{'🔍' * 20}")
        print(f"🔍 [{node_name}] {message}")
        
        if data is not None:
            if isinstance(data, (dict, list)):
                # 字典和列表使用JSON美化输出
                print(f"🔍 数据详情: {json.dumps(data, indent=2, ensure_ascii=False, default=str)}")
            else:
                # 其他类型直接打印
                print(f"🔍 数据详情: {data}")
        
        print(f"{'🔍' * 20}\n")

    
    def _build_graph(self):
        """构建复杂的工作流图"""
        workflow = StateGraph(AdvancedDiagnosisState)
        
        # 添加所有节点
        workflow.add_node("welcome", self._welcome_node)
        workflow.add_node("collect_symptoms", self._collect_symptoms_node)
        workflow.add_node("ask_clarifying_questions", self._ask_clarifying_questions_node)
        workflow.add_node("retrieve_knowledge", self._retrieve_knowledge_node)
        workflow.add_node("analyze_root_cause", self._analyze_root_cause_node)
        workflow.add_node("generate_solution", self._generate_solution_node)
        workflow.add_node("confirm_resolution", self._confirm_resolution_node)
        
        # 设置入口点
        workflow.add_edge(START, "welcome")
        
        # 主要流程边
        workflow.add_edge("welcome", "collect_symptoms")
        workflow.add_conditional_edges(
            "collect_symptoms",
            self._route_after_symptom_collection,
            {
                "needs_info": "ask_clarifying_questions",
                "has_enough_info": "retrieve_knowledge"
            }
        )
        
        workflow.add_edge("ask_clarifying_questions", "collect_symptoms")
        workflow.add_edge("retrieve_knowledge", "analyze_root_cause")
        workflow.add_edge("analyze_root_cause", "generate_solution")
        workflow.add_edge("generate_solution", "confirm_resolution")
        
        # 结束条件
        workflow.add_conditional_edges(
            "confirm_resolution",
            self._route_after_confirmation,
            {
                "solved": END,
                "needs_more_help": "collect_symptoms",
                "new_problem": "welcome"
            }
        )
        
        return workflow.compile()
    
    def _welcome_node(self, state: AdvancedDiagnosisState) -> AdvancedDiagnosisState:
        """欢迎节点 - 初始化对话"""
        self._debug_print(node_name="1_welcome_node", message="进入", data=state)

        if not state.get("messages"):
            # 首次对话
            welcome_message = """您好！我是运维智能诊断助手。我可以帮助您诊断服务器故障问题。
                                请详细描述您遇到的问题，例如：
                                - 具体的错误信息
                                - 问题发生的时间
                                - 影响的系统范围
                                - 您已经尝试过的解决方法

                                请告诉我您遇到了什么运维问题？"""
            
            state["messages"] = [AIMessage(content=welcome_message)]
            state["diagnosis_stage"] = "greeting" 
            state["final_response"] = welcome_message
            
        self._debug_print(node_name="1 welcome_node", message="出来", data=state)
        return state
    
    def _collect_symptoms_node(self, state: AdvancedDiagnosisState) -> AdvancedDiagnosisState:
        """症状收集节点 - 分析用户输入的症状"""
        self._debug_print(node_name="2_collect_symptoms_node", message="进入", data=state)

        user_input = state.get("current_user_input", "")
        
        # 创建提示词模板
        prompt = PromptTemplate(
            template="""
            请分析以下用户描述的运维问题，提取关键症状和信息：
            
            {format_instructions}
            
            用户描述: {user_input}

            请提取：
            1. 主要症状（如CPU高、内存不足、磁盘满等）
            2. 错误信息或日志内容
            3. 问题发生的时间和频率
            4. 影响的范围
            5. 推测的问题类型

            错误信息示例:
            - 用户说"CPU很高" → error_messages: ["CPU使用率超过90%", "系统负载异常"]
            - 用户说"内存不足" → error_messages: ["内存使用率98%", "OOM错误风险"]
            - 用户说"磁盘满了" → error_messages: ["磁盘使用率95%", "空间不足警告"]
            """,
            input_variables=["user_input"],
            partial_variables={"format_instructions": self.output_parser_collect_symptoms_node.get_format_instructions()}
        )
        
        try:

            # 创建链
            chain = prompt | self.llm | self.output_parser_collect_symptoms_node

            analysis = chain.invoke({"user_input": user_input})
            
            # 更新状态
            new_symptoms = analysis.symptoms
            state["confirmed_symptoms"].extend(new_symptoms)
            state["collected_info"].update({
                "error_messages": analysis.error_messages,
                "time_pattern": analysis.time_pattern,
                "impact_scope": analysis.impact_scope,
            })
            state["problem_type"] = analysis.problem_type
            
            
        except json.JSONDecodeError as e:
            state["problem_type"] = "unknown"
        except Exception as e:
            state["problem_type"] = "unknown"
        
        state["diagnosis_stage"] = "symptom_collection"

        self._debug_print(node_name="2_collect_symptoms_node", message="出来", data=state)

        return state
    
    def _ask_clarifying_questions_node(self, state: AdvancedDiagnosisState) -> AdvancedDiagnosisState:
        """主动询问节点 - 询问缺失的关键信息"""
        self._debug_print(node_name="2_1_ask_clarifying_questions_node", message="进入", data=state)

        problem_type = state.get("problem_type", "general")
        collected_info = state.get("collected_info", {})
        
        # 根据问题类型确定需要的信息
        required_info = self.info_templates.get(problem_type, self.info_templates["general"])
        missing_info = []
        
        for info in required_info:
            if info not in collected_info or not collected_info[info]:
                missing_info.append(info)

        if missing_info:
            # 生成询问问题
            question_prompt = f"""
            基于以下诊断情况，请生成一个专业但友好的问题来询问用户：

            问题类型: {problem_type}
            已收集信息: {collected_info}
            还需要的信息: {missing_info[0]}  # 先问最重要的缺失信息

            请生成一个具体的问题来询问关于"{missing_info[0]}"的信息。
            """
            
            try:
                response = self.llm.invoke([HumanMessage(content=question_prompt)])
                question = response.content
                
                state["messages"].append(AIMessage(content=question))
                state["final_response"] = question
                state["missing_info"] = missing_info
                
            except Exception as e:
                state["final_response"] = "请提供更多关于这个问题的详细信息。"
        else:
            state["needs_more_info"] = False
            state["final_response"] = "我已经收集了足够的信息，现在开始分析根本原因..."

        state["diagnosis_stage"] = "information_collection"

        self._debug_print(node_name="2_1_ask_clarifying_questions_node", message="出来", data=state)
        return state
    
    def _retrieve_knowledge_node(self, state: AdvancedDiagnosisState) -> AdvancedDiagnosisState:
        """知识检索节点 - 基于症状检索相关知识"""
        self._debug_print(node_name="2_2_ask_clarifying_questions_node", message="进入", data=state)

        symptoms_text = " ".join(state.get("confirmed_symptoms", []))
        user_input = state.get("current_user_input", "")
        
        # 组合搜索查询
        search_query = f"{symptoms_text} {user_input}"
        
        retrieved_knowledge = self.retriever.get_related_knowledge(search_query)
        
        state["retrieved_knowledge"] = retrieved_knowledge
        state["diagnosis_stage"] = "knowledge_retrieval"

        self._debug_print(node_name="2_2_ask_clarifying_questions_node", message="出来", data=state)
        return state
    
    def _analyze_root_cause_node(self, state: AdvancedDiagnosisState) -> AdvancedDiagnosisState:
        """根本原因分析节点"""
        self._debug_print(node_name="3_analyze_root_cause_node", message="进入", data=state)

        symptoms = state.get("confirmed_symptoms", [])
        collected_info = state.get("collected_info", {})
        knowledge = state.get("retrieved_knowledge", "")

        prompt = PromptTemplate(
            template="""
            作为资深运维工程师，请分析以下故障的根本原因：
            
            {format_instructions}
            
            症状总结: {symptoms}
            收集到的信息: {collected_info}
            相关知识库案例: {knowledge}

            请提供：
            1. 最可能的根本原因
            2. 验证根本原因的方法
            3. 相关的系统组件或应用

            """,
            input_variables=["symptoms", "collected_info", "knowledge"],
            partial_variables={"format_instructions": self.output_parser_analyze_root_cause_node.get_format_instructions()}
        )

        try:
            # 创建链
            chain = prompt | self.llm | self.output_parser_collect_symptoms_node

            analysis = chain.invoke({"symptoms": symptoms, "collected_info": collected_info, "knowledge": knowledge})
            
            state["root_cause_analysis"] = analysis.root_cause
            state["diagnosis_stage"] = "root_cause_analysis"
            
        except json.JSONDecodeError as e:
            state["root_cause_analysis"] = "无法确定具体根本原因"
        except Exception as e:
            state["root_cause_analysis"] = "无法确定具体根本原因"
        
        self._debug_print(node_name="3_analyze_root_cause_node", message="出来", data=state)
        return state
    
    def _generate_solution_node(self, state: AdvancedDiagnosisState) -> AdvancedDiagnosisState:
        """解决方案生成节点"""
        self._debug_print(node_name="4_generate_solution_node", message="进入", data=state)

        root_cause = state.get("root_cause_analysis", "")
        knowledge = state.get("retrieved_knowledge", "")
        problem_type = state.get("problem_type", "")
        
        solution_prompt = f"""
        基于以下分析，生成具体的解决方案：

        问题类型: {problem_type}
        根本原因: {root_cause}
        相关案例: {knowledge}

        请提供：
        1. 具体的解决步骤
        2. 需要执行的命令
        3. 风险提示和回滚方案
        4. 预防措施

        用清晰的中文回复，包含具体的命令和操作步骤。
        """
        
        try:
            
            response = self.llm.invoke([HumanMessage(content=solution_prompt)])
            solution = response.content
            
            state["solution_steps"] = solution.split('\n')  # 简单分割步骤
            state["final_response"] = solution
            state["diagnosis_stage"] = "solution_generation"
            state["generate_solution"] = solution
            
            
        except Exception as e:
            state["final_response"] = "无法生成具体的解决方案。"
        
        self._debug_print(node_name="4_generate_solution_node", message="出来", data=state)

        return state
    
    def _confirm_resolution_node(self, state: AdvancedDiagnosisState) -> AdvancedDiagnosisState:
        """确认解决节点"""
        self._debug_print(node_name="5_confirm_resolution_node", message="进入", data=state)

        confirmation_prompt = """
        请询问用户问题是否已经解决，或者是否需要进一步的帮助。

        请用友好的语气询问。
        """
        
        try:
            
            response = self.llm.invoke([HumanMessage(content=confirmation_prompt)])
            confirmation_question = response.content
            
            state["messages"].append(AIMessage(content=confirmation_question))
            state["final_response"] = confirmation_question
            state["diagnosis_stage"] = "confirmation"
            state["current_user_input"] = "解决"
            
            
        except Exception as e:
            state["final_response"] = "问题是否已经解决？如果需要进一步帮助，请告诉我。"

        self._debug_print(node_name="5_confirm_resolution_node", message="出来", data=state)

        return state
    
    def _route_after_symptom_collection(self, state: AdvancedDiagnosisState) -> str:
        """症状收集后的路由逻辑"""
        self._debug_print(node_name="r1_route_after_symptom_collection", message="进入", data=state)

        symptoms = state.get("confirmed_symptoms", [])
        collected_info = state.get("collected_info", {})
        
        
        # 简单的启发式规则：如果有明确症状且信息足够，直接分析
        if len(symptoms) >= 1 and collected_info.get("error_messages"):
            decision = "has_enough_info"
        else:
            decision = "needs_info"
        
        self._debug_print(node_name="r1_route_after_symptom_collection", message="出来", data=state)
        print(f"decision {decision}")
        return decision
    
    def _route_after_confirmation(self, state: AdvancedDiagnosisState) -> str:
        """确认后的路由逻辑"""
        self._debug_print(node_name="r2_route_after_confirmation", message="进入", data=state)

        user_input = state.get("current_user_input", "").lower()
        
        if any(word in user_input for word in ["解决", "好了", "可以了", "谢谢"]):
            decision = "solved"
        elif any(word in user_input for word in ["没有", "还不行", "另外", "还有"]):
            decision = "needs_more_help"
        else:
            decision = "new_problem"
        
        self._debug_print(node_name="r2_route_after_confirmation", message="出来", data=state)
        print(f"decision {decision}")
        return decision
    
    def diagnose(self, user_input: str, session_id: str = "default") -> str:
        """执行诊断"""
        print(f"\n{'🚀' * 20}")
        print(f"🚀 开始高级诊断会话: {session_id}")
        print(f"🚀 用户输入: {user_input}")
        print(f"{'🚀' * 20}")
        
        # 初始化或更新状态
        if not hasattr(self, 'session_states'):
            self.session_states = {}
        
        initial_state = None
        if session_id not in self.session_states:
            # 新会话
            initial_state = AdvancedDiagnosisState(
                messages=[],
                current_user_input=user_input,
                session_id=session_id,
                diagnosis_stage="initial",
                confirmed_symptoms=[],
                collected_info={},
                missing_info=[],
                problem_type="unknown",
                root_cause_analysis="",
                retrieved_knowledge="",
                solution_steps=[],
                needs_more_info=True,
                problem_solved=False,
                final_response=""
            )
        else:
            # 继续现有会话
            initial_state = self.session_states[session_id]
            initial_state["current_user_input"] = user_input
        
        # 执行图
        result = self.graph.invoke(initial_state)
        
        # 保存会话状态
        self.session_states[session_id] = result
        
        return result.get("generate_solution", "抱歉，诊断过程中出现了错误。")

# 测试函数
def test_advanced_agent_debug():
    """测试带调试信息的高级智能体"""
    print("🤖🔍 测试带调试信息的高级诊断智能体...")
    
    agent = AdvancedDiagnosisAgent(debug_mode=True)
    
    # 模拟多轮对话 
    test_conversation = [
        "我的服务器CPU很高，系统响应很慢",
        # "从今天早上开始出现的，所有用户都受影响", 
        # "错误日志显示数据库连接池满了，连接超时",
        # "好的，我试试看，谢谢",
    ]
    
    session_id = "debug_session_001"
    
    for i, user_input in enumerate(test_conversation, 1):
        print(f"\n{'💬' * 30}")
        print(f"💬 第{i}轮对话 - 用户输入: {user_input}")
        print(f"{'💬' * 30}")
        
        response = agent.diagnose(user_input, session_id)
        print(f"\n{'🤖' * 10} 助手回复 {'🤖' * 10}")
        print(f"🤖 {response}")
        print(f"{'🤖' * 30}")

if __name__ == "__main__":
    test_advanced_agent_debug()