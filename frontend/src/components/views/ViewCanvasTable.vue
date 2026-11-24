<template>
  <section class="canvas-table" :class="{ 'table-empty': !source }" :aria-label="heading"
    @dragover.prevent @drop.prevent.stop="$emit('source-drop')">
    <header class="canvas-table-header">
      <div><span>{{ heading }}</span><strong v-if="source">{{ source }}</strong></div>
      <button v-if="source" type="button" :aria-label="'移除 ' + source" @click="$emit('remove-source')">×</button>
    </header>
    <p v-if="!source" class="canvas-empty">从数据源拖入表，或点击表名添加</p>
    <p v-else-if="!fields.length" class="canvas-empty">正在读取字段…</p>
    <ul v-else class="canvas-column-list" @scroll.passive="$emit('layout')">
      <li v-for="field in fields" :key="field.name" class="canvas-column">
        <button type="button" draggable="true" class="canvas-field" :data-graph-column="field.name" :data-side="side"
          :aria-pressed="selected === field.name" @click="$emit('select-field', field)"
          @dragstart="$emit('drag-field', { event: $event, field })" @dragend="$emit('drag-end')"
          @dragover.prevent @drop.prevent.stop="$emit('drop-field', field)">
          <span>{{ field.name }}</span><small>{{ field.type }}</small>
        </button>
        <button v-if="outputFields" type="button" class="canvas-output-button"
          :aria-label="'切换输出字段 ' + field.name" :aria-pressed="outputFields.includes(field.name)"
          @click="$emit('toggle-output', field.name)">{{ outputFields.includes(field.name) ? '✓' : '+' }}</button>
      </li>
    </ul>
  </section>
</template>

<script>
export default {
  name: 'ViewCanvasTable',
  props: {
    side: { type: String, required: true },
    heading: { type: String, required: true },
    source: { type: String, default: '' },
    fields: { type: Array, required: true },
    selected: { type: String, default: '' },
    outputFields: { type: Array, default: null },
  },
}
</script>
