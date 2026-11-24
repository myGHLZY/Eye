<template>
  <div class="view-fields">
    <div class="view-pair">
      <label>左侧来源<view-source-select :value="spec.left" :groups="groups" @input="changeSource('left', $event)" /></label>
      <label>右侧来源<view-source-select :value="spec.right" :groups="groups" @input="changeSource('right', $event)" /></label>
    </div>
    <label>连接方式
      <select v-model="spec.joinType">
        <option value="inner">内连接（仅匹配的记录）</option>
        <option value="left">左连接（保留左侧所有记录）</option>
      </select>
    </label>

    <fieldset>
      <legend>连接条件</legend>
      <div v-for="(condition, index) in spec.conditions" :key="index" class="view-condition">
        <select v-model="condition.left" :aria-label="'条件 ' + (index + 1) + ' 左侧字段'">
          <option value="">左侧字段</option>
          <option v-for="column in leftColumns" :key="column.name">{{ column.name }}</option>
        </select>
        <span aria-hidden="true">=</span>
        <select v-model="condition.right" :aria-label="'条件 ' + (index + 1) + ' 右侧字段'">
          <option value="">右侧字段</option>
          <option v-for="column in rightColumns" :key="column.name">{{ column.name }}</option>
        </select>
        <button type="button" :disabled="spec.conditions.length === 1" :aria-label="'删除条件 ' + (index + 1)"
          @click="spec.conditions.splice(index, 1)">×</button>
      </div>
      <button type="button" :disabled="spec.conditions.length >= 8"
        @click="spec.conditions.push({ left: '', right: '' })">添加连接条件</button>
    </fieldset>
    <fieldset>
      <legend>输出字段与列名</legend>
      <select v-model="selected" aria-label="添加输出字段" :disabled="!availableColumns.length || spec.columns.length >= 64"
        @change="addColumn">
        <option :value="null">选择要保留的字段</option>
        <option v-for="item in availableColumns" :key="item.side + ':' + item.name" :value="item">
          {{ sideLabels[item.side] }} · {{ item.name }}
        </option>
      </select>
      <div v-for="(item, index) in spec.columns" :key="item.side + ':' + item.name" class="view-output">
        <span>{{ sideLabels[item.side] }} · {{ item.name }}</span>
        <input v-model.trim="item.alias" maxlength="64" :aria-label="item.name + ' 的输出列名'">
        <button type="button" :aria-label="'移除 ' + item.name" @click="spec.columns.splice(index, 1)">×</button>
      </div>
    </fieldset>
  </div>
</template>

<script>
import ViewSourceSelect from './ViewSourceSelect.vue'
import { addJoinOutput, setJoinSource } from '../../data/viewWorkspace.js'

const sideLabels = { left: '左侧', right: '右侧' }

export default {
  name: 'ViewJoinFields',
  components: { ViewSourceSelect },
  props: {
    spec: { type: Object, required: true },
    groups: { type: Array, required: true },
    metadata: { type: Object, required: true },
  },
  data: () => ({ sideLabels, selected: null }),
  computed: {
    leftColumns() { return this.metadata[this.spec.left] || [] },
    rightColumns() { return this.metadata[this.spec.right] || [] },
    availableColumns() {
      return [
        ...this.leftColumns.map(column => ({ side: 'left', name: column.name })),
        ...this.rightColumns.map(column => ({ side: 'right', name: column.name })),
      ].filter(candidate => !this.spec.columns.some(item => item.side === candidate.side && item.name === candidate.name))
    },
  },
  methods: {
    changeSource(side, value) {
      setJoinSource(this.spec, side, value)
      this.$emit('source-selected', value)
    },
    addColumn() {
      if (!this.selected) return
      const { side, name } = this.selected
      addJoinOutput(this.spec, side, name)
      this.selected = null
    },
  },
}
</script>
