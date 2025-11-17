import requests
import json
import time

def test_api():
    """测试FastAPI接口"""
    base_url = "http://localhost:8000"
    
    print("🧪 开始测试FastAPI接口...")
    
    # 测试1: 健康检查
    try:
        response = requests.get(f"{base_url}/health")
        print(f"✅ 健康检查: {response.status_code} - {response.json()}")
    except Exception as e:
        print(f"❌ 健康检查失败: {e}")
        return
    
    # 测试2: 根路径
    response = requests.get(f"{base_url}/")
    print(f"✅ API信息: {response.json()}")
    
    # 测试3: 诊断请求
    test_cases = [
        "我的服务器CPU很高",
        "内存不足怎么办",
        "网站访问很慢"
    ]
    
    session_id = None
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n--- 测试诊断请求 {i} ---")
        
        # 准备请求数据
        data = {
            "message": test_case
        }
        if session_id:
            data["session_id"] = session_id
        
        # 发送诊断请求
        response = requests.post(
            f"{base_url}/diagnose",
            json=data,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            result = response.json()
            session_id = result["session_id"]
            print(f"✅ 诊断成功 (会话: {session_id})")
            print(f"💬 助手回复: {result['response'][:200]}...")  # 只显示前200字符
        else:
            print(f"❌ 诊断失败: {response.status_code} - {response.text}")
        
        # 短暂暂停
        time.sleep(1)
    
    # 测试4: 获取会话历史
    if session_id:
        print(f"\n--- 获取会话历史 ---")
        response = requests.get(f"{base_url}/session/{session_id}")
        if response.status_code == 200:
            history = response.json()
            print(f"✅ 会话历史获取成功，共 {history['message_count']} 条消息")
        else:
            print(f"❌ 会话历史获取失败: {response.text}")

if __name__ == "__main__":
    test_api()