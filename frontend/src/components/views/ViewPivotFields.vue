<template>
  <div class="view-fields">
    <label>长表来源<view-source-select :value="spec.source" :groups="groups" @input="changeSource" /></label>
    <div class="view-pair">
      <label>行字段
        <select v-model="spec.row">
          <option value="">请选择行字段</option>
          <option v-for="column in fields" :key="column.name" :disabled="column.name === spec.category">{{ column.name }}</option>
        </select>
      </label>
      <label>列类别字段
        <select :value="spec.category" @change="changeCategory($event.target.value)">
          <option value="">请选择列类别字段</option>
          <option v-for="column in fields" :key="column.name" :disabled="column.name === spec.row">{{ column.name }}</option>
        </select>
      </label>
    </div>
    <div class="view-pair">
      <label>聚合方式
        <select v-model="spec.aggregation">
          <option value="sum">合计 (SUM)</option><option value="average">平均值 (AVG)</option>
          <option value="max">最大值 (MAX)</option><option value="min">最小值 (MIN)</option>
          <option value="count">记录数 (COUNT)</option>
        </select>
      </label>
      <label v-if="spec.aggregation !== 'count'">数值字段
        <select v-model="spec.metric">
          <option value="">请选择数值字段</option>
          <option v-for="column in numericFields" :key="column.name">{{ column.name }}</option>
        </select>
      </label>
    </div>

    <fieldset>
      <legend>类别值与新列名</legend>
      <div class="view-pair">
        <select v-model="selected" aria-label="添加类别值" @change="addColumn"
          :disabled="!availableValues.length || spec.columns.length >= 16">
          <option :value="null">选择要展开的类别值</option>
          <option v-for="value in availableValues" :key="value" :value="value">{{ value || '空字符串' }}</option>
        </select>
        <button type="button" :disabled="!spec.category || loading" @click="$emit('categories')">
          {{ loading ? '读取中…' : '读取类别值' }}
        </button>
      </div>
      <p v-if="categories?.truncated" class="view-note">显示前 80 个类别值。每次最多生成 16 个类别列。</p>
      <p v-else-if="categories && !categories.values.length" class="view-note">这个字段没有可用的类别值。</p>
      <div v-for="(item, index) in spec.columns" :key="item.value" class="view-output">
        <span>{{ item.value || '空字符串' }}</span>
        <input v-model.trim="item.alias" maxlength="64" :aria-label="(item.value || '空字符串') + ' 的新列名'">
        <button type="button" :aria-label="'移除 ' + (item.value || '空字符串')" @click="spec.columns.splice(index, 1)">×</button>
      </div>
    </fieldset>
  </div>
</template>

<script>
import ViewSourceSelect from './ViewSourceSelect.vue'
import { addPivotValue, numericColumn } from '../../data/viewWorkspace.js'

export default {
  name: 'ViewPivotFields',
  components: { ViewSourceSelect },
  props: {
    spec: { type: Object, required: true },
    groups: { type: Array, required: true },
    metadata: { type: Object, required: true },
    categories: { type: Object, default: null },
    loading: Boolean,
  },
  data: () => ({ selected: null }),
  computed: {
    fields() { return this.metadata[this.spec.source] || [] },
    numericFields() { return this.fields.filter(numericColumn) },
    availableValues() {
      return (this.categories?.values || []).filter(value => !this.spec.columns.some(item => item.value === value))
    },
  },
  methods: {
    changeSource(value) {
      this.spec.source = value
      this.spec.row = this.spec.metric = ''
      this.changeCategory('')
      this.$emit('source-selected', value)
    },
    changeCategory(value) {
      this.spec.category = value
      this.spec.columns = []
      this.selected = null
      this.$emit('reset-categories')
    },
    addColumn() {
      if (this.selected === null) return
      addPivotValue(this.spec, this.selected)
      this.selected = null
    },
  },
}
</script>
