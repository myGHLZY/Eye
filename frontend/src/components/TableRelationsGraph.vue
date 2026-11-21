<template>
  <section :class="{ overview }" aria-label="外键关系图">
    <div class="graph-toolbar">
      <span v-if="overview">PK 主键 · FK 外键 · 连线标注外键字段名</span>
      <span v-else>连线由外键指向被引用字段，点击同库表可查看其关系。</span>
      <el-button-group>
        <el-button size="mini" aria-label="缩小关系图" @click="zoom(-0.15)">缩小</el-button>
        <el-button size="mini" aria-label="放大关系图" @click="zoom(0.15)">放大</el-button>
        <el-button size="mini" @click="fit">适应画布</el-button>
      </el-button-group>
    </div>
    <div class="graph-frame">
      <div ref="canvas" class="graph-canvas" aria-label="数据表与外键连线"></div>
    </div>

    <h3 class="relation-heading">外键约束</h3>
    <p v-if="!detail.relations.length" class="no-relations">当前数据库中没有可见的库内外键关系。</p>
    <ul v-else class="relation-list">
      <li v-for="(relation, index) in detail.relations" :key="index">
        <button
          type="button"
          class="relation-button"
          :aria-pressed="activeRelation === index ? 'true' : 'false'"
          @click="selectRelation(index)"
        >
          <strong>{{ relation.name }}</strong>
          <span v-for="pair in relation.columns" :key="pair.source" class="relation-pair">
            {{ columnLabel(relation.source, pair.source) }} → {{ columnLabel(relation.target, pair.target) }}
          </span>
        </button>
      </li>
    </ul>
  </section>
</template>

<script>
import { Graph } from '@antv/x6'
import ElButton from 'element-ui/lib/button'
import ElButtonGroup from 'element-ui/lib/button-group'

import '@antv/x6/dist/index.css'
import 'element-ui/lib/theme-chalk/button.css'
import 'element-ui/lib/theme-chalk/button-group.css'

const detailNodeWidth = 224
const overviewNodeWidth = 352
const headerHeight = 34
const rowHeight = 24
const horizontalGap = 130
const verticalGap = 32
const edgeColor = '#7e98b7'
const activeEdgeColor = '#176dd1'
const fieldBaseline = index => headerHeight + rowHeight * (index + 0.5)
const tableKey = ({ schema, table }) => JSON.stringify([schema, table])
const portId = (index, side) => `field-${index}-${side}`

function shorten(label, limit) {
  let units = 0
  let prefix = ''
  for (const character of label) {
    units += character.codePointAt(0) < 128 ? 1 : 2
    if (units >= limit) return prefix + '…'
    prefix += character
  }
  return label
}

