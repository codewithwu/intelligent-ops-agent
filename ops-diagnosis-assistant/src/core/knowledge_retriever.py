import os
from elasticsearch import Elasticsearch
from dotenv import load_dotenv
import logging
from typing import List, Dict, Any

load_dotenv()

class KnowledgeRetriever:
    def __init__(self):
        self.es_config = {
            "hosts": [f"http://{os.getenv('ELASTICSEARCH_HOST', 'localhost')}:{os.getenv('ELASTICSEARCH_PORT', '9200')}"],
            "verify_certs": False
        }
        self.es_index = "fault_cases"
        self.es_client = None
        self._connect()
    
    def _connect(self):
        """连接Elasticsearch"""
        try:
            self.es_client = Elasticsearch(**self.es_config)
            if self.es_client.ping():
                logging.info("✅ KnowledgeRetriever: Elasticsearch连接成功")
            else:
                logging.error("❌ KnowledgeRetriever: Elasticsearch连接失败")
        except Exception as e:
            logging.error(f"❌ KnowledgeRetriever: Elasticsearch连接失败: {e}")
    
    def search_fault_cases(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """
        搜索相关的故障案例
        
        Args:
            query: 搜索查询
            top_k: 返回最相关的K条记录
            
        Returns:
            相关故障案例列表
        """
        if not self.es_client:
            logging.error("Elasticsearch客户端未初始化")
            return []
        
        try:
            search_body = {
                "query": {
                    "multi_match": {
                        "query": query,
                        "fields": ["symptoms^3", "fault_type^2", "root_cause", "combined_text"],  # symptoms权重最高
                        "fuzziness": "AUTO",  # 模糊搜索
                        "minimum_should_match": "30%"  # 最小匹配度
                    }
                },
                "size": top_k,
                "_source": ["fault_type", "symptoms", "root_cause", "solution", "severity"]
            }
            
            result = self.es_client.search(index=self.es_index, body=search_body)
            hits = result["hits"]["hits"]
            
            logging.info(f"🔍 知识检索: '{query}' -> 找到 {len(hits)} 条相关记录")
            
            # 格式化返回结果
            cases = []
            for hit in hits:
                source = hit["_source"]
                cases.append({
                    "fault_type": source.get("fault_type", ""),
                    "symptoms": source.get("symptoms", ""),
                    "root_cause": source.get("root_cause", ""),
                    "solution": source.get("solution", ""),
                    "severity": source.get("severity", ""),
                    "score": hit["_score"]  # 相关度分数
                })
            
            return cases
            
        except Exception as e:
            logging.error(f"❌ 知识检索失败: {e}")
            return []
    
    def get_related_knowledge(self, user_input: str) -> str:
        """
        获取相关知识并格式化为字符串
        
        Args:
            user_input: 用户输入的问题
            
        Returns:
            格式化后的相关知识文本
        """
        cases = self.search_fault_cases(user_input)
        
        if not cases:
            return "知识库中没有找到相关的故障案例。"
        
        # 格式化相关知识
        knowledge_text = "基于知识库中的相关故障案例，以下信息可能对诊断有帮助：\n\n"
        
        for i, case in enumerate(cases, 1):
            knowledge_text += f"【案例 {i} - {case['fault_type']} (相关度: {case['score']:.2f})】\n"
            knowledge_text += f"故障现象: {case['symptoms']}\n"
            knowledge_text += f"可能原因: {case['root_cause']}\n"
            knowledge_text += f"解决方案: {case['solution']}\n"
            knowledge_text += f"严重程度: {case['severity']}\n"
            knowledge_text += "─" * 50 + "\n"
        
        return knowledge_text

# 测试函数
def test_retriever():
    """测试知识检索器"""
    retriever = KnowledgeRetriever()
    
    test_queries = [
        "服务器CPU使用率很高怎么办",
        "内存不足出现OOM错误",
        "磁盘空间满了无法写入",
        "网站访问很慢延迟高"
    ]
    
    for query in test_queries:
        print(f"\n🔍 测试查询: {query}")
        knowledge = retriever.get_related_knowledge(query)
        print(f"📚 检索到的知识:\n{knowledge}")

if __name__ == "__main__":
    test_retriever()