<template>
  <div class="app-container">
    <!-- 顶部导航 -->
    <el-header class="app-header">
      <div class="logo">🛡️ 烟盾 — 女性二手烟风险评估平台</div>
      <el-menu mode="horizontal" :default-active="activeTab" @select="handleMenuSelect">
        <el-menu-item index="assess">问卷评估</el-menu-item>
        <el-menu-item index="report">我的报告</el-menu-item>
        <el-menu-item index="action">下一步行动</el-menu-item>
        <el-menu-item index="knowledge">控烟知识</el-menu-item>
      </el-menu>
    </el-header>

    <!-- 主内容区 -->
    <el-main class="app-main">
      <!-- 问卷评估页 -->
      <div v-if="activeTab === 'assess'" class="page">
        <QuestionnaireForm @submit="handleSubmit" />
      </div>

      <!-- 报告展示页 -->
      <div v-if="activeTab === 'report'" class="page">
        <ReportViewer v-if="report" :report="report" @print="handlePrint" />
        <el-empty v-else description="暂无报告，请先完成问卷评估"></el-empty>
      </div>

      <!-- 行动入口 -->
      <div v-if="activeTab === 'action'" class="page">
        <ActionGuide />
      </div>

      <!-- 知识库 -->
      <div v-if="activeTab === 'knowledge'" class="page">
        <KnowledgeBase />
      </div>
    </el-main>

    <!-- 加载状态 -->
    <el-dialog v-model="loading" title="正在分析中..." :show-close="false" :close-on-click-modal="false">
      <el-progress :percentage="loadingPercent" :format="() => '正在调用AI引擎...'" />
    </el-dialog>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import axios from 'axios'
import QuestionnaireForm from './components/QuestionnaireForm.vue'
import ReportViewer from './components/ReportViewer.vue'
import ActionGuide from './components/ActionGuide.vue'
import KnowledgeBase from './components/KnowledgeBase.vue'

const activeTab = ref('assess')
const report = ref(null)
const loading = ref(false)
const loadingPercent = ref(0)

const handleMenuSelect = (index) => {
  activeTab.value = index
}

const handleSubmit = async (formData) => {
  loading.value = true
  loadingPercent.value = 0

  try {
    // 调用后端API
    const response = await axios.post('http://127.0.0.1:8000/api/assess', formData)
    report.value = response.data
    loadingPercent.value = 100
    
    // 自动切换到报告页
    setTimeout(() => {
      activeTab.value = 'report'
      loading.value = false
    }, 1000)

    ElMessage.success('评估完成！')
  } catch (error) {
    ElMessage.error(`评估失败：${error.message}`)
    loading.value = false
  }
}

const handlePrint = () => {
  window.print()
}
</script>

<style scoped>
.app-container {
  height: 100vh;
  display: flex;
  flex-direction: column;
}

.app-header {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.logo {
  font-size: 20px;
  font-weight: bold;
  margin-right: 40px;
}

.app-main {
  flex: 1;
  overflow-y: auto;
  background: #f5f7fa;
}

.page {
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
}
</style>
