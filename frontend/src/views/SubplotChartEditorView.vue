<template>
  <section>
    <router-link class="back-link" :to="{ name: 'chart-workbench', params: { chartId: $route.params.chartId } }">
      ‹ 返回图表工作台
    </router-link>
    <div class="editor-layout">
      <chart-editor-controls>
        <template #data>
          <div class="toolbar">
            <button type="button" :disabled="panels.length >= maxPanels" @click="addPanel()">＋ 添加子图</button>
            <button type="button" :disabled="panels.length >= maxPanels" @click="addPanel('overlay')">＋ 添加重合子图</button>
            <span>{{ panels.length }} / {{ maxPanels }}</span>
          </div>
          <details v-for="(panel, index) in panels" :key="panel.id" :open="panel.id === openPanel">
            <summary>({{ letter(index) }}) {{ panel.title || kinds[panel.kind] }}</summary>
            <div class="controls">
              <label>图形
                <select :value="panel.kind" @change="changeKind(panel, $event.target.value)">
                  <option v-for="(label, kind) in kinds" :key="kind" :value="kind">{{ label }}</option>
                </select>
              </label>
              <template v-if="panel.kind === 'overlay'">
                <p class="field-help">分别配置两张子图。请选择同类型的横轴字段，绘图时按横轴值对齐。</p>
                <details v-for="(layer, layerIndex) in panel.layers" :key="layerIndex" :open="layerIndex === 0">
                  <summary>
                    子图 {{ layerNames[layerIndex] }} · {{ layerKinds[layer.kind] }}
                    <span class="data-status">{{ layer.selection ? '已配置' : '待选择数据' }}</span>
                  </summary>
                  <div class="controls">
                    <label>图形
                      <select :value="layer.kind" @change="changeKind(layer, $event.target.value)">
                        <option v-for="(label, kind) in layerKinds" :key="kind" :value="kind">{{ label }}</option>
                      </select>
                    </label>
                    <subplot-data-fields :entry="layer" overlay />
                  </div>
                </details>
              </template>
              <subplot-data-fields v-else :key="panel.kind" :entry="panel" />
              <label v-if="canUseRightAxis(panel)" class="check">
                <input v-model="panel.rightAxis" type="checkbox">
                {{ panel.kind === 'overlay' ? '子图 B' : '折线' }}使用右纵轴
              </label>
              <div class="toolbar">
                <button type="button" :disabled="index === 0" @click="move(index, -1)">上移</button>
                <button type="button" :disabled="index === panels.length - 1" @click="move(index, 1)">下移</button>
                <button type="button" :disabled="panels.length === 1" @click="panels.splice(index, 1)">移除</button>
              </div>
            </div>
          </details>
        </template>
        <template #style>
          <label>总图标题<input v-model.trim="style.title" type="text" maxlength="60"></label>
          <label>底部题注<input v-model.trim="style.caption" type="text" maxlength="120"></label>
          <label>每行子图数
            <select v-model.number="style.columns">
              <option :value="1">1 列</option><option :value="2">2 列</option><option :value="3">3 列</option>
            </select>
          </label>
          <label>PNG 分辨率
            <select v-model.number="style.dpi">
              <option :value="130">130 DPI</option><option :value="200">200 DPI</option><option :value="300">300 DPI</option>
            </select>
          </label>
          <label class="check"><input v-model="style.showLegend" type="checkbox"> 默认显示图例</label>
          <details v-for="(panel, index) in panels" :key="panel.id">
            <summary>设置子图 ({{ letter(index) }})</summary>
            <div class="controls">
              <label>子图标题<input v-model.trim="panel.title" type="text" maxlength="60"></label>
              <label>横轴名称<input v-model.trim="panel.xLabel" type="text" maxlength="60"></label>
              <label>{{ panel.rightAxis && canUseRightAxis(panel) ? '左纵轴' : '纵轴' }}名称
                <input v-model.trim="panel.yLabel" type="text" maxlength="60">
              </label>
              <label v-if="panel.rightAxis && canUseRightAxis(panel)">右纵轴名称
                <input v-model.trim="panel.rightLabel" type="text" maxlength="60">
              </label>
              <div class="style-row">
                <label>背景色
                  <chart-color-picker v-model="panel.style.backgroundColor" label="子图背景色" show-code />
                </label>
                <label>图例
                  <select v-model="panel.style.legend">
                    <option value="inherit">随总图设置</option><option value="none">隐藏</option>
                    <option value="auto">自动</option><option value="top-left">左上</option>
                    <option value="top-right">右上</option><option value="bottom">底部居中</option>
                  </select>
                </label>
              </div>
              <label class="check"><input v-model="panel.style.legendFrame" type="checkbox"> 显示图例边框</label>
              <div class="style-row">
                <label>网格
                  <select v-model="panel.style.grid">
                    <option value="both">横线和竖线</option><option value="y">横线</option>
                    <option value="x">竖线</option><option value="none">无</option>
                  </select>
                </label>
                <label>边框
                  <select v-model="panel.style.frame">
                    <option value="box">完整边框</option><option value="axes">仅轴线</option>
                    <option value="none">无</option>
                  </select>
                </label>
              </div>
              <label>横轴刻度文字
                <select v-model="panel.style.tickRotation">
                  <option :value="null">自动</option><option :value="0">水平</option>
                  <option :value="25">旋转 25°</option><option :value="45">旋转 45°</option>
                </select>
              </label>
              <div class="style-row">
                <label>纵轴下限<input :value="panel.style.yMin" type="number" step="any" placeholder="自动"
                  @input="setLimit(panel, 'yMin', $event.target)"></label>
                <label>纵轴上限<input :value="panel.style.yMax" type="number" step="any" placeholder="自动"
                  @input="setLimit(panel, 'yMax', $event.target)"></label>
              </div>
              <div v-if="panel.rightAxis && canUseRightAxis(panel)" class="style-row">
                <label>右纵轴下限<input :value="panel.style.rightYMin" type="number" step="any" placeholder="自动"
                  @input="setLimit(panel, 'rightYMin', $event.target)"></label>
                <label>右纵轴上限<input :value="panel.style.rightYMax" type="number" step="any" placeholder="自动"
                  @input="setLimit(panel, 'rightYMax', $event.target)"></label>
              </div>
              <template v-if="panel.kind === 'overlay'">
                <div v-for="(layer, layerIndex) in panel.layers" :key="layerIndex" class="series-styles">
                  <subplot-layer-style-fields :style-options="layer.style" :kind="layer.kind" guides
                    :title="'子图 ' + layerNames[layerIndex] + (isMultiSeries(layer) ? ' · 系列 1' : ' · ' + layerKinds[layer.kind])" />
                  <subplot-layer-style-fields v-if="isMultiSeries(layer)" :style-options="layer.secondSeriesStyle"
                    :kind="layer.kind" :title="'子图 ' + layerNames[layerIndex] + ' · 系列 2'" />
                </div>
              </template>
              <template v-else>
                <subplot-layer-style-fields :style-options="panel.primaryStyle" guides
                  :kind="panel.kind === 'bar_line' ? 'bar' : panel.kind"
                  :title="panel.kind === 'bar_line' ? '柱状图样式' : '图形样式'" />
                <subplot-layer-style-fields v-if="panel.kind === 'bar_line'" :style-options="panel.secondaryStyle"
                  kind="line" title="折线图样式" />
              </template>
            </div>
          </details>
        </template>
      </chart-editor-controls>

      <chart-preview class="panel" :busy="rendering" :url="imageUrl" :title="style.title || '多子图组合'"
        :error="error" empty-message="设置各子图的数据来源，再生成组合图。" filename="subplot-chart.png">
        <div class="preview-actions">
          <button type="button" class="primary" :disabled="!ready || rendering" @click="renderChart">生成组合图</button>
          <span v-if="imageUrl && generated !== signature">配置已修改，可重新生成。</span>
        </div>
      </chart-preview>
    </div>
  </section>
