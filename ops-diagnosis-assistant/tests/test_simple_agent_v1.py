import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from src.core.simple_agent import SimpleDiagnosisAgent

def test_simple_agent():
    print("🤖 测试 LangGraph 1.x 版本诊断智能体...")
    
    agent = SimpleDiagnosisAgent()
    
    # 测试用例
    test_cases = [
        "我的服务器CPU很高，系统很卡",
        "内存不足，经常出现out of memory错误",
        "网络访问很慢，延迟很高",
        "磁盘空间满了怎么办",  # 未知问题测试
        "网站打不开了"
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{'='*50}")
        print(f"测试用例 {i}: {test_case}")
        print(f"{'='*50}")
        try:
            response = agent.diagnose(test_case)
            print(f"💬 助手回复:\n{response}")
        except Exception as e:
            print(f"❌ 测试失败: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    test_simple_agent()