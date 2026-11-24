<template>
  <fieldset>
    <legend>{{ label }}</legend>
    <div class="view-check-list">
      <label v-for="field in fields" :key="field.name" class="view-check">
        <input type="checkbox" :checked="value.includes(field.name)"
          :disabled="!value.includes(field.name) && value.length >= limit"
          @change="toggle(field.name, $event.target.checked)">{{ field.name }}
      </label>
    </div>
  </fieldset>
</template>

<script>
export default {
  name: 'ViewFieldChecks',
  props: {
    fields: { type: Array, required: true }, value: { type: Array, required: true },
    label: { type: String, required: true }, limit: { type: Number, default: 16 },
  },
  methods: {
    toggle(name, checked) {
      this.$emit('input', checked ? [...this.value, name] : this.value.filter(item => item !== name))
    },
  },
}
</script>
