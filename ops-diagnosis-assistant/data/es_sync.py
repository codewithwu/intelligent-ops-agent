import os
import psycopg2
from elasticsearch import Elasticsearch
from dotenv import load_dotenv
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()

class KnowledgeBaseSync:
    def __init__(self):
        # PostgreSQL连接配置
        self.pg_config = {
            "host": os.getenv("POSTGRES_HOST", "localhost"),
            "port": os.getenv("POSTGRES_PORT", "5433"),
            "database": os.getenv("POSTGRES_DB", "ops_knowledge"),
            "user": os.getenv("POSTGRES_USER", "postgres"),
            "password": os.getenv("POSTGRES_PASSWORD", "123456")
        }
        
        # Elasticsearch连接配置
        self.es_config = {
            "hosts": [f"http://{os.getenv('ELASTICSEARCH_HOST', 'localhost')}:{os.getenv('ELASTICSEARCH_PORT', '9200')}"],
            "verify_certs": False  # 开发环境可以关闭证书验证
        }
        
        self.es_index = "fault_cases"
    
    def connect_postgres(self):
        """连接PostgreSQL"""
        try:
            conn = psycopg2.connect(**self.pg_config)
            logger.info("✅ PostgreSQL连接成功")
            return conn
        except Exception as e:
            logger.error(f"❌ PostgreSQL连接失败: {e}")
            return None
    
    def connect_elasticsearch(self):
        """连接Elasticsearch"""
        try:
            es = Elasticsearch(**self.es_config)
            if es.ping():
                logger.info("✅ Elasticsearch连接成功")
                return es
            else:
                logger.error("❌ Elasticsearch连接失败")
                return None
        except Exception as e:
            logger.error(f"❌ Elasticsearch连接失败: {e}")
            return None
    
    def create_es_index(self, es_client):
        """创建Elasticsearch索引"""
        index_mapping = {
            "mappings": {
                "properties": {
                    "id": {"type": "integer"},
                    "fault_type": {"type": "text", "analyzer": "standard"},
                    "symptoms": {"type": "text", "analyzer": "standard"},
                    "root_cause": {"type": "text", "analyzer": "standard"},
                    "solution": {"type": "text", "analyzer": "standard"},
                    "severity": {"type": "keyword"},
                    "frequency": {"type": "keyword"},
                    "combined_text": {"type": "text", "analyzer": "standard"}  # 用于全文搜索
                }
            },
            "settings": {
                "analysis": {
                    "analyzer": {
                        "default": {
                            "type": "standard"
                        }
                    }
                }
            }
        }
        
        try:
            # 删除已存在的索引（开发环境）
            if es_client.indices.exists(index=self.es_index):
                es_client.indices.delete(index=self.es_index)
                logger.info("🗑️ 删除旧索引")
            
            # 创建新索引
            es_client.indices.create(index=self.es_index, body=index_mapping)
            logger.info("✅ Elasticsearch索引创建成功")
            return True
        except Exception as e:
            logger.error(f"❌ 索引创建失败: {e}")
            return False
    
    def sync_data_to_es(self):
        """同步数据到Elasticsearch"""
        pg_conn = self.connect_postgres()
        es_client = self.connect_elasticsearch()
        
        if not pg_conn or not es_client:
            return False
        
        try:
            # 创建索引
            if not self.create_es_index(es_client):
                return False
            
            # 从PostgreSQL读取数据
            cursor = pg_conn.cursor()
            cursor.execute("""
                SELECT id, fault_type, symptoms, root_cause, solution, severity, frequency 
                FROM fault_cases
            """)
            
            records = cursor.fetchall()
            logger.info(f"📊 从PostgreSQL读取到 {len(records)} 条记录")
            
            # 同步到Elasticsearch
            success_count = 0
            for record in records:
                doc = {
                    "id": record[0],
                    "fault_type": record[1],
                    "symptoms": record[2],
                    "root_cause": record[3],
                    "solution": record[4],
                    "severity": record[5],
                    "frequency": record[6],
                    "combined_text": f"{record[1]} {record[2]} {record[3]} {record[4]}"  # 组合文本用于搜索
                }
                
                # 索引文档
                es_client.index(index=self.es_index, id=record[0], body=doc)
                success_count += 1
            
            # 刷新索引使文档立即可搜索
            es_client.indices.refresh(index=self.es_index)
            
            logger.info(f"✅ 成功同步 {success_count}/{len(records)} 条记录到Elasticsearch")
            return True
            
        except Exception as e:
            logger.error(f"❌ 数据同步失败: {e}")
            return False
        finally:
            pg_conn.close()
    
    def test_es_search(self):
        """测试Elasticsearch搜索功能"""
        es_client = self.connect_elasticsearch()
        if not es_client:
            return
        
        test_queries = [
            "CPU使用率高",
            "内存不足",
            "磁盘空间满",
            "网络延迟",
            "数据库连接"
        ]
        
        logger.info("🧪 测试Elasticsearch搜索功能...")
        
        for query in test_queries:
            search_body = {
                "query": {
                    "multi_match": {
                        "query": query,
                        "fields": ["symptoms", "fault_type", "root_cause", "combined_text"],
                        "fuzziness": "AUTO"
                    }
                },
                "size": 3
            }
            
            try:
                result = es_client.search(index=self.es_index, body=search_body)
                hits = result["hits"]["hits"]
                
                logger.info(f"🔍 搜索 '{query}': 找到 {len(hits)} 条相关记录")
                
                for hit in hits[:2]:  # 只显示前2条
                    source = hit["_source"]
                    logger.info(f"   - {source['fault_type']} (相关度: {hit['_score']:.2f})")
                    
            except Exception as e:
                logger.error(f"❌ 搜索测试失败 '{query}': {e}")

if __name__ == "__main__":
    sync_manager = KnowledgeBaseSync()
    
    print("🔄 开始同步数据到Elasticsearch...")
    if sync_manager.sync_data_to_es():
        print("✅ 数据同步完成！")
        sync_manager.test_es_search()
    else:
        print("❌ 数据同步失败")