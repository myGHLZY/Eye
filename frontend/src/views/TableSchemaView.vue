<template>
  <section v-if="diagramVisible" key="diagram" class="schema-browser diagram-page">
    <div class="schema-toolbar">
      <el-button size="small" icon="el-icon-arrow-left" @click="closeDiagram">返回表与关系</el-button>
    </div>
    <p v-if="diagramLoading" role="status">正在读取全库结构…</p>
    <template v-else-if="diagramError">
      <el-alert :title="diagramError" type="error" :closable="false" show-icon />
      <el-button class="diagram-retry" size="small" @click="loadDiagram">重新加载</el-button>
    </template>
    <template v-else-if="diagram">
      <p class="diagram-summary">
        <strong>{{ diagram.database }}</strong> · {{ diagram.tables.length }} 张表 · {{ diagram.relations.length }} 条外键约束
      </p>
      <table-relations-graph
        v-if="diagram.tables.length"
        :detail="diagram"
        :layout-database="diagramLayout"
        @select-table="openDiagramTable"
      />
      <p v-else-if="!diagram.tables.length" role="status">当前数据库中没有可查看的表。</p>
    </template>
  </section>

  <section v-else key="tables" class="schema-browser">
    <div class="schema-toolbar">
      <span v-if="database">当前数据库 <strong>{{ database }}</strong></span>
      <div class="schema-actions">
        <el-button size="small" :loading="loadingTables" @click="refreshTables()">刷新表列表</el-button>
        <el-button type="primary" size="small" @click="openDiagram">查看 ER 图</el-button>
      </div>
    </div>
    <el-alert v-if="listError" :title="listError" type="error" :closable="false" show-icon />
    <p v-else-if="loadingTables" role="status">正在读取数据库表…</p>
    <p v-else-if="!tables.length" role="status">当前数据库中没有可查看的表。</p>

    <div v-else class="schema-layout">
      <aside class="table-sidebar" aria-label="数据表">
        <el-input
          v-model="search"
          aria-label="搜索表名"
          placeholder="搜索表名"
          size="small"
          clearable
        />
        <ul v-if="visibleTables.length" class="table-list">
          <li v-for="name in visibleTables" :key="name">
            <button
              class="table-option"
              type="button"
              :aria-pressed="name === selectedTable ? 'true' : 'false'"
              @click="loadTable(name)"
            >{{ name }}</button>
          </li>
        </ul>
        <p v-else class="empty-search">没有匹配的表。</p>
      </aside>

      <div class="table-detail">
        <h2>{{ selectedTable }}</h2>
        <p v-if="loadingDetail" role="status">正在读取表结构…</p>
        <el-alert v-else-if="detailError" :title="detailError" type="error" :closable="false" show-icon />
        <el-tabs v-else-if="detail" v-model="activeTab">
          <el-tab-pane label="字段" name="columns">
            <div class="field-table-scroll">
              <table class="field-table" aria-label="表字段">
                <thead>
                  <tr>
                    <th scope="col">字段</th>
                    <th scope="col">类型</th>
                    <th scope="col">键</th>
                    <th scope="col">可空</th>
                    <th scope="col">默认值</th>
                    <th scope="col">备注</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="column in detail.columns" :key="column.name">
                    <th scope="row">{{ column.name }}</th>
                    <td>{{ column.type }}</td>
                    <td class="column-keys">
                      <el-tag v-if="column.primaryKey" size="mini" type="danger">主键</el-tag>
                      <el-tag v-if="column.foreignKey" size="mini" type="success">外键</el-tag>
                      <span v-if="!column.primaryKey && !column.foreignKey">—</span>
                    </td>
                    <td>{{ column.nullable ? '是' : '否' }}</td>
                    <td>{{ column.default == null ? '—' : column.default }}</td>
                    <td>{{ column.comment || '—' }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </el-tab-pane>
          <el-tab-pane label="关系图" name="relations">
            <table-relations-graph
              v-if="activeTab === 'relations' && detail.relations.length"
              :detail="detail"
              @select-table="openRelatedTable"
            />
            <p v-else-if="activeTab === 'relations'">当前表没有可见的外键关系。</p>
          </el-tab-pane>
        </el-tabs>
      </div>
    </div>
  </section>
</template>

<script>
import ElAlert from 'element-ui/lib/alert'
import ElButton from 'element-ui/lib/button'
import ElInput from 'element-ui/lib/input'
import ElTabPane from 'element-ui/lib/tab-pane'
import ElTabs from 'element-ui/lib/tabs'
import ElTag from 'element-ui/lib/tag'
import { getDatabaseDiagram, getDatabaseTable, listDatabaseTables } from '../api/database.js'

import 'element-ui/lib/theme-chalk/alert.css'
import 'element-ui/lib/theme-chalk/button.css'
import 'element-ui/lib/theme-chalk/input.css'
import 'element-ui/lib/theme-chalk/tab-pane.css'
import 'element-ui/lib/theme-chalk/tabs.css'
import 'element-ui/lib/theme-chalk/tag.css'

export default {
  name: 'TableSchemaView',
  components: {
    ElAlert, ElButton, ElInput, ElTabs, ElTabPane, ElTag,
    TableRelationsGraph: () => import('../components/TableRelationsGraph.vue'),
  },
  data() {
    return {
      database: '',
      tables: [],
      search: '',
      selectedTable: '',
      activeTab: 'columns',
      detail: null,
      loadingTables: false,
      loadingDetail: false,
      listError: '',
      detailError: '',
      diagramLoading: false,
      diagramError: '',
      diagram: null,
      diagramLayout: null,
    }
  },
  computed: {
    diagramVisible() {
      return this.$route.query.view === 'er'
    },
    visibleTables() {
      const term = this.search.trim().toLowerCase()
      return this.tables.filter(name => name.toLowerCase().includes(term))
    },
  },
  watch: {
    diagramVisible(visible) {
      if (visible) {
        this.loadDiagram()
      } else {
        this.resetDiagram()
        if (!this.database && !this.loadingTables) this.refreshTables()
      }
    },
  },
  created() {
    this._tableRequest = 0
    this._diagramRequest = 0
    if (this.diagramVisible) {
      this.loadDiagram()
    } else {
      this.refreshTables()
    }
  },
  beforeDestroy() {
    this._tableRequest += 1
    this._diagramRequest += 1
  },
  methods: {
    openDiagram() {
      this.$router.push({
        name: 'table-schema',
        query: { ...this.$route.query, view: 'er' },
      })
    },
    closeDiagram() {
      const query = { ...this.$route.query }
      delete query.view
      this.$router.replace({ name: 'table-schema', query })
    },
    async loadDiagram() {
      const request = ++this._diagramRequest
      this.diagramLoading = true
      this.diagramError = ''
      try {
        const [diagram, { layoutDatabaseDiagram }] = await Promise.all([
          getDatabaseDiagram(),
          import('../data/databaseDiagramLayout.js'),
        ])
        if (request === this._diagramRequest) {
          this.diagram = diagram
          this.diagramLayout = layoutDatabaseDiagram
        }
      } catch (error) {
        if (request === this._diagramRequest) this.diagramError = error.message
      } finally {
        if (request === this._diagramRequest) this.diagramLoading = false
      }
    },
    resetDiagram() {
      this._diagramRequest += 1
      this.diagramLoading = false
      this.diagramError = ''
      this.diagram = null
      this.diagramLayout = null
    },
    openDiagramTable(name) {
      const database = this.diagram.database
      this.closeDiagram()
      this.activeTab = 'columns'
      if (this.database === database && this.tables.includes(name)) {
        this.openRelatedTable(name)
      } else {
        this.refreshTables(name)
      }
    },
    async refreshTables(preferredTable = '') {
      if (this.loadingTables) return
      const request = ++this._tableRequest
      this.loadingTables = true
      this.loadingDetail = false
      this.listError = ''
      this.detailError = ''
      this.detail = null
      try {
        const { database, tables } = await listDatabaseTables()
        if (request !== this._tableRequest) return
        const nextTable = preferredTable || (database === this.database ? this.selectedTable : '')
        if (database !== this.database) this.search = ''
        this.database = database
        this.tables = tables
        this.selectedTable = tables.includes(nextTable) ? nextTable : tables[0] || ''
      } catch (error) {
        if (request !== this._tableRequest) return
        this.database = ''
        this.tables = []
        this.listError = error.message
      } finally {
        if (request === this._tableRequest) this.loadingTables = false
      }
      if (request === this._tableRequest && !this.listError && this.selectedTable) {
        this.loadTable(this.selectedTable)
      }
    },
    openRelatedTable(name) {
      if (!this.visibleTables.includes(name)) this.search = ''
      this.loadTable(name)
    },
    async loadTable(name) {
      const request = ++this._tableRequest
      this.selectedTable = name
      this.loadingDetail = true
      this.detailError = ''
      this.detail = null
      try {
        const detail = await getDatabaseTable(name)
        if (request !== this._tableRequest) return
        if (detail.database !== this.database) {
          this.detailError = '数据库连接已切换，请刷新表列表。'
          return
        }
        this.detail = detail
      } catch (error) {
        if (request === this._tableRequest) this.detailError = error.message
      } finally {
        if (request === this._tableRequest) this.loadingDetail = false
      }
    },
  },
}
</script>

<style scoped>
.schema-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 8px;
  margin: 14px 0;
  color: #52647d;
  font-size: 14px;
}

