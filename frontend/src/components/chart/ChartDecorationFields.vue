<template>
  <div class="decoration-fields">
    <details class="decoration-frame">
      <summary>边框与背景</summary>
      <div class="section-fields">
        <label class="field-row">
          外框
          <select :value="value.frameMode" @change="change('frameMode', $event.target.value)">
            <option value="none">无外框</option>
            <option value="axes">仅左轴与底轴</option>
            <option value="plot">绘图区四边</option>
            <option value="canvas">整张图外框</option>
          </select>
        </label>
        <template v-if="value.frameMode !== 'none'">
          <div class="field-row">
            <span>外框颜色</span>
            <chart-color-picker :value="value.frameColor" label="外框颜色" show-code
              @input="change('frameColor', $event)" />
          </div>
          <label class="field-row">
            外框粗细
            <select :value="value.frameWidth" @change="change('frameWidth', Number($event.target.value))">
              <option v-for="width in lineWidths" :key="width" :value="width">{{ width }} 磅</option>
            </select>
          </label>
        </template>
        <label class="check-field">
          <input type="checkbox" :checked="value.showBarOutline"
            @change="change('showBarOutline', $event.target.checked)">
          柱形轮廓
        </label>
        <template v-if="value.showBarOutline">
          <div class="field-row">
            <span>轮廓颜色</span>
            <chart-color-picker :value="value.barOutlineColor" label="柱形轮廓颜色" show-code
              @input="change('barOutlineColor', $event)" />
          </div>
          <label class="field-row">
            轮廓粗细
            <select :value="value.barOutlineWidth" @change="change('barOutlineWidth', Number($event.target.value))">
              <option v-for="width in lineWidths" :key="width" :value="width">{{ width }} 磅</option>
            </select>
          </label>
        </template>
        <label class="check-field">
          <input type="checkbox" :checked="value.transparentBackground"
            @change="change('transparentBackground', $event.target.checked)">
          透明背景
        </label>
        <template v-if="!value.transparentBackground">
          <div class="field-row">
            <span>画布背景</span>
            <chart-color-picker :value="value.figureColor" label="画布背景颜色" show-code
              @input="change('figureColor', $event)" />
          </div>
          <div class="field-row">
            <span>绘图区背景</span>
            <chart-color-picker :value="value.plotColor" label="绘图区背景颜色" show-code
              @input="change('plotColor', $event)" />
          </div>
        </template>
      </div>
    </details>

    <details class="decoration-grid">
      <summary>网格与基线</summary>
      <div class="section-fields">
        <div class="checks">
          <label class="check-field">
            <input type="checkbox" :checked="value.showGrid" @change="change('showGrid', $event.target.checked)">
            横向网格线
          </label>
          <label class="check-field">
            <input type="checkbox" :checked="value.showVerticalGrid"
              @change="change('showVerticalGrid', $event.target.checked)">
            纵向网格线
          </label>
          <label class="check-field">
            <input type="checkbox" :checked="value.showZeroLine" @change="change('showZeroLine', $event.target.checked)">
            零值基线
          </label>
        </div>
        <template v-if="value.showGrid || value.showVerticalGrid">
          <div class="field-row">
            <span>网格颜色</span>
            <chart-color-picker :value="value.gridColor" label="网格线颜色" show-code
              @input="change('gridColor', $event)" />
          </div>
          <label class="field-row">
            网格线型
            <select :value="value.gridStyle" @change="change('gridStyle', $event.target.value)">
              <option value="solid">实线</option>
              <option value="dashed">虚线</option>
              <option value="dotted">点线</option>
            </select>
          </label>
        </template>
      </div>
    </details>

    <details class="decoration-export">
      <summary>画布与导出</summary>
      <div class="section-fields">
        <label class="field-row">
          画布比例
          <select :value="value.chartSize" @change="change('chartSize', $event.target.value)">
            <option value="wide">横版 · 9:5</option>
            <option value="square">方形 · 1:1</option>
            <option value="portrait">竖版 · 3:4</option>
          </select>
        </label>
        <label class="field-row">
          PNG 分辨率
          <select :value="value.dpi" @change="change('dpi', Number($event.target.value))">
            <option :value="130">130 DPI</option>
            <option :value="200">200 DPI</option>
            <option :value="300">300 DPI</option>
          </select>
        </label>
      </div>
    </details>
  </div>
</template>

<script>
import ChartColorPicker from './ChartColorPicker.vue'

export default {
  name: 'ChartDecorationFields',
  components: { ChartColorPicker },
  props: {
    value: { type: Object, required: true },
  },
  data() {
    return { lineWidths: [0.5, 1, 1.5, 2, 3] }
  },
  methods: {
    change(key, value) { this.$emit('change', { [key]: value }) },
  },
}
</script>

<style scoped>
.decoration-fields { display: grid; gap: 8px; min-width: 0; }
details {
  min-width: 0;
  border: 1px solid #dfe7f1;
  border-radius: 6px;
  background: #f8faff;
  color: #263c5a;
  font-size: 13px;
}
summary { padding: 7px 8px; cursor: pointer; }
.section-fields { display: grid; gap: 6px; padding: 0 8px 8px; }
.field-row {
  display: grid;
  grid-template-columns: 76px minmax(0, 1fr);
  gap: 6px;
  align-items: center;
}
select {
  min-width: 0;
  width: 100%;
  min-height: 28px;
  padding: 3px 6px;
  border: 1px solid #cdd9e9;
  border-radius: 5px;
  background: #fff;
  color: #172942;
  font: inherit;
}
.checks { display: flex; flex-wrap: wrap; gap: 6px 10px; }
.check-field { display: flex; align-items: center; gap: 5px; cursor: pointer; }
.check-field input { margin: 0; accent-color: #356fe5; }
</style>
