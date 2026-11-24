<template>
  <select :value="value" @change="$emit('input', $event.target.value)">
    <option value="">请选择数据源</option>
    <optgroup v-for="group in groups" :key="group.label" :label="group.label">
      <option v-for="source in group.items" :key="source.id" :value="source.id">{{ source.name }}</option>
    </optgroup>
  </select>
</template>

<script>
export default {
  name: 'ViewSourceSelect',
  props: {
    value: { type: String, required: true },
    groups: { type: Array, required: true },
  },
}
</script>
