<template>
  <div class="view-fields">
    <label>数值字段<view-field-select v-model="spec.field" :fields="numericFields" /></label>
    <fieldset>
      <legend>分界值（从小到大）</legend>
      <div v-for="(boundary, index) in spec.boundaries" :key="index" class="view-boundary">
        <input v-model.trim="spec.boundaries[index]" inputmode="decimal" maxlength="64" :aria-label="'分界值 ' + (index + 1)">
        <button type="button" :disabled="spec.boundaries.length === 1"
          :aria-label="'移除分界值 ' + (index + 1)" @click="spec.boundaries.splice(index, 1)">×</button>
      </div>
      <button type="button" :disabled="spec.boundaries.length >= 16" @click="spec.boundaries.push('')">添加分界值</button>
      <p class="view-note">例如填写 2 和 5，得到小于 2、包含 2 到小于 5、5 及以上三组。</p>
    </fieldset>
    <label>新列名<input v-model.trim="spec.alias" maxlength="64" placeholder="例如 工时区间"></label>
  </div>
</template>

<script>
import ViewFieldSelect from './ViewFieldSelect.vue'
import { numericColumn } from '../../data/viewWorkspace.js'

export default {
  name: 'ViewBinFields',
  components: { ViewFieldSelect },
  props: { spec: { type: Object, required: true }, fields: { type: Array, required: true } },
  computed: { numericFields() { return this.fields.filter(numericColumn) } },
}
</script>
