import psycopg2
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# 数据库连接配置
DB_CONFIG = {
    "host": os.getenv("POSTGRES_HOST", "localhost"),
    "port": os.getenv("POSTGRES_PORT", "5433"),
    "database": os.getenv("POSTGRES_DB", "ops_knowledge"),
    "user": os.getenv("POSTGRES_USER", "postgres"),
    "password": os.getenv("POSTGRES_PASSWORD", "123456")
}

# 示例运维故障案例数据
SAMPLE_FAULT_CASES = [
    {
        "fault_type": "high_cpu_usage",
        "symptoms": "服务器CPU使用率持续高于90%，系统响应缓慢，用户请求超时，top命令显示某个进程占用大量CPU资源",
        "root_cause": "Java应用程序内存泄漏导致频繁GC，或者存在死循环代码，或者是数据库查询没有索引导致全表扫描",
        "solution": "1. 使用top命令找出CPU占用最高的进程\n2. 使用ps aux --sort=-%cpu查看详细进程信息\n3. 使用jstack分析Java进程线程状态\n4. 检查应用程序日志查找异常\n5. 优化数据库查询，添加缺失索引\n6. 考虑增加CPU资源或优化代码逻辑",
        "severity": "high",
        "frequency": "frequent"
    },
    {
        "fault_type": "memory_leak",
        "symptoms": "服务器内存使用率不断上升，最终触发OOM Killer，系统开始杀死进程，free命令显示可用内存持续减少",
        "root_cause": "应用程序存在内存泄漏，未正确释放内存对象，或者缓存设置不合理导致内存耗尽",
        "solution": "1. 使用free -h查看内存使用情况\n2. 使用ps aux --sort=-%mem查看内存占用最高的进程\n3. 使用jstat监控Java堆内存使用\n4. 分析heap dump文件定位内存泄漏点\n5. 调整JVM内存参数-Xmx -Xms\n6. 检查缓存配置和缓存淘汰策略",
        "severity": "high",
        "frequency": "occasional"
    },
    {
        "fault_type": "disk_space_full",
        "symptoms": "磁盘使用率100%，无法写入新文件，应用程序报错No space left on device，日志文件无法滚动",
        "root_cause": "日志文件未及时清理，大文件占用空间，或者数据库文件增长过快",
        "solution": "1. 使用df -h查看磁盘使用情况\n2. 使用du -sh /* | sort -rh查找大目录\n3. 清理/var/log/目录下的旧日志文件\n4. 检查应用程序日志输出配置\n5. 清理Docker镜像和容器缓存\n6. 设置日志轮转和自动清理策略",
        "severity": "critical",
        "frequency": "frequent"
    },
    {
        "fault_type": "network_latency",
        "symptoms": "网络延迟高，ping响应时间超过100ms，TCP重传率高，用户访问网站缓慢",
        "root_cause": "网络带宽不足，DNS解析慢，或者中间网络设备故障",
        "solution": "1. 使用ping测试基础网络延迟\n2. 使用traceroute查看路由路径\n3. 使用mtr进行持续网络质量监测\n4. 检查DNS解析时间\n5. 使用iftop查看网络流量\n6. 联系网络运营商检查链路质量",
        "severity": "medium",
        "frequency": "occasional"
    },
    {
        "fault_type": "database_connection_pool_full",
        "symptoms": "数据库连接池满，应用程序报错Cannot get connection，新的数据库连接请求被拒绝",
        "root_cause": "数据库连接未正确释放，或者连接池配置过小，或者存在慢查询占用连接时间过长",
        "solution": "1. 检查数据库当前连接数\n2. 查看连接池监控指标\n3. 分析慢查询日志优化SQL\n4. 调整连接池最大连接数配置\n5. 设置合理的连接超时时间\n6. 确保代码中正确关闭数据库连接",
        "severity": "high",
        "frequency": "occasional"
    },
    {
        "fault_type": "service_crash",
        "symptoms": "关键服务进程突然崩溃，系统日志显示Segmentation fault或OutOfMemoryError，服务不可用",
        "root_cause": "内存访问越界，资源耗尽，或者依赖服务不可用",
        "solution": "1. 检查系统日志/var/log/messages\n2. 查看应用程序崩溃日志\n3. 分析core dump文件\n4. 检查系统资源使用情况\n5. 验证依赖服务状态\n6. 配置服务自动重启机制",
        "severity": "critical",
        "frequency": "rare"
    },
    {
        "fault_type": "slow_database_query",
        "symptoms": "数据库查询响应慢，应用程序超时，CPU和IO等待高，用户体验差",
        "root_cause": "缺少合适的索引，SQL写法不合理，或者数据库统计信息过时",
        "solution": "1. 使用EXPLAIN分析慢查询执行计划\n2. 检查表索引情况\n3. 优化SQL语句，避免SELECT *\n4. 添加缺失的索引\n5. 更新数据库统计信息\n6. 考虑读写分离或分库分表",
        "severity": "medium",
        "frequency": "frequent"
    },
    {
        "fault_type": "file_descriptor_exhausted",
        "symptoms": "无法打开新文件或网络连接，报错Too many open files，服务功能受限",
        "root_cause": "文件描述符限制过低，或者程序存在文件描述符泄漏",
        "solution": "1. 使用lsof查看打开的文件描述符\n2. 检查ulimit配置\n3. 调整系统文件描述符限制\n4. 检查应用程序文件操作代码\n5. 重启受影响的服务\n6. 监控文件描述符使用趋势",
        "severity": "high",
        "frequency": "rare"
    },
    {
        "fault_type": "ssl_certificate_expired",
        "symptoms": "HTTPS网站无法访问，浏览器显示证书错误，SSL握手失败",
        "root_cause": "SSL证书过期，或者证书链配置不正确",
        "solution": "1. 检查SSL证书过期时间\n2. 更新过期证书\n3. 验证证书链完整性\n4. 重新配置Web服务器SSL设置\n5. 测试HTTPS访问\n6. 设置证书过期监控告警",
        "severity": "critical",
        "frequency": "rare"
    },
    {
        "fault_type": "load_balancer_issue",
        "symptoms": "部分用户无法访问服务，负载均衡器健康检查失败，后端服务器状态异常",
        "root_cause": "后端服务健康检查端点不可用，或者网络分区，或者负载均衡器配置错误",
        "solution": "1. 检查负载均衡器配置\n2. 验证后端服务健康状态\n3. 检查网络连通性\n4. 查看负载均衡器日志\n5. 测试健康检查端点\n6. 调整健康检查参数",
        "severity": "high",
        "frequency": "occasional"
    }
]

