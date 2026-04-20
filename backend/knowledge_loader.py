import json
import os
from typing import List, Dict
from chromadb import Client
from chromadb.config import Settings
from langchain.text_splitter import RecursiveCharacterTextSplitter

class KnowledgeBaseManager:
    """校园知识库管理器"""
    
    def __init__(self, db_path: str = "./chroma_data"):
        """初始化向量数据库"""
        self.db_path = db_path
        os.makedirs(db_path, exist_ok=True)
        
        # 初始化ChromaDB
        settings = Settings(
            chroma_db_impl="duckdb",
            persist_directory=db_path,
            anonymized_telemetry=False
        )
        self.client = Client(settings)
        
        # 获取或创建集合
        self.collection = self.client.get_or_create_collection(
            name="campus_knowledge",
            metadata={"hnsw:space": "cosine"}  # 使用余弦相似度
        )
        
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=50,
            separators=["\n\n", "\n", "。", "，", " "]
        )
    
    def load_knowledge_base(self, json_path: str = "./knowledge_base.json"):
        """从JSON文件加载知识库"""
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        all_documents = []
        document_ids = []
        metadatas = []
        
        # 加载政策库
        for policy in data.get('policies', []):
            chunks = self.text_splitter.split_text(policy['content'])
            for i, chunk in enumerate(chunks):
                all_documents.append(chunk)
                document_ids.append(f"{policy['id']}_chunk_{i}")
                metadatas.append({
                    "source": "policy",
                    "title": policy['title'],
                    "category": policy['category'],
                    "department": policy['department'],
                    "policy_id": policy['id']
                })
        
        # 加载FAQ库
        for faq in data.get('faqs', []):
            # 问题作为文档
            all_documents.append(f"Q: {faq['question']}\nA: {faq['answer']}")
            document_ids.append(faq['id'])
            metadatas.append({
                "source": "faq",
                "question": faq['question'],
                "category": faq['category'],
                "views": faq['views']
            })
        
        # 加载服务信息
        for service in data.get('services', []):
            text = f"{service['name']}: {service['description']}. 地点：{service['location']}. 电话：{service['contact']}. 营业时间：{service['hours']}"
            all_documents.append(text)
            document_ids.append(service['id'])
            metadatas.append({
                "source": "service",
                "service_name": service['name'],
                "location": service['location']
            })
        
        # 批量添加到向量数据库
        print(f"正在加载{len(all_documents)}条知识...")
        
        # 分批添加（避免一次性过多）
        batch_size = 50
        for i in range(0, len(all_documents), batch_size):
            batch_docs = all_documents[i:i+batch_size]
            batch_ids = document_ids[i:i+batch_size]
            batch_meta = metadatas[i:i+batch_size]
            
            self.collection.add(
                documents=batch_docs,
                ids=batch_ids,
                metadatas=batch_meta
            )
        
        print(f"✓ 知识库加载完成！共{len(all_documents)}条记录")
    
    def search(self, query: str, top_k: int = 5) -> List[Dict]:
        """检索相关知识"""
        results = self.collection.query(
            query_texts=[query],
            n_results=top_k
        )
        
        # 格式化结果
        formatted_results = []
        if results['documents']:
            for doc, meta, distance in zip(
                results['documents'][0],
                results['metadatas'][0],
                results['distances'][0]
            ):
                formatted_results.append({
                    "content": doc,
                    "metadata": meta,
                    "score": 1 - distance  # 转换为相似度分数（0-1）
                })
        
        return formatted_results

# 使用示例
if __name__ == "__main__":
    manager = KnowledgeBaseManager()
    manager.load_knowledge_base()
    
    # 测试搜索
    results = manager.search("怎样申请助学金")
    for r in results:
        print(f"内容: {r['content'][:100]}...")
        print(f"相似度: {r['score']:.2f}")
        print("---")
