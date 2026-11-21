<template>
  <main class="main-page">
    <h1>Eye</h1>

    <section class="health-panel" aria-labelledby="health-title">
      <div class="panel-heading">
        <div>
          <h2 id="health-title">后端连接</h2>
          <code>GET /api/health</code>
        </div>
        <el-button type="primary" :loading="loading" @click="testConnection">
          测试连接
        </el-button>
      </div>

      <div class="response" aria-live="polite">
        <el-alert v-if="error" :title="error" type="error" :closable="false" />
        <template v-else-if="payload">
          <el-alert title="连接成功" type="success" :closable="false" />
          <pre>{{ formattedPayload }}</pre>
        </template>
      </div>
    </section>
  </main>
</template>

<script>
import ElAlert from 'element-ui/lib/alert'
import ElButton from 'element-ui/lib/button'
import 'element-ui/lib/theme-chalk/alert.css'
import 'element-ui/lib/theme-chalk/button.css'
import 'element-ui/lib/theme-chalk/icon.css'
import { checkHealth } from '../api/health.js'

export default {
  name: 'MainView',
  components: { ElAlert, ElButton },
  data() {
    return { error: '', loading: false, payload: null }
  },
  computed: {
    formattedPayload() {
      return JSON.stringify(this.payload, null, 2)
    },
  },
  methods: {
    async testConnection() {
      this.loading = true
      this.error = ''
      this.payload = null
      try {
        this.payload = await checkHealth()
      } catch (error) {
        if (error.name === 'TimeoutError') {
          this.error = '连接超时，请确认 Flask 正在监听 5111 端口。'
        } else if (error instanceof TypeError) {
          this.error = '无法连接后端，请确认 Flask 正在监听 5111 端口。'
        } else {
          this.error = error.message
        }
      } finally {
        this.loading = false
      }
    },
  },
}
</script>

<style scoped>
.main-page {
  box-sizing: border-box;
  max-width: 760px;
  margin: 0 auto;
  padding: 64px 24px;
}

h1 {
  margin: 0 0 24px;
  font-size: 42px;
  line-height: 1.15;
  letter-spacing: -0.04em;
}

.health-panel {
  padding: clamp(16px, 4vw, 28px);
  background: #fff;
  border: 1px solid #dce3ef;
  border-radius: 12px;
}

.panel-heading {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

h2 {
  margin: 0 0 6px;
  font-size: 20px;
}

code {
  color: #49607a;
}

.response:not(:empty) {
  margin-top: 18px;
}

pre {
  overflow: auto;
  margin: 12px 0 0;
  padding: 14px;
  background: #f4f6fb;
  border-radius: 6px;
}
</style>
