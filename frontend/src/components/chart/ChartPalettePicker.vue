<template>
  <div class="palette-picker">
    <label class="palette-label" :for="inputId">预设色组</label>
    <el-select
      :id="inputId"
      :value="activeId"
      size="small"
      placeholder="选择色组"
      @input="change"
    >
      <el-option v-for="palette in palettes" :key="palette.id" :label="palette.name" :value="palette.id">
        <div class="palette-option">
          <span>{{ palette.name }}</span>
          <span class="option-swatches" aria-hidden="true">
            <span v-for="(color, index) in palette.colors.slice(0, 6)" :key="index" :style="{ backgroundColor: color }"></span>
          </span>
        </div>
      </el-option>
    </el-select>
    <div v-if="activePalette" class="palette-strip" :aria-label="activePalette.name + '，' + activePalette.colors.length + ' 色'" role="img">
      <span v-for="(color, index) in activePalette.colors" :key="index" :style="{ backgroundColor: color }" :title="color.toUpperCase()"></span>
    </div>
  </div>
</template>

<script>
import ElOption from 'element-ui/lib/option'
import ElSelect from 'element-ui/lib/select'

import 'element-ui/lib/theme-chalk/input.css'
import 'element-ui/lib/theme-chalk/option.css'
import 'element-ui/lib/theme-chalk/select.css'

let nextInputId = 0

export default {
  name: 'ChartPalettePicker',
  components: { ElOption, ElSelect },
  props: {
    palettes: { type: Array, required: true },
    activeId: { type: String, default: '' },
  },
  data() {
    return { inputId: 'chart-palette-' + ++nextInputId }
  },
  computed: {
    activePalette() {
      return this.palettes.find(palette => palette.id === this.activeId)
    },
  },
  methods: {
    change(id) {
      const palette = this.palettes.find(item => item.id === id)
      if (palette) this.$emit('select', palette)
    },
  },
}
</script>

<style scoped>
.palette-picker {
  display: grid;
  grid-template-columns: 64px minmax(0, 1fr);
  align-items: center;
  gap: 6px 8px;
  font-size: 13px;
}
.palette-picker .el-select { width: 100%; }
.palette-label { color: #435774; }
.palette-option { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
.option-swatches,
.palette-strip {
  display: flex;
  overflow: hidden;
  border-radius: 3px;
}
.option-swatches span { width: 10px; height: 10px; }
.palette-strip { grid-column: 2; height: 6px; }
.palette-strip span { flex: 1; }
</style>
