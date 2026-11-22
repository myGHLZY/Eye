<template>
  <div class="scatter-fields">
    <label>标记形状
      <select v-model="settings.markerShape">
        <option value="circle">圆形</option><option value="square">方形</option>
        <option value="triangle">三角形</option><option value="diamond">菱形</option>
        <option value="cross">叉号</option>
      </select>
    </label>
    <label>点大小 {{ settings.markerSize }}
      <input v-model.number="settings.markerSize" type="range" min="10" max="100" step="1">
    </label>
    <label>不透明度 {{ Math.round(settings.opacity * 100) }}%
      <input v-model.number="settings.opacity" type="range" min="0.15" max="1" step="0.01">
    </label>
    <label class="check"><input v-model="settings.hollow" type="checkbox" :disabled="settings.markerShape === 'cross'"> 空心标记</label>
    <template v-if="guides">
      <label class="check"><input v-model="settings.referenceLine" type="checkbox"> y = x 参考线</label>
      <label class="check"><input v-model="settings.fit" type="checkbox"> 线性拟合</label>
      <p>数值横轴支持参考线与线性拟合。拟合使用全部可见的散点数据，并显示 R² 和 RMSE。</p>
    </template>
  </div>
</template>

<script>
export default {
  name: 'ScatterStyleFields',
  props: {
    settings: { type: Object, required: true },
    guides: Boolean,
  },
}
</script>

<style scoped>
.scatter-fields { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; }
label { display: grid; gap: 4px; min-width: 0; color: #435774; font-size: 13px; }
.check { display: flex; align-items: center; gap: 4px; }
select { min-width: 0; padding: 5px; border: 1px solid #cdd9e9; border-radius: 5px; background: #fff; color: inherit; font: inherit; }
input[type='range'] { width: 100%; margin: 0; }
p { grid-column: 1 / -1; margin: 0; color: #52647d; font-size: 12px; }
</style>
