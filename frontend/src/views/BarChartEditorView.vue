<template>
  <section class="bar-chart-editor">
    <router-link class="back-link" :to="{ name: 'chart-workbench', params: { chartId: $route.params.chartId } }">
      <i class="el-icon-arrow-left" aria-hidden="true"></i> 返回图表工作台
    </router-link>

    <div class="editor-layout">
      <chart-editor-controls>
        <template #data>
          <label class="chart-layout-field">图形布局
            <select v-model="layout">
              <option value="single">普通柱状图</option>
              <option value="grouped">分组柱状图</option>
              <option value="stacked">堆叠柱状图</option>
            </select>
          </label>
          <chart-data-picker v-model="selection" :group-mode="layout === 'single' ? 'none' : 'required'" />
          <p v-if="layout === 'stacked' && ['average', 'max', 'min'].includes(selection?.aggregation)" class="preview-note">
            每一段先按系列计算，整根柱高为各段之和。
          </p>
          <div v-if="selection" class="refresh-options">
            <label><input v-model="autoRefresh" type="checkbox"> 每 5 秒检查数据变化</label>
            <button class="text-button" type="button" :disabled="loadingData" @click="loadData">刷新数据</button>
          </div>
        </template>

        <template #style>
          <div class="style-colors">
            <fieldset v-if="layout === 'single'" class="color-modes">
              <legend class="sr-only">配色模式</legend>
              <label :class="{ selected: perBar }">
                <input v-model="perBar" class="sr-only" name="bar-color-mode" type="radio" :value="true">
                逐柱配色
              </label>
              <label :class="{ selected: !perBar }">
                <input v-model="perBar" class="sr-only" name="bar-color-mode" type="radio" :value="false">
                统一配色
              </label>
            </fieldset>
            <template v-if="perBar || layout !== 'single'">
              <chart-bar-style-fields v-if="bars.length" :bars="bars" :show-legend="style.showLegend"
                :color-groups="colorGroups" :active-group="activeColorGroup" :is-series="layout !== 'single'"
                @change="updateBarStyle" @choose-group="applyColorGroup" />
              <p v-else class="style-empty">选择数据后可逐柱配色。</p>
            </template>
            <div v-else class="uniform-color">
              <span>柱形颜色</span>
              <chart-color-picker :value="style.color" label="统一柱形颜色" show-code
                @input="updateStyle({ color: $event })" />
            </div>
            <label v-if="layout === 'single'" class="gradient-option">
              <input v-model="style.gradient" type="checkbox"> 柱形渐变
            </label>
          </div>
          <chart-appearance-fields :value="style" :per-bar="perBar || layout !== 'single'" :automatic-title="automaticTitle"
            :automatic-legend="seriesName" :automatic-x-label="automaticXLabel" :automatic-y-label="seriesName"
            @change="updateStyle" />
          <chart-spacing-fields :bar-spacing="style.barSpacing" :y-tick-bins="style.yTickBins"
            @change="updateStyle" />
          <chart-decoration-fields :value="style" @change="updateStyle" />
        </template>
      </chart-editor-controls>

      <div class="preview-stack">
        <chart-preview class="panel" :url="imageUrl" :title="style.title || automaticTitle"
          :busy="loadingData || rendering" :error="dataError || renderError" :empty-message="emptyMessage"
          filename="bar-chart.png">
          <p v-if="dataset?.truncated" class="preview-note">
            共展示数值最高的 {{ dataset.points.length }} 个分类。
            <span v-if="dataset.valueUnit === '%'">占比按全部分类的总和计算。</span>
          </p>
          <button v-if="points.length" type="button" class="convert-button" :disabled="!canConvert"
            :title="canConvert ? '使用当前图表数据生成饼图' : '饼图需要非负数值且总和大于零'"
            @click="convertToPie">转为饼图</button>
          <p v-if="points.length && !canConvert" class="preview-note">负值或全为零的数据无法转换为饼图。</p>
        </chart-preview>
        <chart-statistics-fields v-if="layout === 'single'" :bars="statisticsBars" :scope="statisticsScope"
          :is-average="selection?.aggregation === 'average'" :value-unit="dataset?.valueUnit || ''"
          @change="updateAnnotations" />
      </div>
    </div>
  </section>
