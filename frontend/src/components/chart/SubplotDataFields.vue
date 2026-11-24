<template>
  <div class="source-fields">
    <label v-if="overlay && entry.kind !== 'scatter'">系列来源
      <select v-model="entry.seriesMode">
        <option value="single">一个系列</option>
        <option value="group">按字段分组</option>
        <option value="fields">两个数值字段</option>
      </select>
    </label>
    <chart-data-picker :key="entry.kind" v-model="entry.selection"
      :aggregations="secondaryLabel ? numericAggregations : aggregations"
      :raw-points="entry.kind === 'scatter'" :group-mode="groupMode"
      category-label="横轴字段" :group-label="entry.kind === 'scatter' ? '分组字段（可选）' : '系列字段'"
      :value-label="valueLabel" :secondary-label="secondaryLabel" />
  </div>
</template>

<script>
import ChartDataPicker from './ChartDataPicker.vue'

const numericAggregations = ['sum', 'average', 'max', 'min', 'raw']
const aggregations = ['sum', 'count', 'average', 'max', 'min', 'raw']

export default {
  name: 'SubplotDataFields',
  components: { ChartDataPicker },
  props: { entry: { type: Object, required: true }, overlay: Boolean },
  data: () => ({ aggregations, numericAggregations }),
  computed: {
    groupMode() {
      if (this.entry.kind === 'scatter') return 'optional'
      if (this.overlay) return this.entry.seriesMode === 'group' ? 'required' : 'none'
      return this.entry.kind === 'line' ? 'optional' : 'none'
    },
    valueLabel() {
      if (this.entry.kind === 'scatter') return '纵轴数值'
      return this.entry.kind === 'bar_line' ? '柱形数值字段' : '数值字段'
    },
    secondaryLabel() {
      if (this.entry.kind === 'bar_line') return '折线数值字段'
      return this.overlay && this.entry.kind !== 'scatter' && this.entry.seriesMode === 'fields' ? '第二数值字段' : ''
    },
  },
}
</script>

<style scoped>
.source-fields { display: grid; gap: 9px; }
label { display: grid; gap: 5px; font-size: 13px; color: #435774; }
select { min-width: 0; padding: 6px; border: 1px solid #cdd9e9; border-radius: 5px; background: #fff; color: #172942; font: inherit; }
</style>
