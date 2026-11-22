<template>
  <details class="layer">
    <summary>{{ title }}</summary>
    <div class="fields">
      <label class="wide">图例名称<input v-model.trim="styleOptions.legendLabel" type="text" maxlength="40"></label>
      <label>主色<chart-color-picker v-model="styleOptions.color" :label="title + '主色'" show-code /></label>
      <label v-if="kind !== 'scatter'">不透明度 {{ Math.round(styleOptions.opacity * 100) }}%
        <input v-model.number="styleOptions.opacity" type="range" min="0.15" max="1" step="0.01">
      </label>
      <template v-if="kind === 'line'">
        <label>线型
          <select v-model="styleOptions.lineStyle">
            <option value="solid">实线</option>
            <option value="dashed">虚线</option>
            <option value="dotted">点线</option>
          </select>
        </label>
        <label>线宽 {{ styleOptions.lineWidth }}
          <input v-model.number="styleOptions.lineWidth" type="range" min="0.5" max="4" step="0.1">
        </label>
        <label class="wide check"><input v-model="styleOptions.markers" type="checkbox"> 显示折线点标记</label>
        <template v-if="styleOptions.markers">
          <label>标记形状
            <select v-model="styleOptions.lineMarker">
              <option value="circle">圆形</option><option value="triangle">三角形</option>
              <option value="square">方形</option><option value="diamond">菱形</option>
            </select>
          </label>
          <label>标记大小 {{ styleOptions.lineMarkerSize }}
            <input v-model.number="styleOptions.lineMarkerSize" type="range" min="2" max="10" step="1">
          </label>
        </template>
      </template>
      <scatter-style-fields v-if="kind === 'scatter'" class="wide" :settings="styleOptions" :guides="guides" />
    </div>
  </details>
</template>

<script>
import ChartColorPicker from './ChartColorPicker.vue'
import ScatterStyleFields from './ScatterStyleFields.vue'

export default {
  name: 'SubplotLayerStyleFields',
  components: { ChartColorPicker, ScatterStyleFields },
  props: {
    title: { type: String, required: true },
    kind: { type: String, required: true },
    styleOptions: { type: Object, required: true },
    guides: Boolean,
  },
}
</script>

<style scoped>
.layer { min-width: 0; border: 1px solid #dfe7f1; border-radius: 6px; background: #fff; }
summary { padding: 8px; cursor: pointer; }
.fields { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; padding: 0 8px 8px; }
.wide { grid-column: 1 / -1; }
label { display: grid; gap: 5px; font-size: 13px; color: #435774; }
.check { display: flex; align-items: center; }
select, input[type='text'] {
  min-width: 0; padding: 6px; border: 1px solid #cdd9e9; border-radius: 5px; background: #fff;
  color: #172942; font: inherit;
}
input[type='range'] { width: 100%; margin: 0; }
</style>
