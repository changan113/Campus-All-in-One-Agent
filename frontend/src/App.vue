<template>
  <div class="app-container">
    <!-- 导航栏 -->
    <nav class="navbar">
      <div class="navbar-content">
        <div class="logo">
          <span class="logo-icon">🤖</span>
          <span class="logo-text">AI辅导员</span>
        </div>
        <div class="nav-items">
          <span class="nav-item" @click="showAbout = true">关于</span>
          <span class="nav-item" @click="clearChat">新建对话</span>
        </div>
      </div>
    </nav>

    <!-- 主容器 -->
    <div class="main-container">
      <!-- 侧边栏：快捷服务 -->
      <aside class="sidebar" v-if="!chatStarted">
        <div class="sidebar-content">
          <h3>快捷服务导航</h3>
          <div class="services-grid">
            <div 
              v-for="service in quickServices" 
              :key="service.id"
              class="service-card"
              @click="selectService(service)"
            >
              <div class="service-icon">{{ service.icon }}</div>
              <div class="service-name">{{ service.name }}</div>
              <div class="service-desc">{{ service.description }}</div>
            </div>
          </div>

          <h3 style="margin-top: 30px;">热门问题</h3>
          <div class="popular-questions">
            <div 
              v-for="q in popularQuestions" 
              :key="q.id"
              class="question-item"
              @click="sendMessage(q.question)"
            >
              <span class="q-text">{{ q.question }}</span>
              <span class="q-views">{{ q.views }}</span>
            </div>
          </div>
        </div>
      </aside>

      <!-- 聊天主区域 -->
      <main class="chat-container">
        <!-- 欢迎屏幕 -->
        <div v-if="!chatStarted" class="welcome-screen">
          <div class="welcome-content">
            <div class="welcome-avatar">🤖</div>
            <h1>Hi，我是你的AI辅导员</h1>
            <p>我可以帮你解答关于学校的各种问题</p>
            <p style="font-size: 14px; color: #999; margin-top: 20px;">
              📚 校园政策 | 📝 办事流程 | 🏢 设施查询 | 💬 在线咨询
            </p>
          </div>
        </div>

        <!-- 聊天消息区 -->
        <div v-if="chatStarted" class="messages-area">
          <div 
            v-for="(msg, index) in messages" 
            :key="index"
            :class="['message-item', msg.role]"
          >
            <!-- AI消息 -->
            <div v-if="msg.role === 'assistant'" class="ai-message">
              <div class="ai-avatar">🤖</div>
              <div class="message-bubble">
                <div class="message-text">{{ msg.content }}</div>
                
                <!-- 知识源显示 -->
                <div v-if="msg.sources && msg.sources.length > 0" class="sources">
                  <div class="sources-title">📚 相关信息来源</div>
                  <div v-for="(src, idx) in msg.sources" :key="idx" class="source-item">
                    <span v-if="src.type === 'policy'" class="source-tag">政策</span>
                    <span v-else-if="src.type === 'faq'" class="source-tag">FAQ</span>
                    <span class="source-text">
                      {{ src.title || src.question }}
                    </span>
                    <span class="relevance">相关度: {{ (src.relevance * 100).toFixed(0) }}%</span>
                  </div>
                </div>

                <!-- 置信度显示 -->
                <div class="confidence-bar">
                  <div class="confidence-label">回答置信度: {{ msg.confidence.toFixed(0) }}%</div>
                  <div class="confidence-fill" :style="{ width: msg.confidence + '%' }"></div>
                </div>
              </div>
            </div>

            <!-- 用户消息 -->
            <div v-else class="user-message">
              <div class="message-bubble">{{ msg.content }}</div>
              <div class="user-avatar">👤</div>
            </div>
          </div>

          <!-- 加载状态 -->
          <div v-if="loading" class="message-item assistant">
            <div class="ai-message">
              <div class="ai-avatar">🤖</div>
              <div class="message-bubble">
                <div class="typing-animation">
                  <span></span><span></span><span></span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 输入区 -->
        <div class="input-area">
          <div class="input-container">
            <input 
              v-model="inputMessage"
              @keyup.enter="sendMessage(inputMessage)"
              @focus="chatStarted = true"
              placeholder="请输入您的问题..."
              class="chat-input"
            />
            <button @click="sendMessage(inputMessage)" class="send-btn">
              <span v-if="!loading">发送</span>
              <span v-else>发送中...</span>
            </button>
          </div>

          <!-- 快速回复建议 -->
          <div v-if="suggestedQuestions.length > 0" class="suggested-questions">
            <div 
              v-for="(q, idx) in suggestedQuestions" 
              :key="idx"
              class="suggested-btn"
              @click="sendMessage(q)"
            >
              {{ q }}
            </div>
          </div>
        </div>
      </main>
    </div>

    <!-- 反馈对话框 -->
    <el-dialog v-model="showFeedback" title="您觉得这个回答怎么样？" width="400px">
      <div class="feedback-form">
        <el-rate v-model="feedbackRating" :texts="['很差', '不太好', '一般', '很好', '非常好']" />
        <el-input 
          v-model="feedbackComment"
          type="textarea"
          placeholder="可以告诉我们哪些地方需要改进..."
          rows="4"
          style="margin-top: 15px;"
        />
      </div>
      <template #footer>
        <el-button @click="showFeedback = false">取消</el-button>
        <el-button type="primary" @click="submitFeedback">提交反馈</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, nextTick, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import axios from 'axios'

