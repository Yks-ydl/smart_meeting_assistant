import { createApp } from 'vue'
import './style.css'
import App from './App.vue'

async function bootstrap() {
  // ⚠️ 已禁用 MSW Mock Service Worker
  // 现在使用真实的后端 API（FastAPI）+ 目录音频 demo 流程
  // 原始 mock 数据已被真实服务链路替换
  // 
  // if (import.meta.env.DEV) {
  //   const { worker } = await import('./mocks/browser')
  //   await worker.start({
  //     onUnhandledRequest: 'bypass',
  //   })
  // }

  console.log('🚀 智能会议助手启动中...')
  console.log('📊 默认数据来源：本地目录音频（可切换到 VCSum 回退模式）')
  console.log('🔗 后端服务：http://127.0.0.1:8000')

  createApp(App).mount('#app')
}

bootstrap()
