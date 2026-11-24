<template>
  <section class="view-workspace">
    <div class="view-card view-connection">
      <label>数据库
        <select v-model="connectionId" :disabled="loadingConnections || creating">
          <option value="">{{ loadingConnections ? '正在读取连接…' : '请选择已连接的数据库' }}</option>
          <option v-for="connection in connections" :key="connection.id" :value="connection.id">
            {{ connection.database }} · {{ connection.host }}:{{ connection.port }}
          </option>
        </select>
      </label>
      <router-link v-if="!loadingConnections && !connections.length" :to="{ name: 'data-sources' }">打开数据库连接</router-link>
      <p v-if="success" class="view-success" role="status">{{ success }}</p>
      <p v-if="error" class="view-error" role="alert">{{ error }}</p>
    </div>

    <div v-if="connectionId" class="view-grid" :class="{ 'view-grid-visual': visualTab }">
      <section class="view-card view-editor" aria-label="视图配置">
        <div class="view-tabs" role="group" aria-label="构建方式">
          <button type="button" :aria-pressed="spec.mode !== 'sql' && !visualTab" @click="openBuilder">可视化工作台</button>
          <button type="button" :aria-pressed="visualTab" @click="openVisual">可视化</button>
          <button type="button" :aria-pressed="spec.mode === 'sql'" @click="switchMode('sql')">SQL 编辑</button>
        </div>

        <template v-if="spec.mode !== 'sql'">
          <label>数据处理
            <select :value="spec.mode" @change="switchMode($event.target.value)">
              <option v-for="(label, mode) in availableOperations" :key="mode" :value="mode">{{ label }}</option>
            </select>
          </label>
          <view-visual-builder v-if="visualTab" :key="connectionId + ':' + spec.mode" :spec="spec"
            :groups="sourceGroups" :metadata="metadata" :categories="categories" :loading-categories="loadingCategories"
            @source-selected="loadColumns" @categories="loadCategories" @reset-categories="resetCategories" />
          <component :is="visualTab ? 'details' : 'div'" class="view-fields">
            <summary v-if="visualTab">详细设置</summary>
            <view-join-fields v-if="spec.mode === 'join'" :spec="spec" :groups="sourceGroups" :metadata="metadata"
              @source-selected="loadColumns" />
            <view-pivot-fields v-else-if="spec.mode === 'pivot'" :spec="spec" :groups="sourceGroups" :metadata="metadata"
              :categories="categories" :loading="loadingCategories"
              @source-selected="loadColumns" @categories="loadCategories" @reset-categories="resetCategories" />
            <view-transform-fields v-else :key="spec.mode" :spec="spec" :groups="sourceGroups" :metadata="metadata"
              @source-selected="loadColumns" />
          </component>
        </template>
        <label v-else>视图查询
          <textarea v-model="spec.sql" rows="11" maxlength="24000" spellcheck="false"
            placeholder="SELECT year, quarter, consumption&#10;FROM gas_records"></textarea>
          <span class="view-note">输入一条 SELECT 或 WITH 查询。保存后可在视图列表预览数据。</span>
        </label>

        <label>名称
          <input v-model.trim="name" type="text" maxlength="64"
            :placeholder="spec.mode === 'sql' ? '输入视图名称' : '输入中间表或视图名称'">
        </label>
        <div class="view-actions">
          <el-button size="small" :loading="previewing" :disabled="!ready" @click="runPreview">
            {{ spec.mode === 'sql' ? '查看查询' : '预览结果' }}
          </el-button>
          <el-button v-if="spec.mode !== 'sql'" size="small" :disabled="!name || !currentResult || drafts.length >= maxDrafts"
            @click="keepDraft">保留为中间表</el-button>
          <el-button type="primary" size="small" :disabled="!name || !ready || creating" @click="confirmSave">保存为视图</el-button>
        </div>
        <p v-if="spec.mode !== 'sql'" class="view-note">
          先预览再保留中间表。中间表可作为下一步的数据源，最多保留 {{ maxDrafts }} 张。
        </p>
      </section>

      <div class="view-side">
        <section class="view-card">
          <h2>当前结果</h2>
          <template v-if="currentResult">
            <view-result-preview :result="result" />
            <button v-if="spec.mode !== 'sql'" type="button" class="view-copy-query" @click="editQuery">转到 SQL 编辑</button>
          </template>
          <p v-else class="view-note">{{ previewing ? '正在读取预览…' : '配置查询后可在这里查看结果。' }}</p>
        </section>

        <section class="view-card">
          <h2>中间表</h2>
          <p v-if="!drafts.length" class="view-note">已保留的中间表会出现在数据源列表中。</p>
          <ul v-else class="view-list">
            <li v-for="draft in drafts" :key="draft.id">
              <span>{{ draft.name }}</span>
              <div class="view-actions">
                <button type="button" @click="restoreDraft(draft)">载入配置</button>
                <button type="button" :aria-label="'移除 ' + draft.name" @click="removeDraft(draft)">移除</button>
              </div>
            </li>
          </ul>
        </section>

        <section class="view-card">
          <div class="view-heading">
            <h2>已保存视图</h2>
            <button type="button" :disabled="loadingCatalog" @click="loadCatalog">刷新</button>
          </div>
          <p v-if="!catalog.views.length" class="view-note">{{ loadingCatalog ? '正在读取视图…' : '当前数据库没有可见视图。' }}</p>
          <ul v-else class="view-list">
            <li v-for="view in catalog.views" :key="view">
              <span>{{ view }}</span>
              <button type="button" :disabled="loadingSaved" @click="loadSavedView(view)">查看数据</button>
            </li>
          </ul>
          <div v-if="savedResult" class="view-saved">
            <h3>{{ savedName }}</h3>
            <view-result-preview :result="savedResult" />
            <router-link :to="{ name: 'chart-showcase' }">去选择图表</router-link>
          </div>
        </section>
      </div>
    </div>

    <el-dialog title="确认保存视图" :visible.sync="confirmVisible" width="min(450px, 92vw)" append-to-body
      :close-on-click-modal="false" :close-on-press-escape="!creating" :show-close="!creating">
      <p v-if="pending" class="confirm-text">
        在数据库 <strong>{{ pending.database }}</strong> 中创建视图 <strong>{{ pending.payload.name }}</strong>。
      </p>
      <p v-if="confirmError" class="view-error" role="alert">{{ confirmError }}</p>
      <template #footer>
        <el-button :disabled="creating" @click="confirmVisible = false">取消</el-button>
        <el-button type="primary" :loading="creating" @click="saveView">确认创建</el-button>
      </template>
    </el-dialog>
  </section>
