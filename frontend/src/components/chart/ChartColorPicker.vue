<template>
  <span class="color-picker">
    <input type="color" :value="value" :aria-label="label" :title="value.toUpperCase()"
      @input="$emit('input', $event.target.value)">
    <span v-if="showCode" class="color-code">{{ value.toUpperCase() }}</span>
  </span>
</template>

<script>
export default {
  name: 'ChartColorPicker',
  props: {
    value: { type: String, required: true },
    label: { type: String, required: true },
    showCode: Boolean,
  },
}
</script>

<style scoped>
.color-picker { display: inline-flex; align-items: center; gap: 7px; }
input {
  box-sizing: border-box;
  width: 28px;
  height: 28px;
  padding: 3px;
  border: 1px solid #cdd9e9;
  border-radius: 5px;
  background: #fff;
  cursor: pointer;
}
input::-webkit-color-swatch-wrapper { padding: 0; }
input::-webkit-color-swatch { border: 0; border-radius: 3px; }
input::-moz-color-swatch { border: 0; border-radius: 3px; }
.color-code { color: #52647d; font: 12px monospace; }
</style>
