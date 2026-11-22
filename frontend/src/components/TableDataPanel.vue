<template>
  <section class="records" aria-label="表数据">
    <div class="records-heading">
      <h3>表数据</h3>
      <div class="records-actions">
        <el-button size="small" :disabled="!!busy" :loading="loading" @click="loadRows()">刷新数据</el-button>
        <el-button
          type="primary"
          size="small"
          icon="el-icon-plus"
          :disabled="!ready || !!busy || !!creationBlock"
          @click="openEditor()"
        >新增记录</el-button>
      </div>
    </div>

    <form v-if="columns.length" class="records-filter" @submit.prevent="applyFilter">
      <el-select
        v-model="filterColumn"
        size="small"
        placeholder="按字段筛选"
        aria-label="筛选字段"
        clearable
        @change="onFilterColumnChange"
      >
        <el-option v-for="column in filterColumns" :key="column.name" :label="column.name" :value="column.name" />
      </el-select>
      <el-input
        v-model="filterValue"
        size="small"
        class="filter-value"
        :placeholder="filterPlaceholder"
        aria-label="筛选值"
        :disabled="!selectedFilter || filterNull"
      />
      <el-checkbox v-if="selectedFilter && selectedFilter.nullable" v-model="filterNull">仅查 NULL</el-checkbox>
      <el-button size="small" native-type="submit" :disabled="!filterColumn || loading || !!busy">查询</el-button>
      <el-button size="small" :disabled="(!filterColumn && !appliedFilter.filterColumn) || !!busy" @click="clearFilter">
        清除筛选
      </el-button>
    </form>

    <el-alert v-if="readError" :title="readError" type="error" :closable="false" show-icon />
    <el-alert v-if="mutationError && !editor" :title="mutationError" type="error" :closable="false" show-icon />
    <p v-if="mutationNotice" class="records-success" role="status">{{ mutationNotice }}</p>
    <p v-if="loading" class="records-loading" role="status">正在读取记录…</p>
    <p v-if="creationBlock" class="records-note">字段「{{ creationBlock.name }}」为必填项，当前类型暂不支持写入。</p>
    <p v-if="columns.length && !canChangeRows" class="records-note">当前表没有可用于定位记录的主键，不能编辑或删除单条记录。</p>

    <template v-if="columns.length">
      <div class="records-scroll">
        <table class="records-table" aria-label="表记录">
          <thead>
            <tr>
              <th v-for="column in columns" :key="column.name" scope="col">{{ column.name }}</th>
              <th v-if="canChangeRows" scope="col" class="row-actions">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(row, index) in rows" :key="index">
              <td v-for="column in columns" :key="column.name">
                <span v-if="row[column.name] === null" class="null-value">NULL</span>
                <span v-else-if="row[column.name] === ''" class="null-value">空字符串</span>
                <span v-else class="cell-value" :title="String(row[column.name])">{{ row[column.name] }}</span>
              </td>
              <td v-if="canChangeRows" class="row-actions">
                <el-button type="text" size="small" :disabled="!ready || !!busy || !canEdit" @click="openEditor(row)">编辑</el-button>
                <el-button type="text" size="small" class="row-delete" :disabled="!ready || !!busy" @click="removeRow(row)">删除</el-button>
              </td>
            </tr>
            <tr v-if="!rows.length && !loading">
              <td :colspan="columns.length + Number(canChangeRows)" class="records-empty">没有符合条件的记录</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div v-if="!readError" class="records-footer">
        <el-pagination
          :current-page="page"
          :page-size="pageSize"
          :page-sizes="[10, 20, 50, 100]"
          :pager-count="5"
          :total="total"
          :disabled="loading || !!busy"
          layout="total, sizes, prev, pager, next"
          @size-change="changePageSize"
          @current-change="changePage"
        />
      </div>
    </template>

    <table-row-dialog
      v-if="editor"
      :columns="columns"
      :row="editor.row"
      :saving="busy === 'save'"
      :error="mutationError"
      @cancel="closeEditor"
      @save="saveRow"
    />
  </section>
