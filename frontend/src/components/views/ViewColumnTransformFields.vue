<template>
  <div class="view-fields">
    <template v-if="unpivot">
      <view-field-checks v-model="spec.keys" :fields="keyFields" label="保留字段（可选）" :limit="64" />
      <div class="view-pair">
        <label>类别列名<input v-model.trim="spec.categoryAlias" maxlength="64"></label>
        <label>数值或内容列名<input v-model.trim="spec.valueAlias" maxlength="64"></label>
      </div>
    </template>
    <fieldset>
      <legend>{{ unpivot ? '要展开的字段与类别值' : '输出字段与新列名' }}</legend>
      <view-field-select v-model="selected" :fields="available" :label="unpivot ? '添加展开字段' : '添加输出字段'"
        :disabled="!available.length || spec.columns.length >= limit" @input="addField" />
      <button v-if="!unpivot && available.length" type="button" :disabled="spec.columns.length >= limit" @click="addAll">保留全部字段</button>
      <div v-for="(column, index) in spec.columns" :key="column.name" class="view-output">
        <span>{{ column.name }}</span>
        <input v-model.trim="column.alias" maxlength="64" :aria-label="column.name + (unpivot ? ' 对应的类别值' : ' 的新列名')">
        <button type="button" :aria-label="'移除 ' + column.name" @click="spec.columns.splice(index, 1)">×</button>
      </div>
    </fieldset>
  </div>
</template>

<script>
import ViewFieldChecks from './ViewFieldChecks.vue'
import ViewFieldSelect from './ViewFieldSelect.vue'
import { uniqueAlias } from '../../data/viewWorkspace.js'

export default {
  name: 'ViewColumnTransformFields',
  components: { ViewFieldChecks, ViewFieldSelect },
  props: { spec: { type: Object, required: true }, fields: { type: Array, required: true } },
  data: () => ({ selected: '' }),
  computed: {
    unpivot() { return this.spec.mode === 'unpivot' },
    limit() { return this.unpivot ? 16 : 64 },
    keyFields() { return this.fields.filter(field => !this.spec.columns.some(item => item.name === field.name)) },
    available() {
      return this.keyFields.filter(field => !this.unpivot || !this.spec.keys.includes(field.name))
    },
  },
  methods: {
    addField(name) {
      if (name && this.spec.columns.length < this.limit) {
        this.spec.columns.push({ name, alias: uniqueAlias(name, this.spec.columns.map(item => item.alias)) })
      }
      this.selected = ''
    },
    addAll() {
      this.available.slice(0, this.limit - this.spec.columns.length).forEach(field => this.addField(field.name))
    },
  },
}
</script>