</template>

<script>
import ChartColorPicker from '../components/chart/ChartColorPicker.vue'
import { renderChartImage } from '../api/chart.js'
import SubplotDataFields from '../components/chart/SubplotDataFields.vue'
import ChartEditorControls from '../components/chart/ChartEditorControls.vue'
import ChartPreview from '../components/chart/ChartPreview.vue'
import SubplotLayerStyleFields from '../components/chart/SubplotLayerStyleFields.vue'
import { createPanel, isMultiSeries, kinds, layerKinds, subplotPayload } from '../data/subplotConfig.js'

const maxPanels = 6
const layerNames = ['A', 'B']

export default {
  name: 'SubplotChartEditorView',
  components: { ChartColorPicker, ChartEditorControls, ChartPreview, SubplotDataFields, SubplotLayerStyleFields },
  data() {
    const initialKind = this.$route.params.chartId === 'subplot_overlay' ? 'overlay' : 'bar'
    return {
      panels: [createPanel(1, initialKind)], initialKind, nextId: 2, openPanel: 1,
      kinds, layerKinds, layerNames, maxPanels,
      style: { title: '', caption: '', columns: 2, dpi: 130, showLegend: true },
      error: '', rendering: false, imageUrl: '', generated: '',
    }
  },
  computed: {
    ready() {
      return this.panels.every(panel => panel.kind === 'overlay'
        ? panel.layers.every(layer => layer.selection)
        : panel.selection)
    },
    requestPayload() {
      return subplotPayload(this.panels, this.style)
    },
    signature() {
      return JSON.stringify(this.requestPayload)
    },
  },
  beforeDestroy() {
    this._request?.abort()
    this._request = null
    if (this.imageUrl) URL.revokeObjectURL(this.imageUrl)
  },
  methods: {
    letter(index) {
      return 'abcdef'[index]
    },
    addPanel(kind = this.initialKind) {
      // 展开新子图以便选择数据。
      if (this.panels.length >= maxPanels) return
      const panel = createPanel(this.nextId++, kind)
      this.panels.push(panel)
      this.openPanel = panel.id
    },
    changeKind(entry, kind) {
      entry.kind = kind
      entry.selection = null
    },
    canUseRightAxis(panel) {
      return panel.kind === 'overlay' || panel.kind === 'bar_line'
    },
    isMultiSeries,
    setLimit(panel, key, input) {
      panel.style[key] = Number.isFinite(input.valueAsNumber) ? input.valueAsNumber : null
    },
    move(index, offset) {
      const [panel] = this.panels.splice(index, 1)
      this.panels.splice(index + offset, 0, panel)
    },
    async renderChart() {
      // 让预览与生成请求提交的配置保持一致。
      if (!this.ready || this.rendering) return
      const request = new AbortController()
      const signature = this.signature
      this._request = request
      this.rendering = true
      this.error = ''
      try {
        const image = await renderChartImage('subplot', this.requestPayload, request.signal)
        if (this._request !== request) return
        if (this.imageUrl) URL.revokeObjectURL(this.imageUrl)
        this.imageUrl = URL.createObjectURL(image)
        this.generated = signature
      } catch (error) {
        if (this._request === request) this.error = error.message
      } finally {
        if (this._request === request) this.rendering = false
      }
    },
  },
}
</script>

