<template>
  <div class="view-canvas">
    <div class="canvas-toolbar">
      <p>{{ instructions }}</p>
      <label v-if="joining" class="canvas-join-type">连接方式
        <select v-model="spec.joinType">
          <option value="inner">内连接</option><option value="left">左连接</option>
        </select>
      </label>
    </div>
    <div class="canvas-workspace">
      <aside class="canvas-sources" aria-label="数据源">
        <h3>数据源</h3>
        <input v-model.trim="search" type="search" aria-label="查找数据源" placeholder="查找表、视图">
        <div class="canvas-source-list">
          <section v-for="group in filteredGroups" :key="group.label">
            <h4>{{ group.label }}</h4>
            <button v-for="source in group.items" :key="source.id" type="button" draggable="true"
              @dragstart="startDrag($event, { kind: 'source', source: source.id })" @dragend="drag = null"
              @click="clickSource(source.id)">{{ source.name }}</button>
          </section>
          <p v-if="!filteredGroups.length" class="view-note">没有找到数据源。</p>
        </div>
      </aside>

      <div ref="board" class="canvas-board" :class="{ 'canvas-joining': joining }">
        <canvas v-if="joining" ref="wires" class="canvas-wires" aria-hidden="true"></canvas>
        <view-canvas-table v-for="side in sides" :key="side" :side="side" :heading="headings[side]"
          :source="sourceNames.get(spec[side]) || ''" :fields="fields(side)"
          :selected="selected?.side === side ? selected.field.name : ''"
          :output-fields="joining ? outputs(side) : null"
          @source-drop="dropSource(side)" @remove-source="assignSource(side, '')"
          @select-field="selectField(side, $event)" @drag-field="dragField(side, $event)"
          @drag-end="drag = null" @drop-field="dropField(side, $event)" @layout="scheduleDraw"
          @toggle-output="toggleOutput(side, $event)" />
        <div v-if="!joining" class="canvas-destinations">
          <h3>{{ spec.mode === 'pivot' ? '宽表结构' : '长表结构' }}</h3>
          <div v-for="role in roles" :key="role.id" class="canvas-role"
            @dragover.prevent @drop.prevent.stop="dropRole(role.id)">
            <button type="button" :aria-label="'将选中字段放入' + role.label" @click="placeField(role.id, selected)">
              {{ role.label }}
            </button>
            <span v-if="!role.values.length" class="view-note">拖字段到这里</span>
            <button v-for="name in role.values" :key="name" type="button" class="canvas-token"
              :aria-label="'移除 ' + name" @click="removeRole(role.id, name)">{{ name }} ×</button>
          </div>
        </div>
      </div>
    </div>

    <div v-if="joining && connections.length" class="canvas-summary" aria-label="连接条件">
      <span>连接条件</span>
      <button v-for="(pair, index) in connections" :key="index" type="button"
        :aria-label="'移除连接 ' + pair.left + ' 与 ' + pair.right"
        @click="removeCondition(pair)">{{ pair.left }} = {{ pair.right }} ×</button>
    </div>
    <div v-if="pivot && spec.category" class="canvas-summary" aria-label="展开类别值">
      <button type="button" :disabled="loadingCategories" @click="$emit('categories')">{{ loadingCategories ? '正在读取…' : '读取类别值' }}</button>
      <button v-for="value in categories?.values || []" :key="value" type="button" :aria-pressed="hasValue(value)"
        :disabled="!hasValue(value) && spec.columns.length >= 16"
        @click="toggleValue(value)">{{ value || '空字符串' }}</button>
      <p v-if="categories?.truncated" class="view-note">显示前 80 个类别值。最多展开 16 列。</p>
      <p v-else-if="categories && !categories.values.length" class="view-note">这个字段没有可用的类别值。</p>
    </div>
    <p v-if="message" class="view-note" role="status">{{ message }}</p>
  </div>
</template>

<script>
import ViewCanvasTable from './ViewCanvasTable.vue'
import { addJoinOutput, addPivotValue, setJoinSource } from '../../data/viewWorkspace.js'
import { connectCanvasFields, placeCanvasField, resetCanvasSource } from '../../data/viewCanvas.js'
import { drawViewConnections } from '../../data/viewCanvasLines.js'

const headings = { left: '左表', right: '右表', source: '来源表' }

