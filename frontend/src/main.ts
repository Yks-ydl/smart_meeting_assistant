import { createApp } from 'vue'
import './style.css'
import App from './App.vue'

async function bootstrap() {
  // ⚠️ 已禁用 MSW Mock Service Worker
  // 现在使用真实的后端 API（FastAPI）+ VCSum 数据集
  // 原始 mock 数据已被替换为真实数据
  // 
  // if (import.meta.env.DEV) {
  //   const { worker } = await import('./mocks/browser')
  //   await worker.start({
  //     onUnhandledRequest: 'bypass',
  //   })
  // }

  console.log('🚀 智能会议助手启动中...')
  console.log('📊 数据来源：VCSum 真实数据集')
  console.log('🔗 后端服务：http://127.0.0.1:8000')

  createApp(App).mount('#app')
}

bootstrap()
