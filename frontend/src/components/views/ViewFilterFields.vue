<template>
  <div class="view-fields">
    <label>匹配方式
      <select v-model="spec.match"><option value="all">满足全部条件</option><option value="any">满足任一条件</option></select>
    </label>
    <fieldset v-for="(condition, index) in spec.conditions" :key="index">
      <legend>条件 {{ index + 1 }}</legend>
      <div class="view-pair">
        <label>字段<ViewFieldSelect v-model="condition.field" :fields="fields" /></label>
        <label>条件
          <select v-model="condition.operator">
            <option v-for="(label, op) in operators" :key="op" :value="op">{{ label }}</option>
          </select>
        </label>
      </div>
      <label v-if="needsFilterValue(condition.operator)">比较值
        <input v-model="condition.value" maxlength="512" placeholder="按字段类型填写，如 2024-01-01">
      </label>
      <button type="button" :disabled="spec.conditions.length === 1" @click="spec.conditions.splice(index, 1)">移除此条件</button>
    </fieldset>
    <button type="button" :disabled="spec.conditions.length >= 16" @click="spec.conditions.push(newFilterCondition())">添加筛选条件</button>
  </div>
</template>

<script>
import ViewFieldSelect from './ViewFieldSelect.vue'
import { newFilterCondition, needsFilterValue } from '../../data/viewWorkspace.js'

const operators = {
  eq: '等于', ne: '不等于', gt: '大于', gte: '大于或等于', lt: '小于', lte: '小于或等于',
  contains: '包含文字', isNull: '为空（NULL）', notNull: '不为空',
}

export default {
  name: 'ViewFilterFields',
  components: { ViewFieldSelect },
  props: { spec: { type: Object, required: true }, fields: { type: Array, required: true } },
  data: () => ({ operators }),
  methods: { newFilterCondition, needsFilterValue },
}
</script>
