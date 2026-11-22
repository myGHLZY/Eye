<template>
  <section>
    <router-link class="back-link" :to="{ name: 'chart-workbench', params: { chartId: $route.params.chartId } }">
      <i class="el-icon-arrow-left" aria-hidden="true"></i> 返回图表工作台
    </router-link>

    <div class="editor-layout">
      <aside class="panel controls">
        <div class="tabs" role="group" aria-label="编辑面板">
          <button type="button" :aria-pressed="panel === 'data'" @click="panel = 'data'">数据来源</button>
          <button type="button" :aria-pressed="panel === 'style'" @click="panel = 'style'">图表样式</button>
        </div>
        <div v-show="panel === 'data'" class="fields">
          <chart-data-picker v-model="selection" :aggregations="aggregations" />
          <template v-if="selection">
            <label class="check"><input v-model="autoRefresh" type="checkbox"> 每 5 秒检查数据变化</label>
            <button class="text-button" type="button" :disabled="loading" @click="loadData">刷新数据</button>
          </template>
        </div>

        <div v-show="panel === 'style'" class="fields">
          <chart-palette-picker :palettes="palettes" :active-id="paletteId" @select="applyPalette" />
          <label class="field">图表标题<input v-model="style.title" type="text" maxlength="60" :placeholder="automaticTitle"></label>
          <label class="field">扇区标签
            <select v-model="style.labelMode">
              <option value="percent">百分比</option><option value="value">数值</option><option value="none">隐藏</option>
            </select>
          </label>
          <label class="field">图例位置
            <select v-model="style.legendPosition">
              <option value="right">右侧</option><option value="bottom">下方</option><option value="none">隐藏</option>
            </select>
          </label>
          <label v-if="style.legendPosition !== 'none'" class="field">图例标题
            <input v-model="style.legendTitle" type="text" maxlength="60">
          </label>
          <label class="field">突出扇区
            <select v-model="highlight">
              <option value="">无</option>
              <option v-for="point in points" :key="point.key" :value="point.key">{{ point.label }}</option>
            </select>
          </label>

          <details>
            <summary>角度、轮廓与导出</summary>
            <div class="fields detail-fields">
              <label class="field">起始角度
                <input v-model.number="style.startAngle" type="range" min="0" max="360" step="5">
                <output>{{ style.startAngle }}°</output>
              </label>
              <div class="checks">
                <label class="check"><input v-model="style.clockwise" type="checkbox"> 顺时针</label>
                <label class="check"><input v-model="style.donut" type="checkbox"> 环形</label>
                <label class="check"><input v-model="style.showOutline" type="checkbox"> 扇区描边</label>
              </div>
              <div v-if="style.showOutline" class="field"><span>描边颜色</span>
                <chart-color-picker v-model="style.outlineColor" label="扇区描边颜色" show-code />
              </div>
              <label class="check"><input v-model="style.transparentBackground" type="checkbox"> 透明背景</label>
              <div v-if="!style.transparentBackground" class="field"><span>背景颜色</span>
                <chart-color-picker v-model="style.figureColor" label="画布背景颜色" show-code />
              </div>
              <label class="field">PNG 分辨率
                <select v-model.number="style.dpi">
                  <option :value="130">130 DPI</option><option :value="200">200 DPI</option><option :value="300">300 DPI</option>
                </select>
              </label>
            </div>
          </details>
        </div>
      </aside>

      <div class="preview-stack">
        <chart-preview class="panel" :url="imageUrl" :title="style.title || automaticTitle"
          :busy="loading || rendering" :error="dataError || renderError"
          :empty-message="dataset ? '当前数据没有可绘制的正值。' : '选择数据库、表和字段以生成饼图。'"
          filename="pie-chart.png">
          <p v-if="dataset && dataset.combined" class="note">较小的分类已合并为「其他分类」，占比按全部数据计算。</p>
        </chart-preview>
        <section v-if="points.length" class="panel">
          <h2>扇区数据</h2>
          <div class="table-scroll">
            <table>
              <thead><tr><th scope="col">分类</th><th scope="col">颜色</th><th scope="col">数值</th><th scope="col">占比</th></tr></thead>
              <tbody>
                <tr v-for="point in points" :key="point.key">
                  <th scope="row">{{ point.label }}</th>
                  <td><chart-color-picker :value="colors[point.key]" :label="point.label + ' 的扇区颜色'"
                    @input="$set(colors, point.key, $event)" /></td>
                  <td>{{ formatValue(point.value) }}</td>
                  <td>{{ (point.value / dataset.total * 100).toFixed(1) }}%</td>
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
import ChartColorPicker from '../components/chart/ChartColorPicker.vue'
import ChartDataPicker from '../components/chart/ChartDataPicker.vue'
import ChartPalettePicker from '../components/chart/ChartPalettePicker.vue'
import ChartPreview from '../components/chart/ChartPreview.vue'
import { chartPalettes } from '../data/chartPalettes.js'
import { fetchPieData, renderPiePreview } from '../api/pieChart.js'

