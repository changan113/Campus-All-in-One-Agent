from fastapi import FastAPI, WebSocket, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Dict, Optional
import json
import os
from datetime import datetime
from ai_engine import AIConversationEngine

# 初始化FastAPI应用
app = FastAPI(
    title="AI辅导员API",
    description="校园百事通智能体后端服务",
    version="1.0.0"
)

# 跨域配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 初始化AI引擎
ai_engine = AIConversationEngine()

# ============ 数据模型 ============

class ChatMessage(BaseModel):
    """聊天消息"""
    role: str  # "user" 或 "assistant"
    content: str
    timestamp: Optional[datetime] = None

class ChatRequest(BaseModel):
    """用户聊天请求"""
    message: str
    conversation_id: Optional[str] = None  # 对话ID，用于维护上下文
    user_id: Optional[str] = None

class ChatResponse(BaseModel):
    """AI回复"""
    response: str
    sources: List[Dict] = []
    confidence: float
    conversation_id: str
    timestamp: datetime

class ConversationInfo(BaseModel):
    """对话信息"""
    conversation_id: str
    user_id: Optional[str]
    created_at: datetime
    messages: List[ChatMessage] = []

# ============ 存储（简单版，实际应使用数据库） ============

conversations: Dict[str, List[Dict]] = {}  # 存储对话历史

def get_or_create_conversation(conversation_id: str, user_id: Optional[str] = None):
    """获取或创建对话"""
    if conversation_id not in conversations:
        conversations[conversation_id] = {
            "user_id": user_id,
            "created_at": datetime.now(),
            "messages": []
        }
    return conversations[conversation_id]

# ============ API端点 ============

@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "ok",
        "message": "AI辅导员服务正常运行",
        "timestamp": datetime.now()
    }

@app.post("/api/chat")
async def chat(request: ChatRequest) -> ChatResponse:
    """
    核心对话接口
    
    参数:
        message: 用户消息
        conversation_id: 对话ID（用于维护上下文）
        user_id: 用户ID
    
    返回:
        AI回复及相关信息
    """
    
    # 生成或使用现有的对话ID
    if not request.conversation_id:
        request.conversation_id = f"conv_{int(datetime.now().timestamp() * 1000)}"
    
    # 获取或创建对话上下文
    conv = get_or_create_conversation(request.conversation_id, request.user_id)
    
    # 将用户消息添加到历史
    conv["messages"].append({
        "role": "user",
        "content": request.message,
        "timestamp": datetime.now()
    })
    
    try:
        # 调用AI引擎生成回复
        result = await ai_engine.generate_response(
            user_message=request.message,
            conversation_history=conv["messages"][:-1]  # 不包括刚添加的用户消息
        )
        
        # 添加AI回复到历史
        conv["messages"].append({
            "role": "assistant",
            "content": result["response"],
            "timestamp": datetime.now()
        })
        
        # 返回格式化的响应
        return ChatResponse(
            response=result["response"],
            sources=result.get("sources", []),
            confidence=result.get("confidence", 0),
            conversation_id=request.conversation_id,
            timestamp=datetime.now()
        )
    
    except Exception as e:
        return ChatResponse(
            response=f"抱歉，服务出错：{str(e)}",
            sources=[],
            confidence=0,
            conversation_id=request.conversation_id,
            timestamp=datetime.now()
        )

@app.get("/api/conversation/{conversation_id}")
async def get_conversation(conversation_id: str) -> ConversationInfo:
    """获取对话历史"""
    if conversation_id not in conversations:
        raise HTTPException(status_code=404, detail="对话不存在")
    
    conv = conversations[conversation_id]
    return ConversationInfo(
        conversation_id=conversation_id,
        user_id=conv.get("user_id"),
        created_at=conv.get("created_at", datetime.now()),
        messages=conv.get("messages", [])
    )

@app.get("/api/quick-services")
async def get_quick_services():
    """获取快捷服务导航"""
    return {
        "services": [
            {
                "id": "grants",
                "name": "奖助学金",
                "icon": "🏆",
                "description": "查询奖助学金政策和申请流程",
                "quick_questions": [
                    "怎样申请国家助学金？",
                    "国家奖学金的申请条件是什么？",
                    "助学贷款怎么申请？"
                ]
            },
            {
                "id": "academics",
                "name": "学籍管理",
                "icon": "📚",
                "description": "学籍相关问题咨询",
                "quick_questions": [
                    "怎样转专业？",
                    "如何查询成绩？",
                    "旷课有什么后果？"
                ]
            },
            {
                "id": "facilities",
                "name": "校园设施",
                "icon": "🏫",
                "description": "查询教室、宿舍等设施信息",
                "quick_questions": [
                    "如何查询空教室？",
                    "图书馆什么时候开放？",
                    "校医院在哪里？"
                ]
            },
            {
                "id": "student-life",
                "name": "学生生活",
                "icon": "🎓",
                "description": "生活服务相关问题",
                "quick_questions": [
                    "校园卡丢失怎么办？",
                    "宿舍什么时候熄灯？",
                    "如何办理住宿？"
                ]
            },
            {
                "id": "health",
                "name": "健康医疗",
                "icon": "🏥",
                "description": "医疗卫生相关信息",
                "quick_questions": [
                    "校医院如何就诊？",
                    "医疗费用怎么收费？",
                    "学生保险如何理赔？"
                ]
            }
        ]
    }

@app.get("/api/popular-questions")
async def get_popular_questions():
    """获取热门问题"""
    return {
        "questions": [
            {
                "id": 1,
                "question": "怎样申请助学金",
                "views": 1250,
                "category": "财务"
            },
            {
                "id": 2,
                "question": "如何查询空教室",
                "views": 2100,
                "category": "学习"
            },
            {
                "id": 3,
                "question": "学费缴纳截止日期",
                "views": 1560,
                "category": "财务"
            },
            {
                "id": 4,
                "question": "校园卡丢失怎么办",
                "views": 980,
                "category": "生活"
            },
            {
                "id": 5,
                "question": "宿舍什么时候熄灯",
                "views": 1320,
                "category": "生活"
            }
        ]
    }

@app.post("/api/feedback")
async def submit_feedback(
    conversation_id: str,
    rating: int,  # 1-5
    comment: Optional[str] = None
):
    """提交用户反馈，用于优化AI"""
    # 这里可以保存反馈到数据库，用于持续改进
    return {
        "success": True,
        "message": "感谢您的反馈！我们会不断改进服务。"
    }

# ============ WebSocket连接（可选，用于实时对话） ============

@app.websocket("/ws/chat/{conversation_id}")
async def websocket_endpoint(websocket: WebSocket, conversation_id: str):
    """WebSocket实时聊天端点"""
    await websocket.accept()
    
    try:
        while True:
            # 接收客户端消息
            data = await websocket.receive_json()
            user_message = data.get("message", "")
            
            if not user_message:
                continue
            
            # 调用AI引擎
            conv = get_or_create_conversation(conversation_id)
            result = await ai_engine.generate_response(
                user_message=user_message,
                conversation_history=conv.get("messages", [])
            )
            
            # 发送响应
            await websocket.send_json({
                "response": result["response"],
                "sources": result.get("sources", []),
                "confidence": result.get("confidence", 0)
            })
    
    except Exception as e:
        await websocket.close(code=1000, reason=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
