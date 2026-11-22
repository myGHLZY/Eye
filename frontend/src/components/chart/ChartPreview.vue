<template>
  <section class="preview" aria-label="图表预览" :aria-busy="busy">
    <header>
      <h2>图表预览</h2>
      <span v-if="busy" role="status">正在更新…</span>
      <a v-else-if="url" :href="url" :download="filename">下载 PNG</a>
    </header>
    <p v-if="error" role="alert" class="preview-error">{{ error }}</p>
    <img v-if="url" :src="url" :alt="title || '图表预览'">
    <div v-else class="preview-empty">{{ busy ? '正在生成图表' : emptyMessage }}</div>
    <slot />
  </section>
</template>

<script>
export default {
  name: 'ChartPreview',
  props: {
    url: { type: String, default: '' },
    title: { type: String, default: '' },
    filename: { type: String, default: 'chart.png' },
    busy: Boolean,
    error: { type: String, default: '' },
    emptyMessage: { type: String, default: '选择数据以生成图表。' },
  },
}
</script>

<style scoped>
.preview { min-width: 0; align-self: start; }
header { display: flex; justify-content: space-between; gap: 10px; align-items: center; margin-bottom: 12px; }
h2 { margin: 0; color: #15243b; font-size: 17px; }
a { color: #235a9f; font-weight: 600; }
span { color: #52647d; }
img { display: block; width: 100%; height: auto; }
.preview-empty {
  display: grid;
  min-height: clamp(160px, 34vw, 330px);
  place-items: center;
  padding: 12px;
  border: 1px dashed #ccd9eb;
  border-radius: 7px;
  text-align: center;
  color: #52647d;
  background: #f8faff;
}
.preview-error { color: #a12629; margin: 0 0 10px; }
</style>