def connect_db():
    """连接数据库"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        print("✅ 数据库连接成功")
        return conn
    except Exception as e:
        print(f"❌ 数据库连接失败: {e}")
        return None

def check_file_exists(file_path):
        """检查指定路径的文件是否存在"""
        return os.path.exists(file_path) and os.path.isfile(file_path)

def init_database():
    """初始化数据库表结构"""
    conn = connect_db()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        
        # 读取并执行初始化SQL
        init_sql_path = os.path.join(os.path.dirname(__file__), "../docker/init/01-init-db.sql")
        if check_file_exists(init_sql_path):
            print(f"文件 {init_sql_path} 存在")
        else:
            print(f"文件 {init_sql_path} 不存在")
            raise ValueError(f"文件 {init_sql_path} 不存在")
    
        with open(init_sql_path, 'r') as f:
            init_sql = f.read()
        
        cursor.execute(init_sql)
        conn.commit()
        print("✅ 数据库表结构初始化成功")
        return True
        
    except Exception as e:
        print(f"❌ 数据库初始化失败: {e}")
        return False
    finally:
        conn.close()

def insert_sample_data():
    """插入示例数据"""
    conn = connect_db()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        
        # 清空现有数据（可选）
        cursor.execute("TRUNCATE TABLE fault_cases RESTART IDENTITY")
        
        # 插入示例数据
        insert_sql = """
        INSERT INTO fault_cases 
        (fault_type, symptoms, root_cause, solution, severity, frequency) 
        VALUES (%s, %s, %s, %s, %s, %s)
        """
        
        for case in SAMPLE_FAULT_CASES:
            cursor.execute(insert_sql, (
                case["fault_type"],
                case["symptoms"],
                case["root_cause"],
                case["solution"],
                case["severity"],
                case["frequency"]
            ))
        
        conn.commit()
        print(f"✅ 成功插入 {len(SAMPLE_FAULT_CASES)} 条故障案例数据")
        return True
        
    except Exception as e:
        print(f"❌ 数据插入失败: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def verify_data():
    """验证数据插入结果"""
    conn = connect_db()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as count, fault_type FROM fault_cases GROUP BY fault_type")
        results = cursor.fetchall()
        
        print("📊 数据验证结果:")
        for count, fault_type in results:
            print(f"   - {fault_type}: {count} 条记录")
        
        cursor.execute("SELECT COUNT(*) as total FROM fault_cases")
        total = cursor.fetchone()[0]
        print(f"📈 总计: {total} 条故障案例")
        
        return True
        
    except Exception as e:
        print(f"❌ 数据验证失败: {e}")
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    print(f"🗃️ 开始初始化运维知识库数据库...")
    
    if init_database() and insert_sample_data():
        verify_data()
        print("🎉 数据库初始化完成！")
    else:
        print("❌ 数据库初始化失败")