export default {
  name: 'ViewVisualBuilder',
  components: { ViewCanvasTable },
  props: {
    spec: { type: Object, required: true },
    groups: { type: Array, required: true },
    metadata: { type: Object, required: true },
    categories: { type: Object, default: null },
    loadingCategories: Boolean,
  },
  data: () => ({ headings, drag: null, selected: null, search: '', message: '' }),
  computed: {
    joining() { return this.spec.mode === 'join' },
    pivot() { return this.spec.mode === 'pivot' },
    sides() { return this.joining ? ['left', 'right'] : ['source'] },
    instructions() {
      if (this.joining) return '将两个数据源拖进左右槽位。拖一个字段到另一张表的字段上建立连接，也可以依次点选两个字段。用「＋」选择输出列。'
      return '将数据源拖进画布，再拖动字段到右侧。也可以先点字段，再点右侧的目标区域。'
    },
    sourceNames() { return new Map(this.groups.flatMap(group => group.items.map(item => [item.id, item.name]))) },
    filteredGroups() {
      const query = this.search.toLowerCase()
      return this.groups.map(group => ({
        label: group.label, items: group.items.filter(item => item.name.toLowerCase().includes(query)),
      })).filter(group => group.items.length)
    },
    connections() { return this.joining ? this.spec.conditions.filter(item => item.left && item.right) : [] },
    roles() {
      if (this.pivot) return [
        { id: 'row', label: '行字段', values: this.spec.row ? [this.spec.row] : [] },
        { id: 'category', label: '列类别字段', values: this.spec.category ? [this.spec.category] : [] },
        ...(this.spec.aggregation === 'count' ? [] : [
          { id: 'metric', label: '数值字段', values: this.spec.metric ? [this.spec.metric] : [] },
        ]),
      ]
      return [
        { id: 'keys', label: '保留字段', values: this.spec.keys },
        { id: 'columns', label: '展开字段', values: this.spec.columns.map(column => column.name) },
      ]
    },
  },
  watch: {
    connections: { handler: 'scheduleDraw', deep: true },
    metadata: { handler: 'scheduleDraw', deep: true },
  },
  mounted() {
    if (typeof ResizeObserver === 'function') {
      this._resize = new ResizeObserver(() => this.scheduleDraw())
      this._resize.observe(this.$refs.board)
    }
    this.scheduleDraw()
  },
  beforeDestroy() {
    this._resize?.disconnect()
    cancelAnimationFrame(this._frame)
  },
  methods: {
    fields(side) { return this.metadata[this.spec[side]] || [] },
    outputs(side) { return this.spec.columns.filter(column => column.side === side).map(column => column.name) },
    startDrag(event, item) {
      this.drag = item
      this.message = ''
      event.dataTransfer.effectAllowed = 'copy'
      event.dataTransfer.setData('text/plain', item.source || item.field.name)
    },
    dragField(side, { event, field }) { this.startDrag(event, { kind: 'field', side, field }) },
    clickSource(source) {
      if (!this.joining) this.assignSource('source', source)
      else if (!this.spec.left) this.assignSource('left', source)
      else if (!this.spec.right) this.assignSource('right', source)
      else this.message = '两个槽位已有数据源。可将表拖到指定槽位替换，或先移除一张卡片。'
    },
    dropSource(side) {
      if (this.drag?.kind === 'source') this.assignSource(side, this.drag.source)
      this.drag = null
    },
    assignSource(side, source) {
      if (this.spec[side] === source) return
      this.selected = null
      this.message = ''
      if (this.joining) setJoinSource(this.spec, side, source)
      else {
        resetCanvasSource(this.spec, source)
        if (this.pivot) this.$emit('reset-categories')
      }
      if (source) this.$emit('source-selected', source)
      this.scheduleDraw()
    },
    selectField(side, field) {
      this.message = ''
      if (this.joining && this.selected && this.selected.side !== side) {
        this.connect(this.selected, { side, field })
      } else {
        this.selected = { side, field }
      }
    },
    dropField(side, field) {
      if (this.drag?.kind === 'source') this.dropSource(side)
      else if (this.joining && this.drag?.kind === 'field') this.connect(this.drag, { side, field })
      this.drag = null
    },
    connect(from, to) {
      if (from.side === to.side) {
        this.message = '请将字段拖到另一张表。'
        return
      }
      this.message = connectCanvasFields(this.spec, from, to)
      this.selected = null
    },
    toggleOutput(side, name) {
      const index = this.spec.columns.findIndex(column => column.side === side && column.name === name)
      if (index >= 0) this.spec.columns.splice(index, 1)
      else if (this.spec.columns.length < 64) addJoinOutput(this.spec, side, name)
      else this.message = '最多保留 64 个输出字段。'
    },
    removeCondition(pair) {
      this.spec.conditions = this.connections.filter(item => item !== pair)
      if (!this.spec.conditions.length) this.spec.conditions.push({ left: '', right: '' })
    },
    dropRole(role) {
      if (this.drag?.kind === 'field') this.placeField(role, this.drag)
      this.drag = null
    },
    placeField(role, item) {
      if (!item) {
        this.message = '请先选择一个字段，或把字段直接拖到这里。'
        return
      }
      const oldCategory = this.spec.category
      this.message = placeCanvasField(this.spec, role, item.field)
      if (this.pivot && oldCategory !== this.spec.category) {
        this.spec.columns = []
        this.$emit('reset-categories')
        this.$emit('categories')
      }
      if (!this.message) this.selected = null
    },
    removeRole(role, name) {
      if (this.pivot) {
        this.spec[role] = ''
        if (role === 'category') {
          this.spec.columns = []
          this.$emit('reset-categories')
        }
      } else if (role === 'keys') {
        this.spec.keys = this.spec.keys.filter(key => key !== name)
      } else {
        this.spec.columns = this.spec.columns.filter(column => column.name !== name)
      }
    },
    hasValue(value) { return this.spec.columns.some(column => column.value === value) },
    toggleValue(value) {
      if (this.hasValue(value)) this.spec.columns = this.spec.columns.filter(column => column.value !== value)
      else addPivotValue(this.spec, value)
    },
    scheduleDraw() {
      if (!this.joining) return
      cancelAnimationFrame(this._frame)
      this._frame = requestAnimationFrame(() => {
        const { board, wires } = this.$refs
        if (board && wires) drawViewConnections(board, wires, this.connections)
      })
    },
  },
}
</script>

<style src="../../assets/view-canvas.css"></style>
