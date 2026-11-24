<template>
  <select :value="value" :aria-label="label" @change="$emit('input', $event.target.value)">
    <option value="">{{ placeholder }}</option>
    <option v-for="field in fields" :key="field.name" :value="field.name">{{ field.name }} · {{ field.type }}</option>
  </select>
</template>

<script>
export default {
  name: 'ViewFieldSelect',
  props: {
    fields: { type: Array, required: true }, value: { type: String, required: true },
    label: { type: String, default: '' }, placeholder: { type: String, default: '请选择字段' },
  },
}
</script>
