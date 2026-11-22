<template>
  <div class="bar-style-fields">
    <chart-palette-picker :palettes="colorGroups" :active-id="activeGroup" @select="$emit('choose-group', $event)" />

    <details class="bar-style-details">
      <summary>逐柱调整 <span v-if="showLegend">图例</span></summary>
      <div class="bar-style-rows">
        <div v-for="bar in bars" :key="bar.key" class="bar-style-row" :class="{ 'with-legend': showLegend }">
          <div class="bar-color">
            <chart-color-picker :value="bar.color" :label="bar.label + ' 的柱形颜色'"
              @input="update(bar.key, 'color', $event)" />
            <span :title="bar.label">{{ bar.label }}</span>
          </div>
          <input v-if="showLegend" class="bar-legend-label" type="text" maxlength="60" placeholder="图例名称"
            :value="bar.legendLabel" :aria-label="bar.label + ' 的图例名称'"
            title="以下划线开头的名称会隐藏该图例" @input="update(bar.key, 'legendLabel', $event.target.value)">
        </div>
      </div>
    </details>
  </div>
</template>

<script>
import ChartColorPicker from './ChartColorPicker.vue'
import ChartPalettePicker from './ChartPalettePicker.vue'

export default {
  name: 'ChartBarStyleFields',
  components: { ChartColorPicker, ChartPalettePicker },
  props: {
    bars: { type: Array, required: true },
    showLegend: Boolean,
    colorGroups: { type: Array, required: true },
    activeGroup: { type: String, default: '' },
  },
  methods: {
    update(key, field, value) {
      this.$emit('change', key, { [field]: value })
    },
  },
}
</script>

<style scoped>
.bar-style-fields { display: grid; gap: 8px; min-width: 0; }
.bar-style-details { border: 1px solid #dfe7f1; border-radius: 6px; background: #f8faff; }
summary { padding: 7px 8px; color: #263c5a; font-size: 13px; cursor: pointer; }
summary span { float: right; color: #52647d; font-size: 12px; }
.bar-style-rows {
  display: grid;
  gap: 4px;
  max-height: 192px;
  overflow: auto;
  padding: 0 8px 8px;
}
.bar-style-row { display: grid; gap: 6px; align-items: center; min-width: 0; }
.bar-style-row.with-legend { grid-template-columns: minmax(0, 1fr) minmax(0, .9fr); }
.bar-color { display: flex; align-items: center; gap: 5px; min-width: 0; font-size: 13px; }
.bar-color span { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.bar-legend-label {
  min-width: 0;
  width: 100%;
  height: 28px;
  box-sizing: border-box;
  padding: 3px 6px;
  border: 1px solid #cdd9e9;
  border-radius: 5px;
  background: #fff;
  color: #172942;
  font: inherit;
  font-size: 13px;
}
</style>
