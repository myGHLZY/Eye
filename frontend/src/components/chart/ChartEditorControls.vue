<template>
  <aside class="editor-controls">
    <div class="editor-tabs" role="group" aria-label="编辑面板">
      <button type="button" :aria-pressed="panel === 'data'" @click="panel = 'data'">数据来源</button>
      <button type="button" :aria-pressed="panel === 'style'" @click="panel = 'style'">图表样式</button>
    </div>
    <section v-show="panel === 'data'" class="control-panel" aria-label="数据来源"><slot name="data" /></section>
    <section v-show="panel === 'style'" class="control-panel style-panel" aria-label="图表样式"><slot name="style" /></section>
  </aside>
</template>

<script>
export default {
  name: 'ChartEditorControls',
  data() {
    return { panel: 'data' }
  },
}
</script>

<style scoped>
.editor-controls { display: grid; gap: 14px; align-self: start; min-width: 0; }
.editor-tabs { display: flex; gap: 4px; padding: 4px; background: #e8eef7; border-radius: 8px; }
.editor-tabs button {
  flex: 1; padding: 7px 8px; border: 0; border-radius: 5px; background: transparent;
  color: #435774; font: inherit; cursor: pointer;
}
.editor-tabs button[aria-pressed='true'] { background: #fff; color: #15243b; font-weight: 600; }
.control-panel {
  display: grid; gap: 11px; min-width: 0; padding: 16px;
  background: #fff; border: 1px solid #dfe7f1; border-radius: 10px;
}
.style-panel { padding: 12px; }
</style>