export default {
  name: 'PieChartEditorView',
  components: { ChartColorPicker, ChartDataPicker, ChartPalettePicker, ChartPreview },
  data() {
    return {
      panel: 'data', selection: null, dataset: null, aggregations: ['sum', 'count'],
      autoRefresh: true, palettes: chartPalettes, paletteId: 'classic', highlight: '', colors: {},
      style: {
        title: '', legendTitle: '', legendPosition: 'right', labelMode: 'percent',
        startAngle: 90, clockwise: true, donut: false, showOutline: true, outlineColor: '#ffffff',
        transparentBackground: false, figureColor: '#ffffff', dpi: 130,
      },
      loading: false, rendering: false, imageUrl: '', dataError: '', renderError: '',
    }
  },
  computed: {
    points() { return this.dataset?.points || [] },
    automaticTitle() {
      return this.dataset && this.selection ? `${this.selection.categoryColumn} · ${this.dataset.seriesName}` : ''
    },
    renderStyle() {
      const index = this.points.findIndex(point => point.key === this.highlight)
      return {
        ...this.style,
        title: this.style.title || this.automaticTitle.slice(0, 60),
        highlight: index >= 0 ? index : null,
        colors: this.points.map(point => this.colors[point.key]),
      }
    },
  },
  watch: {
    selection() {
      this._dataRequest?.abort()
      this._dataRequest = null
      this.dataset = null
      this.colors = {}
      this.highlight = ''
      this.dataError = ''
      this.loading = false
      this.clearImage()
      this.scheduleRender()
      this.loadData()
    },
    autoRefresh() { this.scheduleRefresh() },
    renderStyle() { this.scheduleRender() },
  },
  beforeDestroy() {
    this._closed = true
    this._dataRequest?.abort()
    this._renderRequest?.abort()
    clearTimeout(this._refreshTimer)
    clearTimeout(this._renderTimer)
    this.clearImage()
  },
  methods: {
    formatValue(value) {
      return new Intl.NumberFormat('zh-CN', { maximumSignificantDigits: 8 }).format(value)
    },
    applyPalette(palette) {
      this.paletteId = palette.id
      this.colors = Object.fromEntries(this.points.map((point, index) => [point.key, palette.colors[index % palette.colors.length]]))
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
      clearTimeout(this._refreshTimer)
      if (this._closed || !this.selection || this._dataRequest) return
      const request = new AbortController()
      this._dataRequest = request
      this.loading = !this.dataset
      try {
        const data = await fetchPieData(this.selection, request.signal)
        if (this._closed || this._dataRequest !== request) return
        if (JSON.stringify(data) !== JSON.stringify(this.dataset)) {
          const palette = this.palettes.find(item => item.id === this.paletteId)
          data.points.forEach((point, index) => {
            if (!this.colors[point.key]) this.$set(this.colors, point.key, palette.colors[index % palette.colors.length])
          })
          this.dataset = data
        }
        this.dataError = ''
      } catch (error) {
        if (!this._closed && this._dataRequest === request) this.dataError = error.message
      } finally {
        if (!this._closed && this._dataRequest === request) {
          this._dataRequest = null
          this.loading = false
          this.scheduleRefresh()
        }
      }
    },
    scheduleRender() {
      clearTimeout(this._renderTimer)
      this._renderRequest?.abort()
      this._renderRequest = null
      this.renderError = ''
      this.rendering = this.points.length > 0
      if (this.rendering) this._renderTimer = setTimeout(() => this.updatePreview(), 230)
      else this.clearImage()
    },
    async updatePreview() {
      const request = new AbortController()
      this._renderRequest = request
      try {
        const image = await renderPiePreview(this.points, this.renderStyle, request.signal)
        if (this._closed || this._renderRequest !== request) return
        this.clearImage()
        this.imageUrl = URL.createObjectURL(image)
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
.back-link:hover { text-decoration: underline; }
.editor-layout { display: grid; grid-template-columns: minmax(235px, 295px) minmax(0, 1fr); gap: 16px; }
.panel { min-width: 0; padding: 14px; border: 1px solid #dfe7f1; border-radius: 10px; background: #fff; }
.controls, .preview-stack { display: grid; gap: 12px; min-width: 0; align-self: start; }
.tabs { display: grid; grid-template-columns: 1fr 1fr; gap: 4px; padding: 4px; background: #e8eef7; border-radius: 8px; }
.tabs button { padding: 7px; border: 0; border-radius: 5px; background: transparent; color: #435774; font: inherit; cursor: pointer; }
.tabs button[aria-pressed='true'] { background: white; color: #15243b; font-weight: 600; }
.fields { display: grid; gap: 8px; color: #435774; font-size: 13px; }
.field { display: grid; grid-template-columns: 64px minmax(0, 1fr); gap: 6px; align-items: center; }
select, input[type='text'] {
  width: 100%; min-width: 0; box-sizing: border-box; min-height: 30px; padding: 4px 6px;
  border: 1px solid #cdd9e9; border-radius: 5px; background: #fff; color: #172942; font: inherit;
}
input[type='range'] { width: 100%; margin: 0; }
output { grid-column: 2; justify-self: end; }
.checks, .check { display: flex; align-items: center; flex-wrap: wrap; gap: 6px; }
.checks { gap: 8px; }
input[type='checkbox'], input[type='range'] { accent-color: #356fe5; }
.text-button { justify-self: start; border: 0; padding: 0; background: none; color: #235a9f; font: inherit; cursor: pointer; }
details { border: 1px solid #dfe7f1; border-radius: 6px; background: #f8faff; }
summary { padding: 8px; cursor: pointer; }
.detail-fields { padding: 0 8px 8px; }
h2 { margin: 0 0 10px; color: #15243b; font-size: 16px; }
.note { margin: 8px 0 0; color: #52647d; font-size: 13px; }
.table-scroll { max-height: 245px; overflow: auto; border: 1px solid #dfe7f1; border-radius: 6px; }
table { width: 100%; border-spacing: 0; text-align: left; font-size: 13px; color: #263c5a; }
thead th { position: sticky; top: 0; background: #f3f7fc; white-space: nowrap; }
th, td { padding: 6px 8px; border-bottom: 1px solid #e5edf6; overflow-wrap: anywhere; }
tbody th { font-weight: 400; }
@media (max-width: 960px) {
  .editor-layout { grid-template-columns: minmax(0, 1fr); }
}
</style>