</template>

<script>
import ElButton from 'element-ui/lib/button'
import ElDialog from 'element-ui/lib/dialog'
import ViewJoinFields from '../components/views/ViewJoinFields.vue'
import ViewPivotFields from '../components/views/ViewPivotFields.vue'
import ViewResultPreview from '../components/views/ViewResultPreview.vue'
import ViewTransformFields from '../components/views/ViewTransformFields.vue'
import ViewVisualBuilder from '../components/views/ViewVisualBuilder.vue'
import {
  createDatabaseView, getChartSource, listChartSources, listDatabaseConnections, listViewCategories,
  previewSavedView, previewView,
} from '../api/database.js'
import { draftStorageKey, hasViewSelection, maxDrafts, newViewSpec, relevantDrafts, restoreViewSpec, sourcesFor,
  viewOperations, visualViewModes } from '../data/viewWorkspace.js'

import 'element-ui/lib/theme-chalk/button.css'
import 'element-ui/lib/theme-chalk/dialog.css'

const copy = value => JSON.parse(JSON.stringify(value))

export default {
  name: 'DatabaseViewsView',
  components: { ElButton, ElDialog, ViewJoinFields, ViewPivotFields, ViewResultPreview, ViewTransformFields, ViewVisualBuilder },
  data() {
    return {
      connections: [], connectionId: '', catalog: { tables: [], views: [] }, metadata: {},
      spec: newViewSpec('join'), name: '', drafts: [], maxDrafts, visual: false,
      categories: null, result: null, resultKey: '', savedName: '', savedResult: null,
      loadingConnections: true, loadingCatalog: false, loadingCategories: false, loadingSaved: false, previewing: false,
      error: '', success: '', pending: null, confirmError: '', confirmVisible: false, creating: false,
    }
  },
  computed: {
    visualTab() { return this.visual && visualViewModes.includes(this.spec.mode) },
    availableOperations() {
      return this.visualTab ? Object.fromEntries(visualViewModes.map(mode => [mode, viewOperations[mode]])) : viewOperations
    },
    sourceGroups() {
      return [
        { label: '数据表', items: this.catalog.tables.map(name => ({ id: 'db:' + name, name })) },
        { label: '视图', items: this.catalog.views.map(name => ({ id: 'db:' + name, name })) },
        { label: '中间表', items: this.drafts.map(draft => ({ id: 'draft:' + draft.id, name: draft.name })) },
      ].filter(group => group.items.length)
    },
    ready() { return Boolean(this.connectionId && hasViewSelection(this.spec)) },
    signature() { return JSON.stringify([this.connectionId, this.spec]) },
    currentResult() { return this.resultKey === this.signature && this.result },
    dependentDrafts() {
      return relevantDrafts(this.spec, this.drafts)
    },
  },
  watch: {
    connectionId() { this.resetConnection() },
  },
  created() {
    this._catalogRequest = 0
    this._categoryRequest = 0
    this._savedRequest = 0
    this.loadConnections()
  },
  methods: {
    async loadConnections() {
      try {
        this.connections = (await listDatabaseConnections()).connections
        if (this.connections.length === 1) this.connectionId = this.connections[0].id
      } catch (error) {
        this.error = error.message
      } finally {
        this.loadingConnections = false
      }
    },
    resetConnection() {
      // 每个库有自己的字段缓存、配置和中间表。
      this.switchMode(this.spec.mode, true)
      this.name = ''
      this.error = this.success = ''
      this.catalog = { tables: [], views: [] }
      this.metadata = {}
      this.savedName = ''
      this.savedResult = null
      this.loadingSaved = false
      this._savedRequest += 1
      this.drafts = []
      if (!this.connectionId) {
        this._catalogRequest += 1
        this.loadingCatalog = false
        return
      }
      try {
        const saved = JSON.parse(localStorage.getItem(draftStorageKey(this.connectionId)) || '[]')
        if (Array.isArray(saved)) this.drafts = saved.slice(0, maxDrafts)
      } catch {
        this.error = '无法读取本地中间表。'
      }
      this.drafts.forEach(draft => this.$set(this.metadata, 'draft:' + draft.id, draft.columns))
      this.loadCatalog()
    },
    async loadCatalog() {
      const request = ++this._catalogRequest
      this.loadingCatalog = true
      try {
        const catalog = await listChartSources(this.connectionId)
        if (request === this._catalogRequest) this.catalog = catalog
      } catch (error) {
        if (request === this._catalogRequest) this.error = error.message
      } finally {
        if (request === this._catalogRequest) this.loadingCatalog = false
      }
    },
    async loadColumns(source) {
      const connectionId = this.connectionId
      if (!source.startsWith('db:') || this.metadata[source]) return
      try {
        const { columns } = await getChartSource(source.slice(3), connectionId)
        if (connectionId === this.connectionId) this.$set(this.metadata, source, columns)
      } catch (error) {
        if (connectionId === this.connectionId) this.error = error.message
      }
    },
    openBuilder() {
      this.visual = false
      if (this.spec.mode === 'sql') this.switchMode('join')
    },
    openVisual() {
      this.visual = true
      if (!visualViewModes.includes(this.spec.mode)) this.switchMode('join')
    },
    switchMode(mode, force = false) {
      if (!force && mode === this.spec.mode) return
      this.spec = newViewSpec(mode)
      if (!visualViewModes.includes(mode)) this.visual = false
      this.error = ''
      this.resetCategories()
      this.result = null
    },
    editQuery() {
      const sql = this.currentResult.query
      this.switchMode('sql')
      this.spec.sql = sql
    },
    resetCategories() {
      this._categoryRequest += 1
      this.categories = null
      this.loadingCategories = false
    },
    async loadCategories() {
      const request = ++this._categoryRequest
      this.loadingCategories = true
      this.error = ''
      try {
        const result = await listViewCategories({
          connectionId: this.connectionId, source: this.spec.source, column: this.spec.category, drafts: this.dependentDrafts,
        })
        if (request === this._categoryRequest) this.categories = result
      } catch (error) {
        if (request === this._categoryRequest) this.error = error.message
      } finally {
        if (request === this._categoryRequest) this.loadingCategories = false
      }
    },
    payload() {
      return { connectionId: this.connectionId, spec: this.spec, drafts: this.dependentDrafts }
    },
    async runPreview() {
      const key = this.signature
      this.previewing = true
      this.error = ''
      try {
        const result = await previewView(this.payload())
        if (key === this.signature) {
          this.result = result
          this.resultKey = key
        }
      } catch (error) {
        if (key === this.signature) {
          this.result = null
          this.error = error.message
        }
      } finally {
        this.previewing = false
      }
    },
    keepDraft() {
      if (!this.currentResult || !this.name.trim() || this.drafts.length >= maxDrafts) return
      if (this.drafts.some(draft => draft.name.toLowerCase() === this.name.toLowerCase())) {
        this.error = '已有同名中间表，请填写新的名称。'
        return
      }
      const id = crypto.randomUUID()
      const draft = { id, name: this.name, spec: copy(this.spec), columns: this.result.columns }
      const drafts = [...this.drafts, draft]
      if (!this.storeDrafts(drafts)) return
      this.$set(this.metadata, 'draft:' + id, draft.columns)
      this.error = ''
      this.success = '已保留中间表「' + draft.name + '」。'
    },
    storeDrafts(drafts) {
      try {
        localStorage.setItem(draftStorageKey(this.connectionId), JSON.stringify(drafts))
        this.drafts = drafts
        return true
      } catch {
        this.error = '无法更新本地中间表。'
        return false
      }
    },
    removeDraft(draft) {
      const source = 'draft:' + draft.id
      if (sourcesFor(this.spec).includes(source) || this.drafts.some(item => sourcesFor(item.spec).includes(source))) {
        this.error = '当前配置或其他中间表仍在使用这张中间表。请先移除引用。'
        return
      }
      if (this.storeDrafts(this.drafts.filter(item => item.id !== draft.id))) {
        this.$delete(this.metadata, source)
        this.error = ''
        this.success = '已移除中间表「' + draft.name + '」。'
      }
    },
    restoreDraft(draft) {
      this.spec = restoreViewSpec(copy(draft.spec))
      if (!visualViewModes.includes(this.spec.mode)) this.visual = false
      this.name = draft.name
      this.result = null
      this.resetCategories()
      sourcesFor(this.spec).forEach(this.loadColumns)
    },
    confirmSave() {
      if (!this.ready || !this.name.trim()) return
      const database = this.connections.find(connection => connection.id === this.connectionId)?.database
      this.pending = { database, payload: copy({ ...this.payload(), name: this.name, confirmed: true }) }
      this.confirmError = ''
      this.confirmVisible = true
    },
    async saveView() {
      if (!this.confirmVisible || !this.pending || this.creating) return
      this.creating = true
      this.confirmError = ''
      try {
        const { name } = await createDatabaseView(this.pending.payload)
        this.confirmVisible = false
        this.success = '已创建视图「' + name + '」，可以在图表的数据来源中选择。'
        await this.loadCatalog()
      } catch (error) {
        this.confirmError = error.message
      } finally {
        this.creating = false
      }
    },
    async loadSavedView(name) {
      const request = ++this._savedRequest
      this.loadingSaved = true
      this.savedName = name
      this.savedResult = null
      this.error = ''
      try {
        const result = await previewSavedView(this.connectionId, name)
        if (request === this._savedRequest) this.savedResult = result
      } catch (error) {
        if (request === this._savedRequest) this.error = error.message
      } finally {
        if (request === this._savedRequest) this.loadingSaved = false
      }
    },
  },
}
</script>

<style src="../assets/view-workspace.css"></style>
