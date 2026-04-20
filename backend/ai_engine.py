import os
import httpx
from typing import List, Dict
from dotenv import load_dotenv
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from knowledge_loader import KnowledgeBaseManager

load_dotenv()

class AIConversationEngine:
    """AI对话引擎 - 使用RAG（检索增强生成）"""
    
    def __init__(self):
        self.api_key = os.getenv("DEEPSEEK_API_KEY")
        self.api_url = os.getenv("DEEPSEEK_API_URL", "https://api.deepseek.com/v1")
        self.knowledge_base = KnowledgeBaseManager()
        
        # 加载知识库
        self.knowledge_base.load_knowledge_base()
        
        # 定义AI辅导员的人格
        self.system_prompt = """你是一个友善、专业的校园AI辅导员助手。你的职责是帮助学生解决关于校园的各种问题。

你的特点：
1. 亲切友善：使用学生能理解的语言，避免复杂的行政用语
2. 专业认真：基于知识库提供准确的校园政策和流程信息
3. 主动帮助：如果学生没有明确问题，可以主动介绍你能提供的服务
4. 个性化服务：根据学生的具体情况给出针对性建议
5. 信息准确：如果知识库中没有相关信息，要诚实地表示，并提供相关部门的联系方式

你拥有以下服务能力：
- 奖助学金申请指导
- 学籍管理咨询
- 校园设施查询
- 学生服务导航
- 政策流程解读

在回答时，如果涉及具体的流程或政策，请：
1. 先用简洁的语言总结关键点
2. 按步骤详细说明
3. 给出相关部门和联系方式"""
    
    async def generate_response(
        self,
        user_message: str,
        conversation_history: List[Dict] = None
    ) -> Dict:
        """
        生成对话回复（使用RAG）
        
        Args:
            user_message: 用户输入
            conversation_history: 对话历史
        
        Returns:
            包含回复内容、相关知识源等的字典
        """
        
        if conversation_history is None:
            conversation_history = []
        
        # Step 1: 从知识库检索相关信息
        retrieved_docs = self.knowledge_base.search(user_message, top_k=3)
        
        # Step 2: 构建增强的提示词
        context = self._build_context(retrieved_docs)
        
        # Step 3: 构建消息列表
        messages = [
            {"role": "system", "content": self.system_prompt}
        ]
        
        # 添加对话历史（最多保留最近3轮）
        for msg in conversation_history[-3:]:
            messages.append(msg)
        
        # 添加当前消息和上下文
        messages.append({
            "role": "user",
            "content": f"{user_message}\n\n【相关校园知识库信息】\n{context}"
        })
        
        # Step 4: 调用DeepSeek API
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.api_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "deepseek-chat",
                        "messages": messages,
                        "temperature": 0.7,
                        "max_tokens": 1000,
                        "top_p": 0.95
                    },
                    timeout=30.0
                )
                
                result = response.json()
                
                if response.status_code == 200:
                    ai_response = result["choices"][0]["message"]["content"]
                    
                    return {
                        "success": True,
                        "response": ai_response,
                        "sources": self._extract_sources(retrieved_docs),
                        "confidence": self._calculate_confidence(retrieved_docs)
                    }
                else:
                    return {
                        "success": False,
                        "error": result.get("error", {}).get("message", "API调用失败"),
                        "response": "抱歉，我暂时无法回答这个问题。请稍后重试，或联系学生服务中心。"
                    }
        
        except httpx.TimeoutException:
            return {
                "success": False,
                "error": "API请求超时",
                "response": "抱歉，网络连接较慢，请稍后重试。"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "response": f"出错了：{str(e)}"
            }
    
    def _build_context(self, retrieved_docs: List[Dict]) -> str:
        """构建检索到的知识的上下文"""
        if not retrieved_docs:
            return "（知识库中未找到相关信息）"
        
        context_parts = []
        for i, doc in enumerate(retrieved_docs, 1):
            meta = doc['metadata']
            source_type = meta.get('source', 'unknown')
            
            if source_type == 'policy':
                context_parts.append(
                    f"{i}. 【政策】{meta.get('title', '无标题')}\n"
                    f"   分类：{meta.get('category', '')}\n"
                    f"   部门：{meta.get('department', '')}\n"
                    f"   内容摘要：{doc['content'][:200]}..."
                )
            elif source_type == 'faq':
                context_parts.append(
                    f"{i}. 【常见问题】Q: {meta.get('question', '')}\n"
                    f"   A: {doc['content'][:200]}..."
                )
            elif source_type == 'service':
                context_parts.append(
                    f"{i}. 【服务】{meta.get('service_name', '')}\n"
                    f"   {doc['content']}"
                )
        
        return "\n\n".join(context_parts)
    
    def _extract_sources(self, retrieved_docs: List[Dict]) -> List[Dict]:
        """提取知识源"""
        sources = []
        for doc in retrieved_docs:
            meta = doc['metadata']
            if meta.get('source') == 'policy':
                sources.append({
                    "type": "policy",
                    "title": meta.get('title', ''),
                    "department": meta.get('department', ''),
                    "relevance": doc['score']
                })
            elif meta.get('source') == 'faq':
                sources.append({
                    "type": "faq",
                    "question": meta.get('question', ''),
                    "relevance": doc['score']
                })
        
        return sources
    
    def _calculate_confidence(self, retrieved_docs: List[Dict]) -> float:
        """计算回答的置信度"""
        if not retrieved_docs:
            return 0.0
        
        # 基于最高匹配分数计算置信度
        max_score = max(doc['score'] for doc in retrieved_docs)
        
        # 分数转换为置信度百分比
        return min(100, max(30, max_score * 100))
