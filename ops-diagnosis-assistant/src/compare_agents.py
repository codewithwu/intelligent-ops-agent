#!/usr/bin/env python3
"""
对比原始智能体和RAG增强智能体的性能
"""
import time
from core.simple_agent import SimpleDiagnosisAgent
from core.rag_agent import RAGDiagnosisAgent

def compare_agents():
    """对比两个智能体的表现"""
    print("🔬 智能体性能对比测试")
    print("=" * 60)
    
    # 初始化两个智能体
    simple_agent = SimpleDiagnosisAgent()
    rag_agent = RAGDiagnosisAgent()
    
    # 测试用例
    test_cases = [
        "服务器CPU使用率很高怎么办",
        "内存不足出现OOM错误",
        "磁盘空间满了无法写入文件"
    ]
    
    for test_case in test_cases:
        print(f"\n🎯 测试用例: {test_case}")
        print("-" * 40)
        
        # 测试原始智能体
        print("🤖 原始智能体:")
        start_time = time.time()
        try:
            simple_response = simple_agent.diagnose(test_case)
            simple_time = time.time() - start_time
            print(f"   响应时间: {simple_time:.2f}s")
            print(f"   回复长度: {len(simple_response)} 字符")
            print(f"   回复摘要: {simple_response[:150]}...")
        except Exception as e:
            print(f"   ❌ 失败: {e}")
        
        # 测试RAG智能体
        print("\n🤖➕📚 RAG增强智能体:")
        start_time = time.time()
        try:
            rag_response = rag_agent.diagnose(test_case)
            rag_time = time.time() - start_time
            print(f"   响应时间: {rag_time:.2f}s")
            print(f"   回复长度: {len(rag_response)} 字符")
            print(f"   回复摘要: {rag_response[:150]}...")
            
            # 检查是否包含知识库内容
            if "案例" in rag_response or "知识库" in rag_response:
                print("   ✅ 包含知识库引用")
            else:
                print("   ⚠️ 可能未充分利用知识库")
                
        except Exception as e:
            print(f"   ❌ 失败: {e}")
        
        print("\n" + "=" * 60)

if __name__ == "__main__":
    compare_agents()