</template>

<script>
import ChartAppearanceFields from '../components/chart/ChartAppearanceFields.vue'
import ChartBarStyleFields from '../components/chart/ChartBarStyleFields.vue'
import ChartColorPicker from '../components/chart/ChartColorPicker.vue'
import ChartEditorControls from '../components/chart/ChartEditorControls.vue'
import ChartDataPicker from '../components/chart/ChartDataPicker.vue'
import ChartDecorationFields from '../components/chart/ChartDecorationFields.vue'
import ChartPreview from '../components/chart/ChartPreview.vue'
import ChartSpacingFields from '../components/chart/ChartSpacingFields.vue'
import ChartStatisticsFields from '../components/chart/ChartStatisticsFields.vue'
import { fetchBarData, renderBarPreview } from '../api/barChart.js'
import { chartPalettes } from '../data/chartPalettes.js'
import { transferBarToPie } from '../data/chartTransfer.js'

export default {
  name: 'BarChartEditorView',
  components: {
    ChartAppearanceFields, ChartBarStyleFields, ChartColorPicker, ChartDataPicker, ChartEditorControls,
    ChartDecorationFields, ChartPreview, ChartSpacingFields, ChartStatisticsFields,
  },
  data() {
    return {
      selection: null,
      dataset: null,
      autoRefresh: false,
      perBar: true,
      layout: 'single',
      barStyles: {},
      colorGroups: chartPalettes,
      activeColorGroup: '',
      annotations: {},
      style: {
        color: '#356fe5', title: '', xLabel: '', yLabel: '', legendLabel: '', legendTitle: '',
        barSpacing: 1, yTickBins: null,
        showLegend: true, showValues: true, legendPosition: 'auto',
        frameMode: 'none', frameColor: '#485b76', frameWidth: 1,
        figureColor: '#ffffff', plotColor: '#ffffff', transparentBackground: false,
        showBarOutline: false, barOutlineColor: '#263c5a', barOutlineWidth: 1,
        showGrid: false, showVerticalGrid: false, showZeroLine: true, gridColor: '#e4ebf4', gridStyle: 'solid',
        chartSize: 'wide', dpi: 130,
        gradient: false,
      },
      loadingData: false,
      rendering: false,
      imageUrl: '',
      dataError: '',
      renderError: '',
    }
  },
  computed: {
    points() {
      return this.dataset?.points || []
    },
    series() {
      return this.dataset?.series || []
    },
    canConvert() {
      return this.points.some(point => point.value > 0) && this.points.every(point => point.value >= 0) &&
        this.series.every(item => item.values.every(value => value >= 0))
    },
    statisticsBars() {
      return this.points.map(point => ({ ...point, key: this.barKey(point) }))
    },
    statisticsScope() {
      const { connectionId, table, categoryColumn, valueColumn, aggregation } = this.selection || {}
      return JSON.stringify([connectionId, table, categoryColumn, valueColumn, aggregation])
    },
    bars() {
      const group = this.colorGroups.find(item => item.id === this.activeColorGroup)
      const palette = (group || this.colorGroups[0]).colors
      const entries = this.layout === 'single' ? this.points : this.series
      return entries.map((point, index) => {
        const key = this.barKey(point)
        return {
          key,
          label: point.label,
          color: palette[index % palette.length],
          legendLabel: point.label.slice(0, 60),
          ...this.barStyles[key],
        }
      })
    },
    seriesName() {
      return this.dataset?.seriesName || ''
    },
    automaticTitle() {
      return this.dataset && this.selection ? `${this.selection.categoryColumn} · ${this.seriesName}` : ''
    },
    automaticXLabel() {
      return this.selection?.categoryColumn || ''
    },
    emptyMessage() {
      if (this.dataset) return '当前所选字段组合没有可绘制的数据。'
      return '选择数据库、数据表和字段以生成图表。'
    },
  },
  watch: {
    selection(next, previous) {
      if (next?.connectionId !== previous?.connectionId || next?.table !== previous?.table ||
        next?.categoryColumn !== previous?.categoryColumn || next?.groupColumn !== previous?.groupColumn) {
        this.activeColorGroup = ''
      }
      this.resetData()
    },
    autoRefresh() { this.scheduleRefresh() },
    perBar() { this.scheduleRender() },
    layout() { this.scheduleRender() },
    points() { this.scheduleRender() },
    style() { this.scheduleRender() },
  },
  beforeDestroy() {
    this._closed = true
    clearTimeout(this._refreshTimer)
    clearTimeout(this._renderTimer)
    this._dataRequest?.abort()
    this._renderRequest?.abort()
    this.clearImage()
  },
  methods: {
    barKey(point) {
      const { connectionId, table, categoryColumn, groupColumn } = this.selection || {}
      return JSON.stringify([connectionId, table, categoryColumn, groupColumn, point.key ?? point.label])
    },
    convertToPie() {
      if (!this.canConvert) return
      transferBarToPie(this.points, this.seriesName, this.style.title || this.automaticTitle)
      this.$router.push({ name: 'pie-chart-editor', params: { chartId: 'pie_features' }, query: { from: 'bar' } })
    },
    applyColorGroup(group) {
      this.activeColorGroup = group.id
      for (const [index, bar] of this.bars.entries()) {
        this.$set(this.barStyles, bar.key, {
          legendLabel: bar.legendLabel,
          color: group.colors[index % group.colors.length],
        })
      }
      this.scheduleRender()
    },
    updateBarStyle(key, change) {
      if (change.color) this.activeColorGroup = ''
      this.$set(this.barStyles, key, { ...this.barStyles[key], ...change })
      this.scheduleRender()
    },
    updateStyle(change) {
      this.style = { ...this.style, ...change }
    },
    updateAnnotations(options) {
      if (JSON.stringify(this.annotations) === JSON.stringify(options)) return
      this.annotations = options
      this.scheduleRender()
    },
    resetData() {
      if (this._closed) return
      this.annotations = {}
      clearTimeout(this._refreshTimer)
      this._dataRequest?.abort()
      this._dataRequest = null
      this.loadingData = false
      this.dataset = null
      this.dataError = ''
      this.clearImage()
      this.scheduleRender()
      if (this.selection) this.loadData()
    },
    scheduleRefresh() {
      clearTimeout(this._refreshTimer)
      if (this._closed || !this.selection || !this.autoRefresh || this._dataRequest) return
      this._refreshTimer = setTimeout(() => {
        if (document.hidden) this.scheduleRefresh()
        else this.loadData()
      }, 5000)
    },
    async loadData() {
      if (this._closed || !this.selection || this._dataRequest) return
      clearTimeout(this._refreshTimer)
      const request = new AbortController()
      this._dataRequest = request
      this.loadingData = !this.dataset
      try {
        const dataset = await fetchBarData(this.selection, request.signal)
        if (this._dataRequest !== request) return
        if (JSON.stringify(dataset) !== JSON.stringify(this.dataset)) this.dataset = dataset
        this.dataError = ''
      } catch (error) {
        if (!this._closed && this._dataRequest === request) this.dataError = error.message
      } finally {
        if (this._dataRequest === request) {
          this._dataRequest = null
          this.loadingData = false
          this.scheduleRefresh()
        }
      }
    },
    scheduleRender() {
      if (this._closed) return
      clearTimeout(this._renderTimer)
      this._renderRequest?.abort()
      this._renderRequest = null
      this.renderError = ''
      this.rendering = this.points.length > 0
      if (!this.rendering) {
        this.clearImage()
        return
      }
      if (this.perBar || this.layout !== 'single') {
        for (const { key, color, legendLabel } of this.bars) {
          if (!this.barStyles[key]) this.$set(this.barStyles, key, { color, legendLabel })
        }
      }
      this._renderTimer = setTimeout(() => this.updatePreview(), 230)
    },
    async updatePreview() {
      const request = new AbortController()
      this._renderRequest = request
      try {
        const style = {
          ...this.style,
          ...(this.layout === 'single' ? this.annotations : {}),
          layout: this.layout,
          gradient: this.layout === 'single' && this.style.gradient,
          title: this.style.title || this.automaticTitle.slice(0, 60),
          xLabel: this.style.xLabel || this.automaticXLabel.slice(0, 60),
          yLabel: this.style.yLabel || this.seriesName.slice(0, 60),
          legendLabel: this.style.legendLabel || this.seriesName.slice(0, 60),
          valueUnit: this.dataset?.valueUnit || '',
        }
        const series = this.layout === 'single' ? [] : this.series
        if (series.length) {
          style.seriesColors = this.bars.map(bar => bar.color)
        } else if (this.perBar && this.layout === 'single') {
          style.barColors = this.bars.map(bar => bar.color)
          style.barLabels = this.bars.map(bar => bar.legendLabel)
        }
        const points = this.points.map(({ label, value }) => ({ label, value }))
        const seriesWithLabels = series.map((item, index) => ({
          ...item, label: this.style.showLegend ? this.bars[index].legendLabel : item.label,
        }))
        const image = await renderBarPreview(points, style, request.signal, seriesWithLabels)
        if (this._closed || this._renderRequest !== request) return
        const url = URL.createObjectURL(image)
        this.clearImage()
        this.imageUrl = url
      } catch (error) {
        if (!this._closed && this._renderRequest === request) this.renderError = error.message
      } finally {
        if (!this._closed && this._renderRequest === request) this.rendering = false
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
.back-link { display: inline-block; margin: 5px 0 15px; color: #235a9f; text-decoration: none; }
.back-link:hover, .text-button:hover { text-decoration: underline; }
.editor-layout { display: grid; grid-template-columns: minmax(220px, 295px) minmax(0, 1fr); gap: 16px; }
.panel { padding: 16px; background: #fff; border: 1px solid #dfe7f1; border-radius: 10px; }
.preview-stack { display: grid; align-self: start; gap: 14px; min-width: 0; }
.style-colors {
  display: grid;
  gap: 8px;
  padding-bottom: 10px;
  border-bottom: 1px solid #e6edf5;
}
.color-modes {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 3px;
  min-width: 0;
  margin: 0;
  padding: 3px;
  border: 0;
  border-radius: 6px;
  background: #edf2f8;
}
.color-modes label {
  padding: 5px 4px;
  border-radius: 4px;
  color: #435774;
  font-size: 13px;
  text-align: center;
  cursor: pointer;
}
.color-modes label.selected { background: #fff; color: #235a9f; font-weight: 600; }
.color-modes label:focus-within { outline: 2px solid #356fe5; outline-offset: -2px; }
.uniform-color {
  display: grid;
  grid-template-columns: 64px minmax(0, 1fr);
  align-items: center;
  gap: 8px;
  color: #435774;
  font-size: 13px;
}
.style-empty { margin: 0; color: #52647d; font-size: 13px; }
.refresh-options label { display: flex; align-items: center; gap: 5px; }
input[type='radio'], input[type='checkbox'] { margin: 0; accent-color: #356fe5; }
.preview-note { margin: 10px 0 0; color: #52647d; }
.chart-layout-field { display: grid; gap: 5px; }
.chart-layout-field select { padding: 7px; border: 1px solid #cdd9e9; border-radius: 6px; background: #fff; font: inherit; }
.gradient-option { display: flex; align-items: center; gap: 6px; color: #435774; font-size: 13px; }
.convert-button { margin-top: 10px; padding: 6px 12px; border: 1px solid #a9c6ed; border-radius: 6px; background: #f3f7fc; color: #235a9f; font: inherit; cursor: pointer; }
.convert-button:disabled { cursor: default; color: #73869f; }
.refresh-options { display: grid; gap: 6px; }
.text-button { justify-self: start; padding: 2px 0; border: 0; background: none; color: #235a9f; font: inherit; cursor: pointer; }
.text-button:disabled { color: #72809a; cursor: default; }
.sr-only { position: absolute; width: 1px; height: 1px; padding: 0; clip-path: inset(50%); overflow: hidden; white-space: nowrap; }

@media (max-width: 960px) {
  .editor-layout { grid-template-columns: minmax(0, 1fr); }
  .preview-stack { grid-row: 1; }
}
</style>
