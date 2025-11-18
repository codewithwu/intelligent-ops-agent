#!/usr/bin/env python3
"""
第一阶段成果演示
"""
import requests
import json

def demo_phase1():
    """演示第一阶段完整功能"""
    base_url = "http://localhost:8000"
    
    print("🎉 第一阶段成果演示 - 运维智能诊断助手")
    print("=" * 50)
    
    # 创建新会话
    print("1. 📝 创建新诊断会话...")
    response = requests.post(f"{base_url}/diagnose", json={
        "message": "你好，我需要运维帮助"
    })
    
    if response.status_code != 200:
        print("❌ 服务不可用，请先启动FastAPI服务")
        return
    
    session_data = response.json()
    session_id = session_data["session_id"]
    
    print(f"✅ 会话创建成功: {session_id}")
    print(f"💬 助手回复: {session_data['response']}")
    
    # 多轮对话演示
    test_cases = [
        "我的服务器CPU使用率很高",
        "内存也不足，经常OOM",
        "网络访问也很慢"
    ]
    
    print("\n2. 🔄 多轮对话演示...")
    for i, case in enumerate(test_cases, 1):
        print(f"\n--- 第{i}轮对话 ---")
        print(f"👤 用户: {case}")
        
        response = requests.post(f"{base_url}/diagnose", json={
            "message": case,
            "session_id": session_id
        })
        
        if response.status_code == 200:
            result = response.json()
            print(f"🤖 助手: {result['response'][:150]}...")
        else:
            print(f"❌ 请求失败: {response.text}")
    
    # 查看会话历史
    print(f"\n3. 📚 查看会话历史...")
    history_response = requests.get(f"{base_url}/session/{session_id}")
    if history_response.status_code == 200:
        history = history_response.json()
        print(f"✅ 会话包含 {history['message_count']} 条消息记录")
    
    print("\n4. 🌐 API文档信息")
    print(f"   文档地址: http://localhost:8000/docs")
    print(f"   健康检查: http://localhost:8000/health")
    
    print("\n🎯 第一阶段目标达成！")
    print("   我们成功构建了一个可用的运维诊断助手MVP")

if __name__ == "__main__":
    demo_phase1()