<template>
  <el-dialog
    :title="row ? '编辑记录' : '新增记录'"
    :visible="true"
    width="min(600px, calc(100vw - 32px))"
    append-to-body
    :close-on-click-modal="false"
    :before-close="cancel"
  >
    <form @submit.prevent="save">
      <el-alert v-if="error" :title="error" type="error" :closable="false" show-icon />
      <div class="row-fields">
        <div v-for="(field, index) in fields" :key="field.column.name" class="row-field">
          <label :for="'record-field-' + index">
            <span class="field-name">{{ field.column.name }}</span>
            <span class="field-type">{{ field.column.type }}</span>
            <span v-if="!row && field.column.required" class="field-required">必填</span>
          </label>
          <div class="field-controls">
            <el-select
              v-if="field.modes.length > 1"
              v-model="field.mode"
              size="small"
              class="value-mode"
              :disabled="saving"
              :aria-label="field.column.name + ' 的填写方式'"
            >
              <el-option v-for="mode in field.modes" :key="mode" :label="modeLabel(mode, field.column)" :value="mode" />
            </el-select>
            <template v-if="field.mode === 'value'">
              <el-select
                v-if="field.column.kind === 'enum'"
                :id="'record-field-' + index"
                v-model="field.value"
                size="small"
                class="field-input"
                :disabled="saving"
                placeholder="选择字段值"
              >
                <el-option v-for="option in field.column.options" :key="option" :label="option || '空字符串'" :value="option" />
              </el-select>
              <el-input
                v-else
                :id="'record-field-' + index"
                v-model="field.value"
                :type="field.column.kind === 'json' ? 'textarea' : 'text'"
                size="small"
                class="field-input"
                :inputmode="field.column.kind === 'integer' ? 'numeric' : undefined"
                :disabled="saving"
                :placeholder="placeholders[field.column.kind]"
              />
            </template>
          </div>
        </div>
        <p v-if="!fields.length" class="field-type">此表的字段均使用数据库生成的值。</p>
      </div>
      <div class="form-actions">
        <el-button size="small" :disabled="saving" @click="cancel">取消</el-button>
        <el-button
          type="primary"
          native-type="submit"
          size="small"
          :loading="saving"
          :disabled="!!row && !changedValues.length"
        >保存</el-button>
      </div>
    </form>
  </el-dialog>
</template>

<script>
import ElAlert from 'element-ui/lib/alert'
import ElButton from 'element-ui/lib/button'
import ElDialog from 'element-ui/lib/dialog'
import ElInput from 'element-ui/lib/input'
import ElOption from 'element-ui/lib/option'
import ElSelect from 'element-ui/lib/select'

import 'element-ui/lib/theme-chalk/dialog.css'

const placeholders = {
  date: 'YYYY-MM-DD',
  datetime: 'YYYY-MM-DD HH:mm:ss',
  time: 'HH:mm:ss',
  binary: '十六进制，每字节两位',
  json: '输入 JSON 文本',
}

export default {
  name: 'TableRowDialog',
  components: { ElAlert, ElButton, ElDialog, ElInput, ElOption, ElSelect },
  props: {
    columns: { type: Array, required: true },
    row: { type: Object, default: null },
    saving: Boolean,
    error: { type: String, default: '' },
  },
  data() {
    const fields = this.columns.filter(column => this.row ? column.editable : column.insertable).map(column => {
      const original = this.row ? this.row[column.name] : null
      const modes = ['value']
      if (column.nullable) modes.push('null')
      if (!this.row && !column.required) modes.unshift('default')
      const mode = this.row && original === null ? 'null' : modes[0]
      return { column, modes, mode, value: original === null ? '' : String(original), original }
    })
    return { fields, placeholders }
  },
  computed: {
    changedValues() {
      return this.fields.flatMap(({ column, mode, value, original }) => {
        if (mode === 'default') return []
        const next = mode === 'null' ? null : value
        if (this.row && next === (original === null ? null : String(original))) return []
        return [[column.name, next]]
      })
    },
  },
  methods: {
    modeLabel(mode, column) {
      if (mode === 'default') return column.hasDefault ? '使用默认值' : '省略字段'
      return mode === 'null' ? '设为 NULL' : '填写值'
    },
    cancel() {
      if (!this.saving) this.$emit('cancel')
    },
    save() {
      if (!this.saving && (!this.row || this.changedValues.length)) {
        this.$emit('save', Object.fromEntries(this.changedValues))
      }
    },
  },
}
</script>

<style scoped>
.row-fields {
  max-height: 56vh;
  overflow: auto;
  padding: 4px 4px 0 0;
  margin-top: 8px;
}

.row-field {
  margin-bottom: 12px;
}

.row-field label {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: baseline;
  margin-bottom: 5px;
  overflow-wrap: anywhere;
}

.field-name {
  font-weight: 600;
  color: #263f63;
}

.field-type,
.field-required {
  font-size: 12px;
  color: #62758e;
}

.field-required {
  color: #b82f34;
}

.field-controls,
.form-actions {
  display: flex;
  gap: 8px;
}

.value-mode {
  flex: 0 0 130px;
}

.field-input {
  flex: 1;
  min-width: 0;
}

.form-actions {
  justify-content: flex-end;
  margin-top: 12px;
}

.form-actions .el-button + .el-button {
  margin-left: 0;
}
</style>