function getGraphData(detail, layoutDatabase) {
  const overview = Boolean(layoutDatabase)
  const tables = new Map()
  const width = overview ? overviewNodeWidth : detailNodeWidth

  function addTable(identity, group) {
    const key = tableKey(identity)
    if (!tables.has(key)) {
      tables.set(key, {
        ...identity, group, id: `table-${tables.size}`, width, fields: new Map(), connected: new Set(),
      })
    }
    return tables.get(key)
  }

  function addColumns(table, columns) {
    const fields = new Map(columns.map(column => [column.name, {
      key: [column.primaryKey && 'PK', column.foreignKey && 'FK'].filter(Boolean).join('/'),
      type: overview ? column.type : '',
    }]))
    for (const [field, value] of table.fields) {
      if (!fields.has(field)) fields.set(field, value)
    }
    table.fields = fields
  }

  let selected
  if (overview) {
    for (const table of detail.tables) {
      addColumns(addTable({ schema: detail.database, table: table.name }), table.columns)
    }
  } else {
    selected = addTable({ schema: detail.database, table: detail.table }, 'center')
  }

  const links = detail.relations.map(relation => {
    const source = addTable(relation.source, 'left')
    const target = addTable(relation.target, 'right')
    for (const { source: sourceField, target: targetField } of relation.columns) {
      if (!overview || !source.fields.has(sourceField)) source.fields.set(sourceField, { key: 'FK' })
      if (!target.fields.has(targetField)) target.fields.set(targetField, { key: '' })
      source.connected.add(sourceField)
      target.connected.add(targetField)
    }
    return [source, target]
  })

  if (selected) {
    addColumns(selected, detail.columns.filter(
      column => column.primaryKey || column.foreignKey || selected.connected.has(column.name),
    ))
  }

  const allTables = [...tables.values()]
  for (const table of allTables) table.height = headerHeight + rowHeight * table.fields.size
  if (overview) {
    const positions = layoutDatabase(allTables, links)
    for (const table of allTables) Object.assign(table, positions.get(table.id))
  } else {
    layoutTableNeighborhood(allTables)
  }

  const nodes = allTables.map(table => makeNode(table, detail.database, table === selected, overview))

  const edges = detail.relations.flatMap((relation, index) => {
    const [source, target] = links[index]
    const sameTable = source === target
    const sourceSide = source.x <= target.x ? 'right' : 'left'
    const targetSide = sameTable ? 'right' : sourceSide === 'right' ? 'left' : 'right'

    return relation.columns.map((pair, pairIndex) => {
      const sourceRow = source.fieldRows.get(pair.source)
      const targetRow = target.fieldRows.get(pair.target)
      const config = {
        id: `edge-${index}-${pairIndex}`,
        zIndex: 0,
        source: { cell: source.id, port: portId(sourceRow, sourceSide) },
        target: { cell: target.id, port: portId(targetRow, targetSide) },
        data: { relationIndex: index },
        attrs: {
          line: { stroke: edgeColor, strokeWidth: 1.6, targetMarker: { name: 'classic', size: 7 } },
        },
        connector: { name: 'rounded', args: { radius: 6 } },
        labels: [{
          attrs: {
            label: {
              text: shorten(pair.source, 24),
              fill: '#294866',
              fontSize: 11,
              fontFamily: 'monospace',
              pointerEvents: 'none',
            },
            body: {
              fill: '#ffffff',
              stroke: '#d8e3f2',
              strokeWidth: 1,
              refWidth: '100%',
              refWidth2: 8,
              refHeight: '100%',
              refHeight2: 5,
              refX: -4,
              refY: -2.5,
            },
          },
          position: { distance: 0.42 + Math.min(pairIndex, 4) * 0.055, offset: sourceSide === 'right' ? -10 : 10 },
        }],
      }
      if (sameTable) {
        const outerX = source.x + source.width + 28 + pairIndex * 8
        const startY = source.y + fieldBaseline(sourceRow)
        const endY = target.y + fieldBaseline(targetRow)
        config.vertices = startY === endY
          ? [{ x: outerX, y: startY - 12 }, { x: outerX, y: startY + 12 }]
          : [{ x: outerX, y: startY }, { x: outerX, y: endY }]
      } else {
        config.router = {
          name: 'manhattan',
          args: { startDirections: [sourceSide], endDirections: [targetSide], padding: 12 },
        }
      }
      return config
    })
  })
  return { nodes, edges }
}

function layoutTableNeighborhood(tables) {
  const groups = ['left', 'center', 'right'].map(group => tables.filter(table => table.group === group))
  const groupHeight = group => group.reduce((height, table) => height + table.height + verticalGap, 0) - verticalGap
  const canvasHeight = Math.max(...groups.map(groupHeight))
  groups.forEach((group, column) => {
    let y = (canvasHeight - groupHeight(group)) / 2
    for (const table of group) {
      table.x = column * (table.width + horizontalGap)
      table.y = y
      y += table.height + verticalGap
    }
  })
}

function makeNode(table, database, selected, overview) {
  const { width, height } = table
  const label = table.schema === database ? table.table : `${table.schema}.${table.table}`
  const markup = [
    { tagName: 'rect', selector: 'body' },
    { tagName: 'rect', selector: 'header' },
    { tagName: 'text', selector: 'title' },
  ]
  const attrs = {
    body: {
      width, height, rx: 7, fill: '#ffffff',
      stroke: selected ? '#176dd1' : '#aec3dc', strokeWidth: selected ? 2 : 1,
    },
    header: {
      x: 1, y: 1, width: width - 2, height: headerHeight - 1, rx: 6,
      fill: selected || overview ? '#e3efff' : '#eef3f9',
    },
    title: {
      text: shorten(label, overview ? 36 : 25), x: 12, y: headerHeight / 2, textVerticalAnchor: 'middle',
      fontSize: 13, fontWeight: 600, fontFamily: 'monospace', fill: '#14233b',
    },
  }
  const ports = []
  table.fieldRows = new Map()
  let index = 0

  for (const [field, { key, type }] of table.fields) {
    const y = fieldBaseline(index)
    const name = `name${index}`
    const badge = `key${index}`
    table.fieldRows.set(field, index)
    markup.push({ tagName: 'text', selector: name }, { tagName: 'text', selector: badge })
    attrs[name] = {
      text: shorten(field, 19), x: 12, y, textVerticalAnchor: 'middle',
      fontSize: 12, fontFamily: 'monospace', fill: '#263f63',
    }
    attrs[badge] = {
      text: key, x: width - 10, y, textAnchor: 'end', textVerticalAnchor: 'middle',
      fontSize: 10, fontWeight: 600, fill: '#235a9f',
    }
    if (overview) {
      const typeSelector = `type${index}`
      markup.push({ tagName: 'text', selector: typeSelector })
      attrs[typeSelector] = {
        text: shorten(type || '', 21), x: 155, y, textVerticalAnchor: 'middle',
        fontSize: 12, fontFamily: 'monospace', fill: '#52647d',
      }
    }
    if (table.connected.has(field)) {
      ports.push(
        { id: portId(index, 'left'), group: 'fields', args: { x: 0, y } },
        { id: portId(index, 'right'), group: 'fields', args: { x: '100%', y } },
      )
    }
    index += 1
  }

  return {
    id: table.id,
    shape: 'rect',
    x: table.x,
    y: table.y,
    width,
    height,
    zIndex: 2,
    markup,
    attrs,
    ports: {
      groups: {
        fields: {
          position: 'absolute',
          attrs: { circle: { r: 2, fill: '#7e98b7', stroke: 'none', magnet: false } },
        },
      },
      items: ports,
    },
    data: { schema: table.schema, table: table.table },
  }
}

