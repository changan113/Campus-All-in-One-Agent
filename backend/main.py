from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

# 解决前端跨域调用问题
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============ 数据模型 ============
class QuestionnaireInput(BaseModel):
    """问卷数据结构"""
    exposure_years: int          # 暴露年限
    daily_hours: int             # 每日暴露时长（小时）
    environment_types: list      # 暴露环境（家庭/办公室/餐厅等）
    ventilation_level: str       # 通风情况（差/中/好）
    age: int                      # 年龄
    existing_symptoms: list      # 现有症状（咳嗽/呼吸困难等）

class RiskAssessmentReport(BaseModel):
    """风险评估报告结构"""
    risk_score: float            # 综合风险分数（0-100）
    risk_level: str              # 风险等级（低/中/高/极高）
    ai_analysis: str             # AI生成的分析文本
    recommendations: list        # 防护建议
    benchmark_percentile: float  # 在同龄人中的百分位

# ============ 核心算法：风险评分计算 ============
def calculate_risk_score(data: QuestionnaireInput) -> tuple[float, str]:
    """
    基于二手烟暴露评估量表（SHSES）的风险计算
    返回：(风险分数, 风险等级)
    """
    # Step 1: 基础暴露指数 = 暴露年限 × 每日小时数
    exposure_index = min(data.exposure_years * data.daily_hours / 10, 40)  # 标准化到40分以内
    
    # Step 2: 环境加权分
    environment_weights = {
        "家庭": 1.2,      # 家庭通风最差，权重最高
        "办公室": 0.9,
        "餐厅": 1.0,
        "公共交通": 0.8
    }
    env_score = sum(environment_weights.get(env, 0.8) for env in data.environment_types) / max(len(data.environment_types), 1)
    
    # Step 3: 通风调整系数
    ventilation_factors = {"差": 1.3, "中": 1.0, "好": 0.6}
    ventilation_factor = ventilation_factors.get(data.ventilation_level, 1.0)
    
    # Step 4: 症状加权
    symptom_weight = len(data.existing_symptoms) * 8  # 每个症状加8分
    
    # Step 5: 综合风险分数
    risk_score = (exposure_index * env_score * ventilation_factor) + symptom_weight
    risk_score = min(100, max(0, risk_score))  # 限制在0-100
    
    # Step 6: 风险等级判定
    if risk_score < 25:
        risk_level = "低风险"
    elif risk_score < 50:
        risk_level = "中风险"
    elif risk_score < 75:
        risk_level = "高风险"
    else:
        risk_level = "极高风险"
    
    return risk_score, risk_level

# ============ AI报告生成（调用DeepSeek API） ============
async def generate_ai_report(data: QuestionnaireInput, risk_score: float, risk_level: str) -> str:
    """
    调用DeepSeek API生成个性化分析报告
    需要在 .env 文件中设置：DEEPSEEK_API_KEY
    """
    api_key = os.getenv("DEEPSEEK_API_KEY")
    
    prompt = f"""
基于以下二手烟暴露信息，请生成一份专业的健康风险评估报告（200字内）：

用户信息：
- 年龄：{data.age}岁
- 暴露年限：{data.exposure_years}年
- 日均暴露时长：{data.daily_hours}小时
- 主要暴露环境：{', '.join(data.environment_types)}
- 通风情况：{data.ventilation_level}
- 现有症状：{', '.join(data.existing_symptoms) if data.existing_symptoms else '无'}

系统评估结果：
- 综合风险分数：{risk_score:.1f}/100
- 风险等级：{risk_level}

请从以下角度分析：
1. 当前健康风险的科学解释
2. 可能的短期和长期健康影响
3. 个性化的防护和改善建议

回应应该充满同情心且基于证据。
"""
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.deepseek.com/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "deepseek-chat",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.7,
                    "max_tokens": 500
                }
            )
            result = response.json()
            return result["choices"][0]["message"]["content"]
    except Exception as e:
        return f"AI分析失败：{str(e)}。请稍后重试。"

# ============ 基准人群对照数据 ============
def get_benchmark_data(age: int, risk_score: float) -> float:
    """
    返回用户在同龄人中的百分位排名
    （真实应用中应从数据库查询大样本数据）
    """
    # 模拟数据：同龄人风险分数分布
    benchmark_distributions = {
        "20-30": [15, 28, 35, 42, 50, 58, 65, 72, 80, 88],
        "30-40": [20, 32, 40, 48, 55, 62, 70, 78, 85, 92],
        "40-50": [25, 38, 45, 55, 62, 70, 78, 85, 90, 96],
        "50-60": [30, 42, 50, 60, 68, 75, 82, 88, 94, 99],
    }
    
    age_group = "20-30" if age < 30 else ("30-40" if age < 40 else ("40-50" if age < 50 else "50-60"))
    distribution = benchmark_distributions.get(age_group, [50])
    
    percentile = sum(1 for score in distribution if score <= risk_score) / len(distribution) * 100
    return percentile

# ============ API端点 ============

@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {"status": "ok", "message": "烟盾后端服务正常运行"}

@app.post("/api/assess")
async def assess_risk(data: QuestionnaireInput) -> RiskAssessmentReport:
    """
    核心评估端点
    输入：问卷数据
    输出：风险评估报告
    """
    # Step 1: 计算风险分数
    risk_score, risk_level = calculate_risk_score(data)
    
    # Step 2: 获取基准百分位
    percentile = get_benchmark_data(data.age, risk_score)
    
    # Step 3: 生成AI分析报告
    ai_analysis = await generate_ai_report(data, risk_score, risk_level)
    
    # Step 4: 生成防护建议
    recommendations = []
    if risk_score > 50:
        recommendations.append("✓ 强烈建议增加室内通风或使用空气净化器")
    if "家庭" in data.environment_types:
        recommendations.append("✓ 建议家庭成员共同制定无烟计划")
    if data.exposure_years > 5:
        recommendations.append("✓ 建议定期进行肺功能检查")
    recommendations.append("✓ 了解当地控烟政策，查询无烟场所")
    
    return RiskAssessmentReport(
        risk_score=risk_score,
        risk_level=risk_level,
        ai_analysis=ai_analysis,
        recommendations=recommendations,
        benchmark_percentile=percentile
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
