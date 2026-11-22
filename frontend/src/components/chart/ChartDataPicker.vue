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
        数据表
        <select v-model="table" :disabled="!tables.length || Boolean(loading)">
          <option value="">{{ loading === 'tables' ? '正在读取表…' : '请选择数据表' }}</option>
          <option v-for="name in tables" :key="name">{{ name }}</option>
        </select>
      </label>
      <p v-if="connectionId && !loading && !error && !tables.length">这个数据库没有可读取的数据表。</p>
      <label>
        分类字段
        <select v-model="categoryColumn" :disabled="!columns.length || Boolean(loading)">
          <option value="">{{ loading === 'columns' ? '正在读取字段…' : '请选择分类字段' }}</option>
          <option v-for="column in categoryColumns" :key="column.name" :value="column.name">
            {{ column.name }} · {{ column.type }}
          </option>
        </select>
      </label>
      <label>
        聚合方式
        <select v-model="aggregation">
          <option v-for="mode in aggregations" :key="mode" :value="mode">{{ aggregationLabels[mode] }}</option>
        </select>
      </label>
      <label v-if="aggregation !== 'count'">
        数值字段
        <select v-model="valueColumn" :disabled="!numericColumns.length || Boolean(loading)">
          <option value="">请选择数值字段</option>
          <option v-for="column in numericColumns" :key="column.name" :value="column.name">
            {{ column.name }} · {{ column.type }}
          </option>
        </select>
      </label>
      <p v-if="columns.length && aggregation !== 'count' && !numericColumns.length">
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
import { getDatabaseTable, listDatabaseConnections, listDatabaseTables } from '../../api/database.js'

const numericType = /^(tinyint|smallint|mediumint|int|integer|bigint|decimal|numeric|float|double|real|year)\b/i
const categoryType = /^(char|varchar|tinytext|text|mediumtext|longtext|enum|set|date|datetime|timestamp|time|bool|boolean)\b/i
const aggregationLabels = { sum: '合计', average: '平均值', count: '记录数', max: '最大值', min: '最小值', share: '占比' }

export default {
  name: 'ChartDataPicker',
  props: {
    aggregations: { type: Array, default: () => Object.keys(aggregationLabels) },
  },
  data() {
    return {
      connections: [], tables: [], columns: [],
      connectionId: '', table: '', categoryColumn: '', valueColumn: '', aggregation: this.aggregations[0], aggregationLabels,
      loading: 'connections', error: '',
    }
  },
  computed: {
    numericColumns() {
      return this.columns.filter(column => numericType.test(column.type))
    },
    categoryColumns() {
      return this.columns.filter(column => categoryType.test(column.type) || numericType.test(column.type))
    },
    selection() {
      const { connectionId, table, categoryColumn, aggregation, valueColumn } = this
      if (this.loading || !connectionId || !table || !categoryColumn || (aggregation !== 'count' && !valueColumn)) {
        return null
      }
      return { connectionId, table, categoryColumn, aggregation, valueColumn: aggregation === 'count' ? '' : valueColumn }
    },
  },
  watch: {
    connectionId() { this.loadTables() },
    table() { if (this.loading !== 'tables') this.loadColumns() },
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
      this.clearColumns()
      this.error = ''
      this.loading = this.connectionId ? 'tables' : ''
      if (!this.connectionId) return
      try {
        const result = await listDatabaseTables(this.connectionId)
        if (request === this._metadataRequest) this.tables = result.tables
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
        const result = await getDatabaseTable(this.table, this.connectionId)
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
      this.valueColumn = ''
    },
  },
}
</script>

<style scoped>
.data-picker { display: grid; gap: 12px; }
label { display: grid; gap: 5px; min-width: 0; }
select {
  width: 100%;
  padding: 8px;
  border: 1px solid #cdd9e9;
  border-radius: 6px;
  background: white;
  color: #172942;
  font: inherit;
}
select:disabled { background: #f4f6fa; color: #687894; }
p { margin: 0; color: #52647d; line-height: 1.5; }
.picker-error { color: #a12629; }
a { color: #235a9f; }
</style>