// 配置
const API_BASE = 'http://127.0.0.1:8000/api'

// 状态
const messages = ref([])
const inputMessage = ref('')
const loading = ref(false)
const chatStarted = ref(false)
const conversationId = ref('')
const quickServices = ref([])
const popularQuestions = ref([])
const showFeedback = ref(false)
const feedbackRating = ref(5)
const feedbackComment = ref('')
const showAbout = ref(false)
const lastAIMessage = ref(null)

// 计算属性
const suggestedQuestions = computed(() => {
  if (messages.value.length === 0) return []
  const lastMsg = messages.value[messages.value.length - 1]
  if (lastMsg.role === 'assistant' && lastMsg.suggested) {
    return lastMsg.suggested
  }
  return []
})

// 初始化
onMounted(async () => {
  // 生成对话ID
  conversationId.value = `conv_${Date.now()}`
  
  // 加载快捷服务和热门问题
  await loadQuickServices()
  await loadPopularQuestions()
})

// 加载快捷服务
const loadQuickServices = async () => {
  try {
    const response = await axios.get(`${API_BASE}/quick-services`)
    quickServices.value = response.data.services
  } catch (error) {
    console.error('加载快捷服务失败:', error)
  }
}

// 加载热门问题
const loadPopularQuestions = async () => {
  try {
    const response = await axios.get(`${API_BASE}/popular-questions`)
    popularQuestions.value = response.data.questions
  } catch (error) {
    console.error('加载热门问题失败:', error)
  }
}

// 选择服务
const selectService = (service) => {
  chatStarted.value = true
  const question = service.quick_questions[0]
  sendMessage(question)
}

// 发送消息
const sendMessage = async (message) => {
  if (!message.trim()) return
  
  // 添加用户消息
  messages.value.push({
    role: 'user',
    content: message
  })
  
  inputMessage.value = ''
  loading.value = true
  
  try {
    // 调用API
    const response = await axios.post(`${API_BASE}/chat`, {
      message: message,
      conversation_id: conversationId.value
    })
    
    // 添加AI回复
    const aiMessage = {
      role: 'assistant',
      content: response.data.response,
      sources: response.data.sources,
      confidence: response.data.confidence,
      suggested: generateSuggestedQuestions(response.data.response)
    }
    
    messages.value.push(aiMessage)
    lastAIMessage.value = aiMessage
    
    // 滚动到底部
    await nextTick()
    scrollToBottom()
    
    // 显示反馈提示
    setTimeout(() => {
      if (response.data.confidence < 80) {
        ElMessage.warning('我对这个回答的把握不是很大，欢迎点击反馈帮助我改进！')
      }
    }, 1000)
    
  } catch (error) {
    ElMessage.error('发送消息失败，请重试')
    console.error(error)
  } finally {
    loading.value = false
  }
}

// 生成建议问题
const generateSuggestedQuestions = (response) => {
  // 简单的启发式方法，实际可以用更复杂的逻辑
  if (response.includes('助学金')) {
    return ['国家奖学金申请条件是什么？', '助学贷款怎么申请？']
  } else if (response.includes('教室')) {
    return ['图书馆什么时候开放？', '自习室如何预约？']
  }
  return []
}

// 滚动到底部
const scrollToBottom = () => {
  const container = document.querySelector('.messages-area')
  if (container) {
    container.scrollTop = container.scrollHeight
  }
}

// 清除聊天
const clearChat = () => {
  messages.value = []
  chatStarted.value = false
  conversationId.value = `conv_${Date.now()}`
}

// 提交反馈
const submitFeedback = async () => {
  try {
    await axios.post(`${API_BASE}/feedback`, {
      conversation_id: conversationId.value,
      rating: feedbackRating.value,
      comment: feedbackComment.value
    })
    
    ElMessage.success('感谢您的反馈！')
    showFeedback.value = false
    feedbackRating.value = 5
    feedbackComment.value = ''
  } catch (error) {
    ElMessage.error('反馈提交失败')
  }
}
</script>

<style scoped>
* {
  box-sizing: border-box;
}

.app-container {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
}

/* ============ 导航栏 ============ */
.navbar {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 15px 30px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
}

.navbar-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  max-width: 1400px;
  margin: 0 auto;
}

.logo {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 20px;
  font-weight: bold;
}

.logo-icon {
  font-size: 28px;
}

.nav-items {
  display: flex;
  gap: 20px;
}

.nav-item {
  cursor: pointer;
  opacity: 0.8;
  transition: opacity 0.3s;
}

.nav-item:hover {
  opacity: 1;
}

/* ============ 主容器 ============ */
.main-container {
  display: flex;
  flex: 1;
  overflow: hidden;
  gap: 15px;
  padding: 15px;
}

