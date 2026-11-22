<template>
  <details class="spacing-fields">
    <summary>柱间距与纵轴刻度</summary>
    <div class="spacing-controls">
      <label>
        <span>X 轴柱间距</span>
        <output>{{ barSpacing.toFixed(2) }} 倍</output>
        <input type="range" min="0.7" max="2" step="0.05" :value="barSpacing"
          @input="change('barSpacing', $event.target.valueAsNumber)">
      </label>
      <label>
        <span>Y 轴刻度间距</span>
        <output>{{ yTickBins === null ? '自动' : '约 ' + yTickBins + ' 格' }}</output>
        <input type="range" min="3" max="12" step="1" :value="yTickBins ?? 6"
          @input="change('yTickBins', $event.target.valueAsNumber)">
      </label>
      <button v-if="barSpacing !== 1 || yTickBins !== null" type="button"
        @click="$emit('change', { barSpacing: 1, yTickBins: null })">恢复默认间距</button>
    </div>
  </details>
</template>

<script>
export default {
  name: 'ChartSpacingFields',
  props: {
    barSpacing: { type: Number, required: true },
    yTickBins: { type: Number, default: null },
  },
  methods: {
    change(key, value) { this.$emit('change', { [key]: value }) },
  },
}
</script>

<style scoped>
.spacing-fields {
  min-width: 0;
  border: 1px solid #dfe7f1;
  border-radius: 6px;
  background: #f8faff;
  color: #263c5a;
  font-size: 13px;
}
summary { padding: 7px 8px; cursor: pointer; }
.spacing-controls { display: grid; gap: 8px; padding: 0 8px 8px; }
label {
  display: grid;
  grid-template-columns: 1fr auto;
  align-items: center;
  gap: 3px 7px;
}
output { color: #52647d; font-variant-numeric: tabular-nums; }
input {
  grid-column: 1 / -1;
  width: 100%;
  margin: 0;
  accent-color: #356fe5;
  cursor: pointer;
}
button {
  justify-self: start;
  padding: 0;
  border: 0;
  background: transparent;
  color: #235a9f;
  font: inherit;
  cursor: pointer;
}
</style>
