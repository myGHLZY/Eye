<template>
  <section class="bar-chart-editor">
    <router-link class="back-link" :to="{ name: 'chart-workbench', params: { chartId: $route.params.chartId } }">
      <i class="el-icon-arrow-left" aria-hidden="true"></i> 返回图表工作台
    </router-link>

    <div class="editor-layout">
      <aside class="editor-controls">
        <div class="editor-tabs" role="group" aria-label="编辑面板">
          <button type="button" :aria-pressed="activePanel === 'data'" @click="activePanel = 'data'">数据来源</button>
          <button type="button" :aria-pressed="activePanel === 'style'" @click="activePanel = 'style'">图表样式</button>
        </div>
        <section v-show="activePanel === 'data'" class="panel control-panel" aria-label="数据来源">
          <chart-data-picker v-model="selection" />
          <div v-if="selection" class="refresh-options">
            <label><input v-model="autoRefresh" type="checkbox"> 每 5 秒检查数据变化</label>
            <button class="text-button" type="button" :disabled="loadingData" @click="loadData">刷新数据</button>
          </div>
        </section>

        <section v-show="activePanel === 'style'" class="panel control-panel style-panel" aria-label="图表样式">
          <div class="style-colors">
            <fieldset class="color-modes">
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
            <template v-if="perBar">
              <chart-bar-style-fields v-if="bars.length" :bars="bars" :show-legend="style.showLegend"
                :color-groups="colorGroups" :active-group="activeColorGroup"
                @change="updateBarStyle" @choose-group="applyColorGroup" />
              <p v-else class="style-empty">选择数据后可逐柱配色。</p>
            </template>
            <div v-else class="uniform-color">
              <span>柱形颜色</span>
              <chart-color-picker :value="style.color" label="统一柱形颜色" show-code
                @input="updateStyle({ color: $event })" />
            </div>
          </div>
          <chart-appearance-fields :value="style" :per-bar="perBar" :automatic-title="automaticTitle"
            :automatic-legend="seriesName" :automatic-x-label="automaticXLabel" :automatic-y-label="seriesName"
            @change="updateStyle" />
          <chart-spacing-fields :bar-spacing="style.barSpacing" :y-tick-bins="style.yTickBins"
            @change="updateStyle" />
          <chart-decoration-fields :value="style" @change="updateStyle" />
        </section>
      </aside>

      <div class="preview-stack">
        <chart-preview class="panel" :url="imageUrl" :title="style.title || automaticTitle"
          :busy="loadingData || rendering" :error="dataError || renderError" :empty-message="emptyMessage"
          filename="bar-chart.png">
          <p v-if="dataset?.truncated" class="preview-note">
            共展示数值最高的 {{ dataset.points.length }} 个分类。
            <span v-if="dataset.valueUnit === '%'">占比按全部分类的总和计算。</span>
          </p>
        </chart-preview>
        <chart-statistics-fields :bars="statisticsBars" :scope="statisticsScope"
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
import ChartDataPicker from '../components/chart/ChartDataPicker.vue'
import ChartDecorationFields from '../components/chart/ChartDecorationFields.vue'
import ChartPreview from '../components/chart/ChartPreview.vue'
import ChartSpacingFields from '../components/chart/ChartSpacingFields.vue'
import ChartStatisticsFields from '../components/chart/ChartStatisticsFields.vue'
import { fetchBarData, renderBarPreview } from '../api/barChart.js'
import { chartPalettes } from '../data/chartPalettes.js'

export default {
  name: 'BarChartEditorView',
  components: {
    ChartAppearanceFields, ChartBarStyleFields, ChartColorPicker, ChartDataPicker,
    ChartDecorationFields, ChartPreview, ChartSpacingFields, ChartStatisticsFields,
  },
  data() {
    return {
      activePanel: 'data',
      selection: null,
      dataset: null,
      autoRefresh: true,
      perBar: true,
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
      return this.points.map((point, index) => {
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
        next?.categoryColumn !== previous?.categoryColumn) {
        this.activeColorGroup = ''
      }
      this.resetData()
    },
    autoRefresh() { this.scheduleRefresh() },
    perBar() { this.scheduleRender() },
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
      const { connectionId, table, categoryColumn } = this.selection || {}
      return JSON.stringify([connectionId, table, categoryColumn, point.key ?? point.label])
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
      if (this.perBar) {
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
          ...this.annotations,
          title: this.style.title || this.automaticTitle.slice(0, 60),
          xLabel: this.style.xLabel || this.automaticXLabel.slice(0, 60),
          yLabel: this.style.yLabel || this.seriesName.slice(0, 60),
          legendLabel: this.style.legendLabel || this.seriesName.slice(0, 60),
          valueUnit: this.dataset?.valueUnit || '',
        }
        if (this.perBar) {
          style.barColors = this.bars.map(bar => bar.color)
          style.barLabels = this.bars.map(bar => bar.legendLabel)
        }
        const points = this.points.map(({ label, value }) => ({ label, value }))
        const image = await renderBarPreview(points, style, request.signal)
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
.editor-controls { display: grid; gap: 14px; align-self: start; min-width: 0; }
.panel { padding: 16px; background: #fff; border: 1px solid #dfe7f1; border-radius: 10px; }
.preview-stack { display: grid; align-self: start; gap: 14px; min-width: 0; }
.control-panel { display: grid; gap: 11px; }
.editor-tabs { display: flex; gap: 4px; padding: 4px; background: #e8eef7; border-radius: 8px; }
.editor-tabs button {
  flex: 1;
  padding: 7px 8px;
  border: 0;
  border-radius: 5px;
  background: transparent;
  color: #435774;
  font: inherit;
  cursor: pointer;
}
.editor-tabs button[aria-pressed='true'] { background: white; color: #15243b; font-weight: 600; }
.style-panel { padding: 12px; gap: 11px; }
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
.refresh-options { display: grid; gap: 6px; }
.text-button { justify-self: start; padding: 2px 0; border: 0; background: none; color: #235a9f; font: inherit; cursor: pointer; }
.text-button:disabled { color: #72809a; cursor: default; }
.sr-only { position: absolute; width: 1px; height: 1px; padding: 0; clip-path: inset(50%); overflow: hidden; white-space: nowrap; }

@media (max-width: 960px) {
  .editor-layout { grid-template-columns: minmax(0, 1fr); }
  .preview-stack { grid-row: 1; }
}
</style>
