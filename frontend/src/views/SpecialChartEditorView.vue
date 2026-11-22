<template>
  <section>
    <router-link class="back-link" :to="{ name: 'chart-workbench', params: $route.params }">‹ 返回图表工作台</router-link>
    <div class="editor-layout">
      <chart-editor-controls>
        <template #data>
          <label v-if="kind === 'heatmap'" class="field">表结构
            <select v-model="heatmapLayout">
              <option value="long">长表（从字段值生成列）</option>
              <option value="wide">宽表（多个数值列）</option>
            </select>
          </label>
          <chart-data-picker v-model="selection" :aggregations="aggregations"
            :category-label="config.categoryLabel" :group-label="config.groupLabel"
            :group-mode="wideHeatmap ? 'none' : config.groupMode" :wide-metrics="wideHeatmap"
            :value-label="kind === 'scatter' ? '纵轴数值' : '数值字段'" :raw-points="kind === 'scatter'" />
          <button v-if="selection" type="button" :disabled="loading" @click="loadData">刷新数据</button>
        </template>
        <template #style>
          <chart-palette-picker v-if="kind !== 'heatmap'" :palettes="palettes" :active-id="paletteId"
            @select="paletteId = $event.id" />
          <label class="field">图表标题
            <input v-model="title" type="text" maxlength="60" :placeholder="automaticTitle">
          </label>
          <label v-if="isRadar" class="check"><input v-model="fill" type="checkbox"> 填充轮廓</label>
          <template v-if="kind === 'sankey'">
            <label class="field">流带不透明度
              <input v-model.number="flowOpacity" type="range" min="0.15" max="0.85" step="0.05">
            </label>
            <label class="check"><input v-model="showFlowValues" type="checkbox"> 在流带上显示流量</label>
          </template>
          <label v-if="kind === 'line'" class="check"><input v-model="showMarkers" type="checkbox"> 显示数据点</label>
          <template v-if="kind === 'scatter'">
            <label class="field">横轴名称<input v-model.trim="scatterXLabel" type="text" maxlength="60" :placeholder="dataset?.xLabel"></label>
            <label class="field">纵轴名称<input v-model.trim="scatterYLabel" type="text" maxlength="60" :placeholder="dataset?.yLabel"></label>
            <label class="check"><input v-model="scatterShowGrid" type="checkbox"> 显示网格</label>
            <label class="check"><input v-model="scatterShowLegend" type="checkbox"> 显示图例</label>
            <scatter-style-fields :settings="scatter" guides />
          </template>
          <template v-if="kind === 'heatmap'">
            <label class="field">热力配色
              <select v-model="colorMap">
                <option value="Blues">蓝色</option><option value="YlOrRd">黄红色</option>
                <option value="viridis">紫绿渐变</option><option value="coolwarm">冷暖对比</option>
              </select>
            </label>
            <label class="check"><input v-model="showValues" type="checkbox"> 显示单元格数值</label>
          </template>
        </template>
      </chart-editor-controls>
      <div class="preview-stack">
        <chart-preview class="panel" :url="imageUrl" :title="title || automaticTitle"
          :busy="loading || rendering" :error="dataError || previewError" :empty-message="emptyMessage"
          :filename="kind + '-chart.png'">
          <p v-if="dataset?.truncated" class="note">已达到预览上限，按当前顺序展示部分数据。</p>
        </chart-preview>
        <section v-if="rows.length" class="panel">
          <h2>{{ config.dataHeading }}</h2>
          <div class="table-scroll">
            <table>
              <thead><tr>
                <th v-for="(heading, index) in headings" :key="index" scope="col">{{ heading }}</th>
              </tr></thead>
              <tbody>
                <tr v-for="(row, index) in rows" :key="index">
                  <th scope="row">{{ row[0] }}</th>
                  <td v-for="(cell, column) in row.slice(1)" :key="column">{{ cell }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </div>
  </section>
</template>

<script>
import { fetchChartData, renderChartImage } from '../api/chart.js'
import ChartEditorControls from '../components/chart/ChartEditorControls.vue'
import ChartDataPicker from '../components/chart/ChartDataPicker.vue'
import ChartPalettePicker from '../components/chart/ChartPalettePicker.vue'
import ChartPreview from '../components/chart/ChartPreview.vue'
import ScatterStyleFields from '../components/chart/ScatterStyleFields.vue'
import { chartPalettes } from '../data/chartPalettes.js'
import { createScatterStyle } from '../data/scatterStyle.js'

const format = new Intl.NumberFormat('zh-CN', { maximumSignificantDigits: 8 })
const baseAggregations = ['sum', 'average', 'count', 'max', 'min']
const wideAggregations = ['raw', 'sum', 'average', 'max', 'min']
const chartEditors = {
  radar_chart: { kind: 'radar', title: '雷达图', categoryLabel: '指标字段', groupLabel: '系列字段', groupMode: 'optional', dataHeading: '指标数据' },
  sankey_basics: { kind: 'sankey', title: '桑基图', categoryLabel: '来源字段', groupLabel: '目标字段', groupMode: 'required', dataHeading: '流量数据' },
  simple_plot: { kind: 'line', title: '折线图', categoryLabel: '横轴字段', groupLabel: '系列字段', groupMode: 'optional', dataHeading: '折线数据' },
  scatter_with_legend: { kind: 'scatter', title: '散点图', categoryLabel: '横轴字段', groupLabel: '分组字段（可选）', groupMode: 'optional', dataHeading: '散点数据' },
  specialty_heatmap: { kind: 'heatmap', title: '热力图', categoryLabel: '行字段', groupLabel: '列字段', groupMode: 'required', dataHeading: '矩阵数据' },
}

export default {
  name: 'SpecialChartEditorView',
  components: { ChartDataPicker, ChartEditorControls, ChartPalettePicker, ChartPreview, ScatterStyleFields },
  data() {
    return {
      selection: null, dataset: null, palettes: chartPalettes, paletteId: 'classic',
      title: '', fill: true, flowOpacity: 0.4, loading: false, rendering: false, imageUrl: '',
      showFlowValues: false,
      heatmapLayout: 'long',
      showMarkers: true, colorMap: 'Blues', showValues: true,
      scatter: createScatterStyle(), scatterXLabel: '', scatterYLabel: '',
      scatterShowGrid: true, scatterShowLegend: true,
      dataError: '', previewError: '',
    }
  },
  computed: {
    config() { return chartEditors[this.$route.params.chartId] },
    kind() { return this.config.kind },
    isRadar() { return this.kind === 'radar' },
    wideHeatmap() { return this.kind === 'heatmap' && this.heatmapLayout === 'wide' },
    aggregations() {
      if (this.wideHeatmap) return wideAggregations
      return ['line', 'heatmap'].includes(this.kind) ? baseAggregations : ['sum', 'count']
    },
    automaticTitle() {
      if (!this.dataset || !this.selection) return this.config.title
      if (this.kind === 'scatter') return `${this.selection.categoryColumn} · ${this.selection.valueColumn}`
      if (this.selection.layout === 'wide') return `${this.selection.table} · ${this.selection.categoryColumn} · ${this.dataset.seriesName}`
      const { categoryColumn, groupColumn } = this.selection
      return groupColumn ? `${categoryColumn} · ${groupColumn} · ${this.dataset.seriesName}` : `${categoryColumn} · ${this.dataset.seriesName}`
    },
    series() { return this.dataset?.series || [] },
    groupedScatter() { return Boolean(this.selection?.groupColumn) },
    headings() {
      if (this.kind === 'sankey') return ['来源', '目标', '流量']
      if (this.kind === 'scatter') return [
        ...(this.groupedScatter ? ['分组'] : []), this.dataset?.xLabel, this.dataset?.yLabel,
      ]
      if (this.kind === 'heatmap') return ['行 / 列', ...(this.dataset?.columns || [])]
      return [this.isRadar ? '指标' : '横轴', ...(this.series.length ? this.series.map(item => item.label) : ['数值'])]
    },
    rows() {
      if (!this.dataset) return []
      if (this.kind === 'sankey') return this.dataset.flows.map(flow => [flow.source, flow.target, format.format(flow.value)])
      if (this.kind === 'scatter') {
        const labels = new Map((this.dataset.points || []).map(point => [point.x, point.label]))
        return this.series.flatMap(group => group.samples.map(([x, y]) => [
          ...(this.groupedScatter ? [group.label] : []), labels.get(x) ?? format.format(x), format.format(y),
        ]))
      }
      if (this.kind === 'heatmap') return this.dataset.rows.map((row, index) => [
        row, ...this.dataset.values[index].map(value => value == null ? '—' : format.format(value)),
      ])
      return this.dataset.points.map((point, index) => [
        point.label,
        ...(this.series.length
          ? this.series.map(item => item.values[index] == null ? '—' : format.format(item.values[index]))
          : [format.format(point.value)]),
      ])
    },
    renderPayload() {
      if (!this.dataset || (!this.isRadar && !this.rows.length) || (this.isRadar && this.rows.length < 3)) return null
      const palette = this.palettes.find(item => item.id === this.paletteId)
      return {
        ...this.dataset,
        style: {
          colors: palette.colors, title: this.title || this.automaticTitle.slice(0, 60),
          legendLabel: this.dataset.seriesName, fill: this.fill, flowOpacity: this.flowOpacity,
          ...(this.kind === 'sankey' ? { showFlowValues: this.showFlowValues } : {}),
          showMarkers: this.showMarkers, colorMap: this.colorMap, showValues: this.showValues,
          xLabel: (this.selection.layout === 'wide' ? '数值列'
            : this.kind === 'heatmap' ? this.selection.groupColumn : this.selection.categoryColumn).slice(0, 60),
          yLabel: (this.kind === 'heatmap' ? this.selection.categoryColumn
            : this.kind === 'scatter' ? this.selection.valueColumn : this.dataset.seriesName).slice(0, 60),
          ...(this.kind === 'scatter' ? {
            ...this.scatter,
            showGrid: this.scatterShowGrid, showLegend: this.scatterShowLegend,
            xLabel: this.scatterXLabel || this.selection.categoryColumn.slice(0, 60),
            yLabel: this.scatterYLabel || this.selection.valueColumn.slice(0, 60),
          } : {}),
        },
      }
    },
    emptyMessage() {
      if (!this.dataset) return '选择数据库、表和字段以生成图表。'
      if (this.isRadar) return '雷达图至少需要三个指标分类。'
      return this.kind === 'sankey' ? '当前数据没有可绘制的正流量。' : '当前字段组合没有可绘制的数据。'
    },
  },
  watch: {
    selection() {
      this._dataRequest?.abort()
      this._dataRequest = null
      this.dataset = null
      this.loading = false
      this.dataError = ''
      this.clearImage()
      this.loadData()
    },
    renderPayload() {
      clearTimeout(this._renderTimer)
      this._renderRequest?.abort()
      this._renderRequest = null
      this.previewError = ''
      this.rendering = Boolean(this.renderPayload)
      if (this.rendering) this._renderTimer = setTimeout(() => this.updatePreview(), 230)
      else this.clearImage()
    },
  },
  beforeDestroy() {
    this._dataRequest?.abort()
    this._renderRequest?.abort()
    this._dataRequest = this._renderRequest = null
    clearTimeout(this._renderTimer)
    this.clearImage()
  },
  methods: {
    async loadData() {
      // Keep only the latest selection's result.
      if (!this.selection) return
      this._dataRequest?.abort()
      const request = new AbortController()
      this._dataRequest = request
      this.loading = true
      this.dataError = ''
      try {
        const dataset = await fetchChartData(this.kind, this.selection, request.signal)
        if (this._dataRequest === request) this.dataset = dataset
      } catch (error) {
        if (this._dataRequest === request && error.name !== 'AbortError') this.dataError = error.message
      } finally {
        if (this._dataRequest === request) this.loading = false
      }
    },
    async updatePreview() {
      // Render style changes without re-querying the database.
      const request = new AbortController()
      this._renderRequest = request
      try {
        const image = await renderChartImage(this.kind, this.renderPayload, request.signal)
        if (this._renderRequest === request) {
          this.clearImage()
          this.imageUrl = URL.createObjectURL(image)
        }
      } catch (error) {
        if (this._renderRequest === request && error.name !== 'AbortError') this.previewError = error.message
      } finally {
        if (this._renderRequest === request) this.rendering = false
      }
    },
    clearImage() {
      if (this.imageUrl) URL.revokeObjectURL(this.imageUrl)
      this.imageUrl = ''
    },
  },
}
</script>

<style scoped>
.back-link { display: inline-block; margin: 2px 0 14px; color: #235a9f; text-decoration: none; }
.editor-layout { display: grid; grid-template-columns: minmax(230px, 295px) minmax(0, 1fr); gap: 16px; }
.preview-stack { display: grid; align-content: start; gap: 12px; min-width: 0; }
.panel { min-width: 0; padding: 14px; border: 1px solid #dfe7f1; border-radius: 10px; background: #fff; }
h2 { margin: 0 0 4px; color: #15243b; font-size: 16px; }
.field { display: grid; grid-template-columns: 76px minmax(0, 1fr); align-items: center; gap: 7px; color: #435774; font-size: 13px; }
input[type='text'], select, button { min-width: 0; padding: 6px; border: 1px solid #cdd9e9; border-radius: 5px; background: #fff; font: inherit; }
input[type='range'] { width: 100%; }
.check { display: flex; gap: 5px; align-items: center; color: #435774; font-size: 13px; }
button { justify-self: start; color: #235a9f; cursor: pointer; }
.note { margin: 8px 0 0; color: #52647d; font-size: 13px; }
.table-scroll { max-height: 250px; overflow: auto; }
table { width: 100%; border-spacing: 0; text-align: left; color: #263c5a; font-size: 13px; }
th, td { padding: 6px 8px; border-bottom: 1px solid #e5edf6; overflow-wrap: anywhere; }
thead th { position: sticky; top: 0; background: #f3f7fc; }
tbody th { font-weight: 400; }
@media (max-width: 960px) { .editor-layout { grid-template-columns: minmax(0, 1fr); } }
</style>
