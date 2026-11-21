<template>
  <el-card class="connection-card" shadow="never">
    <p class="description">测试 MySQL 是否可用，或保存为 Eye 后端使用的连接。</p>

    <el-form
      ref="connectionForm"
      :model="form"
      :rules="rules"
      :disabled="loadingSettings || Boolean(pendingAction)"
      label-position="top"
      @submit.native.prevent="submitConnection('save')"
    >
      <div class="address-row">
        <el-form-item label="主机地址" prop="host">
          <el-input
            v-model.trim="form.host"
            placeholder="例如 127.0.0.1"
            @input="result = null"
          />
        </el-form-item>
        <el-form-item label="端口" prop="port">
          <el-input-number
            v-model="form.port"
            :min="1"
            :max="65535"
            :step="1"
            :controls="false"
            @input="result = null"
          />
        </el-form-item>
      </div>
      <el-form-item label="数据库名" prop="database">
        <el-input v-model.trim="form.database" @input="result = null" />
      </el-form-item>
      <el-form-item label="用户名" prop="username">
        <el-input v-model.trim="form.username" @input="result = null" />
      </el-form-item>
      <el-form-item label="密码" prop="password">
        <el-input
          v-model="form.password"
          autocomplete="new-password"
          placeholder="需要密码时重新输入"
          show-password
          @input="result = null"
        />
      </el-form-item>

      <div class="actions">
        <el-button type="primary" native-type="submit" :loading="pendingAction === 'save'">
          保存并连接
        </el-button>
        <el-button :loading="pendingAction === 'test'" @click="submitConnection('test')">
          测试连接
        </el-button>
        <el-button @click="resetForm">重置</el-button>
      </div>
    </el-form>

    <el-alert
      v-if="result"
      class="connection-result"
      :type="result.type"
      :title="result.message"
      :closable="false"
      show-icon
    />
  </el-card>
</template>

<script>
import ElAlert from 'element-ui/lib/alert'
import ElButton from 'element-ui/lib/button'
import ElCard from 'element-ui/lib/card'
import ElForm from 'element-ui/lib/form'
import ElFormItem from 'element-ui/lib/form-item'
import ElInput from 'element-ui/lib/input'
import ElInputNumber from 'element-ui/lib/input-number'
import {
  getDatabaseConnection,
  saveDatabaseConnection,
  testDatabaseConnection,
} from '../api/database.js'

import 'element-ui/lib/theme-chalk/alert.css'
import 'element-ui/lib/theme-chalk/button.css'
import 'element-ui/lib/theme-chalk/card.css'
import 'element-ui/lib/theme-chalk/form.css'
import 'element-ui/lib/theme-chalk/form-item.css'
import 'element-ui/lib/theme-chalk/input.css'
import 'element-ui/lib/theme-chalk/input-number.css'

const defaultSettings = { host: '127.0.0.1', port: 3306, database: '', username: '' }
const rules = {
  host: [{ required: true, whitespace: true, message: '请输入主机地址。', trigger: 'blur' }],
  port: [{
    required: true, type: 'integer', min: 1, max: 65535,
    message: '端口必须是 1 到 65535 之间的整数。', trigger: 'change',
  }],
  database: [{ required: true, whitespace: true, message: '请输入数据库名。', trigger: 'blur' }],
  username: [{ required: true, whitespace: true, message: '请输入用户名。', trigger: 'blur' }],
}

export default {
  name: 'DatabaseConnectionView',
  components: { ElAlert, ElButton, ElCard, ElForm, ElFormItem, ElInput, ElInputNumber },
  data() {
    return {
      form: { ...defaultSettings, password: '' },
      savedSettings: { ...defaultSettings },
      rules,
      loadingSettings: true,
      pendingAction: '',
      result: null,
    }
  },
  async mounted() {
    try {
      this.savedSettings = await getDatabaseConnection()
      this.resetForm()
    } catch (error) {
      this.result = { type: 'warning', message: error.message }
    } finally {
      this.loadingSettings = false
    }
  },
  methods: {
    resetForm() {
      this.form = { ...this.savedSettings, password: '' }
      this.result = null
      this.$nextTick(() => this.$refs.connectionForm?.clearValidate())
    },
    async submitConnection(action) {
      if (this.loadingSettings || this.pendingAction) return

      this.result = null
      this.pendingAction = action
      try {
        const valid = await this.$refs.connectionForm.validate().catch(() => false)
        if (!valid) return

        const { password, ...settings } = this.form
        const submit = action === 'save' ? saveDatabaseConnection : testDatabaseConnection
        const result = await submit({ ...settings, password })
        if (action === 'save') {
          this.savedSettings = settings
          this.form.password = ''
        }
        this.result = { type: 'success', message: result.message }
      } catch (error) {
        this.result = { type: 'error', message: error.message }
      } finally {
        this.pendingAction = ''
      }
    },
  },
}
</script>

<style scoped>
.connection-card {
  max-width: 680px;
  border-color: #dfe7f1;
  border-radius: 10px;
}

.description {
  margin: 0 0 18px;
  color: #52647d;
  font-size: 14px;
}

.address-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(105px, 150px);
  gap: 16px;
}

.address-row .el-input-number {
  width: 100%;
}

.actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.actions .el-button {
  margin-left: 0;
}

.connection-result {
  margin-top: 16px;
}
</style>