export default {
  name: 'TableRelationsGraph',
  components: { ElButton, ElButtonGroup },
  props: {
    detail: { type: Object, required: true },
    layoutDatabase: { type: Function, default: null },
  },
  data() {
    return { activeRelation: null }
  },
  computed: {
    overview() {
      return Boolean(this.layoutDatabase)
    },
  },
  mounted() {
    this._graph = new Graph({
      container: this.$refs.canvas,
      autoResize: true,
      background: { color: '#f8faff' },
      grid: { size: 18, visible: true, args: { color: '#d8e3f2', thickness: 1 } },
      panning: { enabled: true },
      mousewheel: { enabled: true, modifiers: ['ctrl', 'meta'] },
      scaling: { min: 0.1, max: 2 },
      interacting: { nodeMovable: true, edgeMovable: false, magnetConnectable: false },
    })
    this._graph.fromJSON(getGraphData(this.detail, this.layoutDatabase))
    this._graph.on('edge:click', ({ edge }) => this.selectRelation(edge.getData().relationIndex))
    this._graph.on('node:click', ({ node }) => {
      const { schema, table } = node.getData()
      if (schema === this.detail.database && table !== this.detail.table) {
        this.$emit('select-table', table)
      }
    })
    this.fit()
  },
  beforeDestroy() {
    this._graph?.dispose()
  },
  methods: {
    columnLabel({ schema, table }, column) {
      return schema === this.detail.database ? `${table}.${column}` : `${schema}.${table}.${column}`
    },
    selectRelation(index) {
      this.activeRelation = this.activeRelation === index ? null : index
      for (const edge of this._graph.getEdges()) {
        const selected = edge.getData().relationIndex === this.activeRelation
        edge.setAttrs({ line: { stroke: selected ? activeEdgeColor : edgeColor, strokeWidth: selected ? 2.7 : 1.6 } })
        edge.setZIndex(selected ? 1 : 0)
      }
    },
    zoom(step) {
      this._graph.zoom(step)
    },
    fit() {
      this._graph.zoomToFit({ padding: 24, maxScale: 1 })
    },
  },
}
</script>

<style scoped>
.graph-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 10px;
  color: #52647d;
  font-size: 13px;
}

.graph-frame {
  height: 380px;
  overflow: hidden;
  border: 1px solid #dfe7f1;
  border-radius: 8px;
}

.overview .graph-frame {
  height: 70vh;
  min-height: 320px;
}

.no-relations {
  color: #52647d;
  font-size: 13px;
}

.graph-canvas {
  width: 100%;
  height: 100%;
}

.relation-heading {
  margin: 16px 0 6px;
  font-size: 14px;
}

.relation-list {
  margin: 0;
  padding: 0;
  list-style: none;
}

.relation-button {
  display: block;
  width: 100%;
  padding: 7px 9px;
  background: transparent;
  border: 0;
  border-radius: 6px;
  color: #263f63;
  text-align: left;
  font: inherit;
  font-size: 13px;
  cursor: pointer;
}

.relation-button:hover,
.relation-button[aria-pressed='true'] {
  background: #e9f2ff;
}

.relation-pair {
  display: block;
  margin-top: 3px;
  overflow-wrap: anywhere;
}
</style>