/* ============ 侧边栏 ============ */
.sidebar {
  width: 280px;
  background: white;
  border-radius: 12px;
  overflow-y: auto;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
}

.sidebar-content {
  padding: 20px;
}

.sidebar-content h3 {
  margin: 0 0 15px 0;
  font-size: 16px;
  color: #333;
}

.services-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 12px;
}

.service-card {
  padding: 15px;
  border: 2px solid #e8e8e8;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.3s;
  text-align: center;
}

.service-card:hover {
  border-color: #667eea;
  background: #f5f7ff;
  transform: translateY(-2px);
}

.service-icon {
  font-size: 24px;
  margin-bottom: 8px;
}

.service-name {
  font-weight: bold;
  margin-bottom: 4px;
}

.service-desc {
  font-size: 12px;
  color: #999;
}

.popular-questions {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.question-item {
  padding: 10px;
  background: #f5f7fa;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  transition: all 0.3s;
}

.question-item:hover {
  background: #667eea;
  color: white;
}

.q-text {
  flex: 1;
}

.q-views {
  font-size: 11px;
  opacity: 0.7;
}

/* ============ 聊天容器 ============ */
.chat-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: white;
  border-radius: 12px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
  overflow: hidden;
}

.welcome-screen {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}

.welcome-content {
  text-align: center;
}

.welcome-avatar {
  font-size: 80px;
  margin-bottom: 20px;
}

.welcome-screen h1 {
  margin: 0 0 10px 0;
  color: #333;
}

.welcome-screen p {
  color: #999;
  margin: 5px 0;
}

/* ============ 消息区 ============ */
.messages-area {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.message-item {
  display: flex;
  gap: 10px;
  animation: slideIn 0.3s ease-out;
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.message-item.user {
  justify-content: flex-end;
}

.message-item.assistant {
  justify-content: flex-start;
}

.ai-avatar, .user-avatar {
  font-size: 24px;
  min-width: 30px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.message-bubble {
  max-width: 60%;
  padding: 12px 16px;
  border-radius: 12px;
  word-wrap: break-word;
  white-space: pre-wrap;
}

.ai-message .message-bubble {
  background: #f0f0f0;
  color: #333;
}

.user-message .message-bubble {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.message-text {
  margin-bottom: 10px;
  line-height: 1.5;
}

/* ============ 知识源 ============ */
.sources {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid #e0e0e0;
  font-size: 12px;
}

.sources-title {
  color: #666;
  margin-bottom: 8px;
  font-weight: bold;
}

.source-item {
  display: flex;
  gap: 8px;
  margin-bottom: 6px;
  align-items: center;
}

.source-tag {
  background: #667eea;
  color: white;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: bold;
  min-width: 40px;
  text-align: center;
}

.source-text {
  flex: 1;
  color: #666;
}

.relevance {
  color: #999;
  font-size: 11px;
}

/* ============ 置信度条 ============ */
.confidence-bar {
  margin-top: 10px;
  font-size: 11px;
  color: #999;
}

.confidence-label {
  margin-bottom: 4px;
}

.confidence-fill {
  height: 4px;
  background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
  border-radius: 2px;
  transition: width 0.5s ease;
}

/* ============ 打字动画 ============ */
.typing-animation {
  display: flex;
  gap: 4px;
}

.typing-animation span {
  width: 8px;
  height: 8px;
  background: #667eea;
  border-radius: 50%;
  animation: typing 1.4s infinite;
}

.typing-animation span:nth-child(2) {
  animation-delay: 0.2s;
}

.typing-animation span:nth-child(3) {
  animation-delay: 0.4s;
}

@keyframes typing {
  0%, 60%, 100% {
    opacity: 0.3;
    transform: translateY(0);
  }
  30% {
    opacity: 1;
    transform: translateY(-10px);
  }
}

/* ============ 输入区 ============ */
.input-area {
  padding: 20px;
  border-top: 1px solid #e8e8e8;
  background: #fafafa;
}

.input-container {
  display: flex;
  gap: 10px;
  margin-bottom: 10px;
}

.chat-input {
  flex: 1;
  padding: 12px 16px;
  border: 1px solid #ddd;
  border-radius: 24px;
  font-size: 14px;
  outline: none;
  transition: border-color 0.3s;
}

.chat-input:focus {
  border-color: #667eea;
}

.send-btn {
  padding: 12px 24px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  border-radius: 24px;
  cursor: pointer;
  font-weight: bold;
  transition: transform 0.3s;
}

.send-btn:hover:not(:disabled) {
  transform: scale(1.05);
}

.send-btn:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

/* ============ 建议问题 ============ */
.suggested-questions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.suggested-btn {
  padding: 8px 12px;
  background: white;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.3s;
}

.suggested-btn:hover {
  border-color: #667eea;
  color: #667eea;
  background: #f5f7ff;
}

/* ============ 响应式 ============ */
@media (max-width: 768px) {
  .main-container {
    flex-direction: column;
  }

  .sidebar {
    width: 100%;
    max-height: 200px;
  }

  .message-bubble {
    max-width: 100%;
  }
}
</style>