<style scoped>
.back-link { display: inline-block; margin: 2px 0 14px; color: #235a9f; text-decoration: none; }
.editor-layout { display: grid; grid-template-columns: minmax(250px, 330px) minmax(0, 1fr); gap: 16px; }
.panel { padding: 16px; border: 1px solid #dfe7f1; border-radius: 10px; background: #fff; }
.toolbar, .preview-actions { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.toolbar span, .preview-actions span { color: #52647d; font-size: 13px; }
.preview-actions { margin-top: 12px; }
details { min-width: 0; border: 1px solid #dfe7f1; border-radius: 6px; background: #f8faff; }
summary { padding: 8px; cursor: pointer; }
.controls { display: grid; gap: 9px; padding: 0 10px 10px; }
.series-styles { display: grid; gap: 7px; }
.style-row { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; }
.field-help { margin: 0; color: #52647d; font-size: 13px; }
.data-status { color: #52647d; font-size: 12px; margin-left: 4px; }
label { display: grid; gap: 5px; font-size: 13px; color: #435774; }
label.check { display: flex; align-items: center; }
select, input[type='number'], input[type='text'], button {
  min-width: 0; padding: 6px; border: 1px solid #cdd9e9; border-radius: 5px; background: #fff;
  color: #172942; font: inherit;
}
button { cursor: pointer; color: #235a9f; }
button:disabled { cursor: default; color: #64748b; background: #eff3f8; }
button.primary:not(:disabled) { background: #235a9f; color: #fff; border-color: #235a9f; }
@media (max-width: 960px) { .editor-layout { grid-template-columns: minmax(0, 1fr); } }
</style>
