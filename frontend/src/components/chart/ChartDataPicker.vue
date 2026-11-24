<template>
  <div class="data-picker">
    <p v-if="error" role="alert" class="picker-error">{{ error }}</p>
    <template v-if="connections.length">
      <label>
        数据库
        <select v-model="connectionId">
          <option value="">请选择连接</option>
          <option v-for="connection in connections" :key="connection.id" :value="connection.id">
            {{ connectionLabel(connection) }}
          </option>
        </select>
      </label>
      <label>
        数据表 / 视图
        <select v-model="table" :disabled="!hasSources || Boolean(loading)">
          <option value="">{{ loading === 'tables' ? '正在读取数据源…' : '请选择数据表或视图' }}</option>
          <optgroup v-if="tables.length" label="数据表">
            <option v-for="name in tables" :key="name">{{ name }}</option>
          </optgroup>
          <optgroup v-if="views.length" label="视图">
            <option v-for="name in views" :key="name">{{ name }}</option>
          </optgroup>
        </select>
      </label>
      <p v-if="connectionId && !loading && !error && !hasSources">这个数据库没有可读取的数据表或视图。</p>
      <label v-if="!sampleMode">
        {{ categoryLabel }}
        <select v-model="categoryColumn" :disabled="!columns.length || Boolean(loading)">
          <option value="">{{ loading === 'columns' ? '正在读取字段…' : '请选择' + categoryLabel }}</option>
          <option v-for="column in categoryColumns" :key="column.name" :value="column.name">
            {{ column.name }} · {{ column.type }}
          </option>
        </select>
      </label>
      <label v-if="groupMode !== 'none'">
        {{ groupLabel }}
        <select v-model="groupColumn" :disabled="!columns.length || Boolean(loading)">
          <option value="">{{ groupMode === 'required' ? '请选择字段' : rawValues ? '不分组' : '不分系列' }}</option>
          <option v-for="column in groupColumns" :key="column.name" :value="column.name">
            {{ column.name }} · {{ column.type }}
          </option>
        </select>
      </label>
      <label v-if="!rawValues && aggregations.length > 1">
        聚合方式
        <select v-model="aggregation">
          <option v-for="mode in aggregations" :key="mode" :value="mode">{{ aggregationLabels[mode] }}</option>
        </select>
      </label>
      <template v-if="wideMetrics">
        <label>数值列
          <select :value="''" :disabled="Boolean(loading) || !availableMetrics.length || valueColumns.length >= 16"
            @change="addMetric($event.target)">
            <option value="">选择要添加的数值列</option>
            <option v-for="column in availableMetrics" :key="column.name" :value="column.name">
              {{ column.name }} · {{ column.type }}
            </option>
          </select>
        </label>
        <ol v-if="valueColumns.length" class="metric-order" aria-label="热力图列顺序">
          <li v-for="(name, index) in valueColumns" :key="name">
            <span>{{ name }}</span>
            <button type="button" :aria-label="'上移 ' + name" :disabled="index === 0" @click="moveMetric(index, -1)">↑</button>
            <button type="button" :aria-label="'下移 ' + name" :disabled="index === valueColumns.length - 1"
              @click="moveMetric(index, 1)">↓</button>
            <button type="button" :aria-label="'移除 ' + name" @click="valueColumns.splice(index, 1)">×</button>
          </li>
        </ol>
        <div v-if="numericRow" class="row-range">
          <label>行范围起点<input v-model.number="rowMin" type="number" step="any" placeholder="不限"></label>
          <label>行范围终点<input v-model.number="rowMax" type="number" step="any" placeholder="不限"></label>
        </div>
      </template>
      <label v-else-if="rawValues || aggregation !== 'count'">
        {{ valueLabel }}
        <select v-model="valueColumn" :disabled="!numericColumns.length || Boolean(loading)">
          <option value="">请选择数值字段</option>
          <option v-for="column in numericColumns" :key="column.name" :value="column.name">
            {{ column.name }} · {{ column.type }}
          </option>
        </select>
      </label>
      <label v-if="secondaryLabel">
        {{ secondaryLabel }}
        <select v-model="secondaryValueColumn" :disabled="!numericColumns.length || Boolean(loading)">
          <option value="">请选择数值字段</option>
          <option v-for="column in numericColumns.filter(item => item.name !== valueColumn)"
            :key="column.name" :value="column.name">{{ column.name }} · {{ column.type }}</option>
        </select>
      </label>
      <label v-if="rawPoints && pointLimit">最多绘制点数
        <select v-model.number="maxPoints">
          <option :value="100">100</option><option :value="250">250</option><option :value="500">500</option>
        </select>
      </label>
      <p v-if="wideMetrics && categoryColumn && !valueColumns.length && !availableMetrics.length">此表没有可选的数值列。</p>
      <p v-else-if="sampleMode && columns.length && !numericColumns.length">此表没有可选的数值字段。</p>
      <p v-else-if="!wideMetrics && !rawValues && columns.length && aggregation !== 'count' && !numericColumns.length">
        此表可以按记录数统计。
      </p>
      <p v-else-if="aggregation === 'share' && numericColumns.length">
        每个分类的合计 ÷ 所有分类的合计 × 100%。
      </p>
    </template>
    <p v-else-if="loading">正在读取数据库连接…</p>
    <p v-else-if="!error">还没有已连接的数据库。<router-link :to="{ name: 'data-sources' }">打开数据库连接</router-link></p>
  </div>
