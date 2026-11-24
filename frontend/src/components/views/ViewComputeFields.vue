<template>
  <div class="view-fields">
    <label>计算配置方式
      <select v-model="spec.inputMode">
        <option value="fields">选择字段与运算符</option><option value="formula">输入公式</option>
      </select>
    </label>
    <template v-if="spec.inputMode === 'formula'">
      <label>公式
        <textarea ref="expression" v-model="spec.expression" rows="3" maxlength="1200"
          spellcheck="false" placeholder="Q1 + Q2 + Q3 + Q4"></textarea>
      </label>
      <label>插入数值字段
        <select :value="''" @change="insertField($event.target)">
          <option value="">在公式光标处插入字段</option>
          <option v-for="field in numericFields" :key="field.name" :value="field.name">{{ field.name }}</option>
        </select>
      </label>
      <p class="view-note">支持加减乘除和括号。字段名含空格或符号时，可以用插入字段自动加上反引号。</p>
    </template>
    <template v-else>
      <fieldset v-for="(item, index) in spec.operands" :key="index">
        <legend>第 {{ index + 1 }} 项</legend>
        <label v-if="index > 0">运算符
          <select v-model="item.operator">
            <option v-for="(operator, key) in operators" :key="key" :value="key">{{ operator.label }}</option>
          </select>
        </label>
        <div class="view-pair">
          <label>取值方式
            <select :value="item.kind" @change="changeKind(item, $event.target.value)">
              <option value="field">数值字段</option><option value="number">固定数值</option>
            </select>
          </label>
          <label v-if="item.kind === 'field'">字段
            <view-field-select v-model="item.value" :fields="numericFields" />
          </label>
          <label v-else>数值<input v-model.trim="item.value" inputmode="decimal" maxlength="64"></label>
        </div>
        <button v-if="spec.operands.length > 2" type="button" @click="spec.operands.splice(index, 1)">移除此项</button>
      </fieldset>
      <button type="button" :disabled="spec.operands.length >= maxComputeOperands"
        @click="spec.operands.push(newComputeOperand())">添加一项</button>
      <p class="view-note">算式预览 {{ expressionPreview }}</p>
    </template>
    <label>新列名<input v-model.trim="spec.alias" maxlength="64" placeholder="例如 年度消费量"></label>
    <p v-if="showDivisionNote" class="view-note">除数为 0 时，该行计算结果为空。</p>
  </div>
</template>

<script>
import ViewFieldSelect from './ViewFieldSelect.vue'
import { maxComputeOperands, newComputeOperand, numericColumn } from '../../data/viewWorkspace.js'

const operators = {
  add: { label: '加（＋）', symbol: '+' },
  subtract: { label: '减（−）', symbol: '−' },
  multiply: { label: '乘（×）', symbol: '×' },
  divide: { label: '除（÷）', symbol: '÷' },
}

export default {
  name: 'ViewComputeFields',
  components: { ViewFieldSelect },
  props: { spec: { type: Object, required: true }, fields: { type: Array, required: true } },
  data: () => ({ operators, maxComputeOperands }),
  computed: {
    numericFields() { return this.fields.filter(numericColumn) },
    expressionPreview() {
      return this.spec.operands.map((item, index) => {
        const value = item.value === '' ? '□' : item.value
        return index ? operators[item.operator].symbol + ' ' + value : value
      }).join(' ')
    },
    showDivisionNote() {
      return this.spec.inputMode === 'formula'
        ? this.spec.expression.includes('/')
        : this.spec.operands.slice(1).some(item => item.operator === 'divide')
    },
  },
  methods: {
    newComputeOperand,
    changeKind(item, kind) {
      item.kind = kind
      item.value = ''
    },
    insertField(select) {
      if (!select.value) return
      const editor = this.$refs.expression
      const name = select.value
      const quote = String.fromCharCode(96)
      const field = quote + name.replaceAll(quote, quote + quote) + quote
      const cursor = editor.selectionStart ?? this.spec.expression.length
      const end = editor.selectionEnd ?? cursor
      this.spec.expression = this.spec.expression.slice(0, cursor) + field + this.spec.expression.slice(end)
      select.value = ''
      this.$nextTick(() => {
        editor.focus()
        editor.setSelectionRange(cursor + field.length, cursor + field.length)
      })
    },
  },
}
</script>