import requests
import json
import time
import threading

def test_advanced_api():
    """测试高级API功能"""
    base_url = "http://localhost:8000"
    api_key = "123"  # 默认API密钥
    
    headers = {
        "X-API-Key": api_key,
        "Content-Type": "application/json"
    }
    
    print("🧪 测试高级API功能...")
    
    # 测试1: 健康检查
    try:
        response = requests.get(f"{base_url}/health")
        print(f"✅ 健康检查: {response.status_code}")
        print(f"   详情: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    except Exception as e:
        print(f"❌ 健康检查失败: {e}")
        return
    
    # 测试2: 异步诊断
    print("\n2. 🚀 测试异步诊断...")
    test_cases = [
        # "我的服务器CPU使用率很高，系统响应很慢",
        "内存不足，经常出现OutOfMemoryError"
    ]
    
    task_ids = []
    session_id = None
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"   发送诊断请求 {i}: {test_case}")
        
        data = {
            "message": test_case
        }
        if session_id:
            data["session_id"] = session_id
        
        response = requests.post(
            f"{base_url}/diagnose/async",
            json=data,
            headers=headers
        )
        
        if response.status_code == 200:
            result = response.json()
            task_id = result["task_id"]
            session_id = result["session_id"]
            task_ids.append(task_id)
            
            print(f"   ✅ 任务提交成功")
            print(f"      任务ID: {task_id}")
            print(f"      会话ID: {session_id}")
        else:
            print(f"   ❌ 任务提交失败: {response.text}")
    
    # 测试3: 轮询任务状态
    print("\n3. 🔄 轮询任务状态...")
    for task_id in task_ids:
        print(f"   查询任务状态: {task_id}")
        
        max_attempts = 50
        for attempt in range(max_attempts):
            response = requests.get(
                f"{base_url}/tasks/{task_id}",
                headers=headers
            )
            
            if response.status_code == 200:
                status_data = response.json()
                print(f"wx  status_data {status_data}")
                current_status = status_data["status"]
                
                print(f"      尝试 {attempt + 1}: 状态 = {current_status}")
                
                if current_status == "SUCCESS":
                    print(f"      ✅ 任务完成!")
                    result = status_data.get("result", {}).get("result", {})
                    if result:
                        response_text = result.get("response", "")[:200] + "..." if len(result.get("response", "")) > 200 else result.get("response", "")
                        print(f"      回复摘要: {response_text}")
                    break
                elif current_status == "FAILURE":
                    print(f"      ❌ 任务失败: {status_data.get('error')}")
                    break
                elif current_status == "PROGRESS":
                    progress = status_data.get("progress", {})
                    print(f"      进度: {progress.get('status', '处理中...')}")
            else:
                print(f"      ❌ 状态查询失败: {response.text}")
                break
            
            if attempt < max_attempts - 1:
                time.sleep(2)  # 等待2秒再查询
        else:
            print(f"      ⚠️ 任务超时，最大尝试次数 reached")
    
    # 测试4: 获取会话信息
    if session_id:
        print(f"\n4. 📚 获取会话信息: {session_id}")
        response = requests.get(
            f"{base_url}/sessions/{session_id}",
            headers=headers
        )
        
        if response.status_code == 200:
            session_info = response.json()
            print(f"   ✅ 会话信息获取成功")
            print(f"      诊断阶段: {session_info.get('diagnosis_stage')}")
            print(f"      消息数量: {session_info.get('message_count')}")
        else:
            print(f"   ❌ 会话信息获取失败: {response.text}")
    
    # 测试5: 列出所有会话
    print("\n5. 📋 列出所有会话...")
    response = requests.get(f"{base_url}/sessions", headers=headers)
    if response.status_code == 200:
        sessions_data = response.json()
        print(f"   ✅ 活跃会话: {sessions_data.get('active_sessions', 0)}")
    else:
        print(f"   ❌ 会话列表获取失败: {response.text}")

def monitor_celery_tasks():
    """监控Celery任务的线程函数"""
    time.sleep(1)
    print("\n👷 Celery Worker监控（在另一个终端启动）:")
    print("   python run_celery_worker.py")

if __name__ == "__main__":
    # 启动监控线程
    monitor_thread = threading.Thread(target=monitor_celery_tasks)
    monitor_thread.daemon = True
    monitor_thread.start()
    
    # 运行测试
    test_advanced_api()