</template>

<script>
import { getChartSource, listDatabaseConnections, listChartSources } from '../../api/database.js'

const numericType = /^(tinyint|smallint|mediumint|int|integer|bigint|decimal|numeric|float|double|real|year)\b/i
const categoryType = /^(char|varchar|tinytext|text|mediumtext|longtext|enum|set|date|datetime|timestamp|time|bool|boolean)\b/i
const aggregationLabels = {
  sum: '合计 (SUM)', average: '平均值 (AVG)', count: '记录数 (COUNT)',
  max: '最大值 (MAX)', min: '最小值 (MIN)', share: '占比 (SUM / SUM)',
  raw: '原始记录（每行一条记录）',
}

export default {
  name: 'ChartDataPicker',
  props: {
    aggregations: { type: Array, default: () => Object.keys(aggregationLabels) },
    categoryLabel: { type: String, default: '分类字段' },
    groupLabel: { type: String, default: '系列字段' },
    groupMode: { type: String, default: 'none' },
    valueLabel: { type: String, default: '数值字段' },
    secondaryLabel: { type: String, default: '' },
    rawPoints: Boolean,
    pointLimit: { type: Boolean, default: true },
    sampleMode: Boolean,
    numericCategory: Boolean,
    wideMetrics: Boolean,
  },
  data() {
    return {
      connections: [], tables: [], views: [], columns: [],
      connectionId: '', table: '', categoryColumn: '', groupColumn: '', valueColumn: '', secondaryValueColumn: '',
      valueColumns: [], rowMin: '', rowMax: '', maxPoints: 500,
      aggregation: this.aggregations[0], aggregationLabels,
      loading: 'connections', error: '',
    }
  },
  computed: {
    hasSources() { return Boolean(this.tables.length || this.views.length) },
    rawValues() { return this.rawPoints || this.sampleMode },
    selectedGroup() {
      return this.groupMode !== 'none' && this.groupColumn !== this.categoryColumn &&
        (!this.rawValues || this.groupColumn !== this.valueColumn) ? this.groupColumn : ''
    },
    numericColumns() {
      return this.columns.filter(column => numericType.test(column.type))
    },
    numericRow() {
      return this.numericColumns.some(column => column.name === this.categoryColumn)
    },
    availableMetrics() {
      return this.numericColumns.filter(column => column.name !== this.categoryColumn && !this.valueColumns.includes(column.name))
    },
    categoryColumns() {
      if (this.numericCategory) return this.numericColumns
      return this.columns.filter(column => categoryType.test(column.type) || numericType.test(column.type))
    },
    groupColumns() {
      return this.columns.filter(column => column.name !== this.categoryColumn &&
        (!this.rawValues || column.name !== this.valueColumn) &&
        (categoryType.test(column.type) || numericType.test(column.type)))
    },
    selection() {
      const { connectionId, table, categoryColumn, aggregation, valueColumn } = this
      if (this.loading || !connectionId || !table) return null
      if (this.sampleMode) {
        if (!valueColumn) return null
        return { connectionId, table, valueColumn, ...(this.selectedGroup ? { groupColumn: this.selectedGroup } : {}) }
      }
      if (!categoryColumn || !this.aggregations.includes(aggregation)) return null
      if (this.wideMetrics) {
        if (!this.valueColumns.length) return null
        return {
          layout: 'wide', connectionId, table, categoryColumn, aggregation, valueColumns: [...this.valueColumns],
          ...(this.numericRow && this.rowMin !== '' ? { rowMin: this.rowMin } : {}),
          ...(this.numericRow && this.rowMax !== '' ? { rowMax: this.rowMax } : {}),
        }
      }
      if (((this.rawPoints || aggregation !== 'count') && !valueColumn) ||
        (this.secondaryLabel && (!this.secondaryValueColumn || this.secondaryValueColumn === valueColumn)) ||
        (this.groupMode === 'required' && !this.selectedGroup)) {
        return null
      }
      return {
        connectionId, table, categoryColumn,
        ...(this.rawPoints ? { valueColumn, ...(this.pointLimit ? { maxPoints: this.maxPoints } : {}) }
          : { aggregation, valueColumn: aggregation === 'count' ? '' : valueColumn }),
        ...(this.selectedGroup ? { groupColumn: this.selectedGroup } : {}),
        ...(this.secondaryLabel ? { secondaryValueColumn: this.secondaryValueColumn } : {}),
      }
    },
  },
  watch: {
    wideMetrics() { this.aggregation = this.aggregations[0] },
    aggregations(modes) {
      if (!modes.includes(this.aggregation)) this.aggregation = modes[0]
    },
    connectionId() { this.loadTables() },
    table() { if (this.loading !== 'tables') this.loadColumns() },
    categoryColumn(value) {
      if (value === this.groupColumn) this.groupColumn = ''
      if (this.valueColumns.includes(value)) this.valueColumns = this.valueColumns.filter(name => name !== value)
      this.rowMin = this.rowMax = ''
    },
    valueColumn(value) {
      if (this.rawValues && value === this.groupColumn) this.groupColumn = ''
      if (value === this.secondaryValueColumn) this.secondaryValueColumn = ''
    },
    selection(value) { this.$emit('input', value) },
  },
  created() {
    this._metadataRequest = 0
    this.loadConnections()
  },
  beforeDestroy() {
    this._metadataRequest += 1
    this.$emit('input', null)
  },
  methods: {
    addMetric(select) {
      if (select.value && this.valueColumns.length < 16) this.valueColumns.push(select.value)
      select.value = ''
    },
    moveMetric(index, offset) {
      const [name] = this.valueColumns.splice(index, 1)
      this.valueColumns.splice(index + offset, 0, name)
    },
    connectionLabel(connection) {
      const duplicate = this.connections.some(item => item.id !== connection.id && item.database === connection.database)
      return duplicate
        ? `${connection.database} · ${connection.host}:${connection.port} · ${connection.username}`
        : connection.database
    },
    async loadConnections() {
      const request = ++this._metadataRequest
      try {
        const result = await listDatabaseConnections()
        if (request === this._metadataRequest) this.connections = result.connections
      } catch (error) {
        if (request === this._metadataRequest) this.error = error.message
      } finally {
        if (request === this._metadataRequest) this.loading = ''
      }
    },
    async loadTables() {
      const request = ++this._metadataRequest
      this.table = ''
      this.tables = []
      this.views = []
      this.clearColumns()
      this.error = ''
      this.loading = this.connectionId ? 'tables' : ''
      if (!this.connectionId) return
      try {
        const result = await listChartSources(this.connectionId)
        if (request === this._metadataRequest) {
          this.tables = result.tables
          this.views = result.views
        }
      } catch (error) {
        if (request === this._metadataRequest) this.error = error.message
      } finally {
        if (request === this._metadataRequest) this.loading = ''
      }
    },
    async loadColumns() {
      const request = ++this._metadataRequest
      this.clearColumns()
      this.error = ''
      this.loading = this.table ? 'columns' : ''
      if (!this.table) return
      try {
        const result = await getChartSource(this.table, this.connectionId)
        if (request === this._metadataRequest) this.columns = result.columns
      } catch (error) {
        if (request === this._metadataRequest) this.error = error.message
      } finally {
        if (request === this._metadataRequest) this.loading = ''
      }
    },
    clearColumns() {
      this.columns = []
      this.categoryColumn = ''
      this.groupColumn = ''
      this.valueColumn = ''
      this.secondaryValueColumn = ''
      this.valueColumns = []
      this.rowMin = this.rowMax = ''
    },
  },
}
</script>

<style scoped>
.data-picker { display: grid; gap: 12px; }
label { display: grid; gap: 5px; min-width: 0; }
select, input[type='number'] {
  box-sizing: border-box;
  width: 100%;
  padding: 8px;
  border: 1px solid #cdd9e9;
  border-radius: 6px;
  background: white;
  color: #172942;
  font: inherit;
}
select:disabled { background: #f4f6fa; color: #687894; }
.row-range { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; }
.metric-order { margin: 0; padding: 0 0 0 25px; }
.metric-order li { padding-block: 2px; }
.metric-order li span { display: inline-block; min-width: 48px; overflow-wrap: anywhere; margin-right: 6px; }
.metric-order button { margin-right: 4px; padding: 2px 6px; cursor: pointer; }
.metric-order button:disabled { cursor: default; }
p { margin: 0; color: #52647d; line-height: 1.5; }
.picker-error { color: #a12629; }
a { color: #235a9f; }
</style>