.schema-toolbar strong,
.diagram-summary strong {
  color: #14233b;
  overflow-wrap: anywhere;
}

.schema-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.schema-actions .el-button + .el-button {
  margin-left: 0;
}

.diagram-page .schema-toolbar {
  justify-content: flex-start;
}

.diagram-summary {
  margin: 0 0 12px;
  color: #52647d;
}

.diagram-retry {
  margin-top: 12px;
}

.schema-layout {
  display: grid;
  grid-template-columns: 200px minmax(0, 1fr);
  gap: 16px;
}

.table-sidebar,
.table-detail {
  min-width: 0;
  padding: 16px;
  background: #fff;
  border: 1px solid #dfe7f1;
  border-radius: 10px;
}

.table-list {
  list-style: none;
  margin: 10px 0 0;
  padding: 0;
  max-height: 450px;
  overflow-y: auto;
}

.table-option {
  width: 100%;
  text-align: left;
  background: transparent;
  border: 0;
  border-radius: 5px;
  color: #263f63;
  padding: 7px 8px;
  margin: 2px 0;
  cursor: pointer;
  overflow-wrap: anywhere;
  font: inherit;
  font-size: 13px;
}

.table-option:hover,
.table-option[aria-pressed='true'] {
  background: #e9f2ff;
  color: #174a84;
}

.table-detail h2 {
  margin: 0 0 12px;
  overflow-wrap: anywhere;
  font-size: 18px;
}

.empty-search {
  color: #52647d;
  font-size: 13px;
}

.field-table-scroll {
  overflow-x: auto;
}

.field-table {
  width: 100%;
  min-width: 570px;
  border-collapse: collapse;
  color: #263f63;
  font-size: 13px;
  text-align: left;
}

.field-table th,
.field-table td {
  padding: 9px 8px;
  border-bottom: 1px solid #e5edf6;
  overflow-wrap: anywhere;
  vertical-align: top;
}

.field-table thead {
  background: #f3f7fc;
  color: #52647d;
  white-space: nowrap;
}

.field-table tbody th {
  font-weight: 500;
}

.column-keys {
  white-space: nowrap;
}

.column-keys .el-tag + .el-tag {
  margin-left: 4px;
}

@media (max-width: 880px) {
  .schema-layout {
    grid-template-columns: minmax(0, 1fr);
  }

  .table-list {
    max-height: 160px;
  }
}
</style>