</template>

<script>
import ElAlert from 'element-ui/lib/alert'
import ElButton from 'element-ui/lib/button'
import ElCheckbox from 'element-ui/lib/checkbox'
import ElInput from 'element-ui/lib/input'
import MessageBox from 'element-ui/lib/message-box'
import ElOption from 'element-ui/lib/option'
import ElPagination from 'element-ui/lib/pagination'
import ElSelect from 'element-ui/lib/select'
import { createTableRow, deleteTableRow, listTableRows, updateTableRow } from '../api/database.js'
import TableRowDialog from './TableRowDialog.vue'

import 'element-ui/lib/theme-chalk/alert.css'
import 'element-ui/lib/theme-chalk/button.css'
import 'element-ui/lib/theme-chalk/checkbox.css'
import 'element-ui/lib/theme-chalk/input.css'
import 'element-ui/lib/theme-chalk/message-box.css'
import 'element-ui/lib/theme-chalk/option.css'
import 'element-ui/lib/theme-chalk/pagination.css'
import 'element-ui/lib/theme-chalk/select.css'

export default {
  name: 'TableDataPanel',
  components: {
    ElAlert, ElButton, ElCheckbox, ElInput, ElOption, ElPagination, ElSelect, TableRowDialog,
  },
  props: {
    connectionId: { type: String, required: true },
    name: { type: String, required: true },
  },
  data() {
    return {
      columns: [],
      primaryKey: [],
      canChangeRows: false,
      rows: [],
      page: 1,
      pageSize: 20,
      total: 0,
      filterColumn: '',
      filterValue: '',
      filterNull: false,
      appliedFilter: {},
      loading: false,
      readError: '',
      mutationError: '',
      mutationNotice: '',
      busy: '',
      editor: null,
    }
  },
  computed: {
    ready() {
      return this.columns.length > 0 && !this.loading && !this.readError
    },
    canEdit() {
      return this.columns.some(column => column.editable)
    },
    creationBlock() {
      return this.columns.find(column => column.required && !column.insertable)
    },
    filterColumns() {
      return this.columns.filter(column => column.filterable)
    },
    selectedFilter() {
      return this.filterColumns.find(column => column.name === this.filterColumn)
    },
    filterPlaceholder() {
      return this.selectedFilter?.kind === 'binary' ? '输入十六进制数值' : '输入要精确匹配的值'
    },
  },
  created() {
    this._readRequest = 0
    this._leaving = false
    this.loadRows()
  },
  beforeDestroy() {
    this._leaving = true
    this._readRequest += 1
  },
  methods: {
    async loadRows(page = this.page) {
      const request = ++this._readRequest
      this.loading = true
      this.readError = ''
      try {
        const result = await listTableRows(this.connectionId, this.name, {
          page,
          pageSize: this.pageSize,
          ...this.appliedFilter,
        })
        if (request !== this._readRequest) return
        this.columns = result.columns
        this.primaryKey = result.primaryKey
        this.canChangeRows = result.canChangeRows
        this.rows = result.rows.map(row => Object.freeze(row))
        this.page = result.page
        this.total = result.total
      } catch (error) {
        if (request === this._readRequest) this.readError = error.message
      } finally {
        if (request === this._readRequest) this.loading = false
      }
    },
    onFilterColumnChange() {
      this.filterValue = ''
      this.filterNull = false
    },
    applyFilter() {
      if (!this.filterColumn || this.loading || this.busy) return
      this.appliedFilter = {
        filterColumn: this.filterColumn,
        ...(this.filterNull ? { filterNull: '1' } : { filterValue: this.filterValue }),
      }
      this.mutationError = ''
      this.mutationNotice = ''
      this.loadRows(1)
    },
    clearFilter() {
      this.filterColumn = ''
      this.onFilterColumnChange()
      this.appliedFilter = {}
      this.mutationError = ''
      this.mutationNotice = ''
      this.loadRows(1)
    },
    changePage(page) {
      if (page !== this.page && !this.loading && !this.busy) this.loadRows(page)
    },
    changePageSize(size) {
      if (size === this.pageSize || this.loading || this.busy) return
      this.pageSize = size
      this.loadRows(1)
    },
    openEditor(row = null) {
      this.mutationError = ''
      this.mutationNotice = ''
      this.editor = { row }
    },
    closeEditor() {
      this.editor = null
      this.mutationError = ''
    },
    rowKey(row) {
      return Object.fromEntries(this.primaryKey.map(name => [name, row[name]]))
    },
    async saveRow(values) {
      if (this.busy) return
      const { row } = this.editor
      this.busy = 'save'
      this.mutationError = ''
      try {
        if (row) {
          await updateTableRow(this.connectionId, this.name, this.rowKey(row), values)
        } else {
          await createTableRow(this.connectionId, this.name, values)
        }
        if (!this._leaving) {
          this.closeEditor()
          this.mutationNotice = row ? '记录已更新。' : '记录已新增。'
          await this.loadRows()
        }
      } catch (error) {
        if (!this._leaving) this.mutationError = error.message
      } finally {
        if (!this._leaving) this.busy = ''
      }
    },
    async removeRow(row) {
      if (this.busy) return
      this.busy = 'delete'
      this.mutationError = ''
      this.mutationNotice = ''
      const key = this.rowKey(row)
      const label = this.primaryKey.map(name => `${name} = ${key[name]}`).join('，')
      try {
        await MessageBox.confirm(`确定删除这条记录？（${label}）`, '删除记录', {
          type: 'warning',
          confirmButtonText: '确认删除',
          cancelButtonText: '取消',
        })
        if (this._leaving) return
        await deleteTableRow(this.connectionId, this.name, key)
        if (!this._leaving) {
          this.mutationNotice = '记录已删除。'
          await this.loadRows()
        }
      } catch (error) {
        if (!this._leaving && error instanceof Error) this.mutationError = error.message
      } finally {
        if (!this._leaving) this.busy = ''
      }
    },
  },
}
</script>

<style scoped>
.records {
  margin-top: 24px;
  padding-top: 16px;
  border-top: 1px solid #e5edf6;
}

.records-heading,
.records-actions,
.records-filter {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}

.records-heading {
  justify-content: space-between;
  margin-bottom: 12px;
}

.records-heading h3 {
  margin: 0;
  font-size: 16px;
  color: #14233b;
}

.records-filter {
  margin-bottom: 12px;
}

.records-filter .el-select,
.filter-value {
  width: 180px;
}

.records .el-button + .el-button {
  margin-left: 0;
}

.records .el-alert {
  margin-bottom: 10px;
}

.records-loading,
.records-note,
.null-value {
  color: #62758e;
  font-size: 13px;
}

.records-scroll {
  max-height: 460px;
  overflow: auto;
  border: 1px solid #dfe7f1;
  border-radius: 6px;
}

.records-table {
  width: 100%;
  border-spacing: 0;
  color: #263f63;
  font-size: 13px;
  text-align: left;
}

.records-table th,
.records-table td {
  min-width: 104px;
  padding: 8px 10px;
  border-bottom: 1px solid #e5edf6;
}

.records-table th {
  position: sticky;
  top: 0;
  z-index: 1;
  background: #f3f7fc;
  white-space: nowrap;
}

.records-table .row-actions {
  position: sticky;
  right: 0;
  min-width: 76px;
  width: 76px;
  border-left: 1px solid #e5edf6;
  white-space: nowrap;
}

.records-table th.row-actions {
  z-index: 2;
}

.records-table td.row-actions {
  background: #fff;
}

.records-table .row-actions .el-button {
  padding: 1px 0;
}

.cell-value {
  display: block;
  max-width: 280px;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}

.records-empty {
  color: #62758e;
  text-align: center;
}

.records .el-button + .row-delete {
  margin-left: 10px;
  color: #c9363e;
}

.records-success {
  color: #257044;
  font-size: 13px;
}

.records-footer {
  overflow-x: auto;
  margin-top: 12px;
}
</style>
