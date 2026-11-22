<template>
  <section class="panel chart-statistics" aria-labelledby="chart-statistics-title">
    <h2 id="chart-statistics-title">误差棒与显著性</h2>
    <p v-if="!bars.length" class="muted">生成柱状图后可添加统计标注。</p>
    <div v-else class="statistics-layout">
      <div class="statistics-section">
        <label class="mode-field">
          <strong>误差棒</strong>
          <select v-model="errorMode">
            <option value="none">无</option>
            <option value="manual">手动填写</option>
            <option value="sampleSd" :disabled="!isAverage">标准差（SD）</option>
            <option value="sampleSem" :disabled="!isAverage">标准误（SEM）</option>
          </select>
        </label>
        <p v-if="!isAverage" class="muted">选择「平均值」聚合可使用按组计算的 SD 或 SEM。</p>
        <p v-else-if="isAutomatic" class="muted">有效记录少于 2 条的分类省略误差棒。</p>
        <p v-if="errorMode === 'manual'" class="muted">填写上下相同的误差幅度，留空则省略该柱的误差棒。</p>
        <div class="statistics-scroll">
          <table>
            <thead>
              <tr>
                <th scope="col">分类</th>
                <th scope="col">柱高</th>
                <th v-if="isAverage" scope="col">有效记录</th>
                <th v-if="errorMode !== 'none'" scope="col">误差幅度</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="bar in bars" :key="bar.key">
                <th scope="row" :title="bar.label">{{ bar.label }}</th>
                <td>{{ formatNumber(bar.value) }}{{ valueUnit }}</td>
                <td v-if="isAverage">{{ bar.sampleSize ?? '—' }}</td>
                <td v-if="errorMode === 'manual'">
                  <input
                    type="number" min="0" max="1e150" step="any" placeholder="—"
                    :value="manualErrors[bar.key] ?? ''"
                    :aria-label="bar.label + ' 的误差幅度'"
                    @input="$set(manualErrors, bar.key, $event.target.value)"
                  >
                </td>
                <td v-else-if="isAutomatic">{{ formatNumber(bar[errorMode]) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div class="statistics-section">
        <div class="comparison-heading">
          <h3>显著性标注</h3>
          <button type="button" :disabled="bars.length < 2 || comparisons.length >= maxComparisons"
            @click="addComparison">添加比较</button>
        </div>
        <p class="muted">选两组并填写已有检验结果的 p 值，或直接选择标注。</p>
        <p v-if="bars.length < 2" class="muted">至少需要两个可见分类。</p>
        <div v-for="(comparison, index) in comparisons" :key="comparison.id" class="comparison">
          <div class="comparison-pair">
            <select v-model="comparison.left" :aria-label="'比较 ' + (index + 1) + ' 的第一组'">
              <option value="">第一组</option>
              <option v-for="bar in bars" :key="bar.key" :value="bar.key" :disabled="bar.key === comparison.right">
                {{ bar.label }}
              </option>
            </select>
            <select v-model="comparison.right" :aria-label="'比较 ' + (index + 1) + ' 的第二组'">
              <option value="">第二组</option>
              <option v-for="bar in bars" :key="bar.key" :value="bar.key" :disabled="bar.key === comparison.left">
                {{ bar.label }}
              </option>
            </select>
          </div>
          <div class="comparison-format">
            <select v-model="comparison.format" :aria-label="'比较 ' + (index + 1) + ' 的标注格式'">
              <option value="p">按 p 值标星</option>
              <option value="*">*</option>
              <option value="**">**</option>
              <option value="***">***</option>
              <option value="ns">ns</option>
            </select>
            <input v-if="comparison.format === 'p'" v-model="comparison.pValue" type="number" min="0" max="1"
              step="any" placeholder="例如 0.004" :aria-label="'比较 ' + (index + 1) + ' 的 p 值'">
            <button type="button" @click="comparisons.splice(index, 1)" :aria-label="'移除比较 ' + (index + 1)">
              移除
            </button>
          </div>
          <p v-if="comparisonWarnings[comparison.id]" class="validation" role="status">{{ comparisonWarnings[comparison.id] }}</p>
          <p v-else class="comparison-ready" role="status">标注已设置，预览会自动更新。</p>
        </div>
      </div>
    </div>
  </section>
</template>

<script>
const maxComparisons = 8

function enteredNumber(value, maximum) {
  if (typeof value !== 'string' || !value.trim()) return null
  const number = Number(value)
  return Number.isFinite(number) && number >= 0 && number <= maximum ? number : null
}

export default {
  name: 'ChartStatisticsFields',
  props: {
    bars: { type: Array, required: true },
    scope: { type: String, required: true },
    isAverage: Boolean,
    valueUnit: { type: String, default: '' },
  },
  data() {
    return { errorMode: 'none', manualErrors: {}, comparisons: [], nextId: 1, maxComparisons }
  },
  computed: {
    isAutomatic() {
      return this.errorMode === 'sampleSd' || this.errorMode === 'sampleSem'
    },
    validComparisons() {
      const locations = new Map(this.bars.map((bar, index) => [bar.key, index]))
      const seen = new Set()
      const entries = []
      const warnings = {}
      for (const comparison of this.comparisons) {
        if (!comparison.left || !comparison.right || comparison.left === comparison.right) {
          warnings[comparison.id] = '请选择两根不同的柱子。'
          continue
        }
        const left = locations.get(comparison.left)
        const right = locations.get(comparison.right)
        if (left === undefined || right === undefined) {
          warnings[comparison.id] = '比较中的分类暂不可见。'
          continue
        }
        const pValue = enteredNumber(comparison.pValue, 1)
        if (comparison.format === 'p' && pValue === null) {
          warnings[comparison.id] = '请填写 0 至 1 的 p 值，或直接选择星号或 ns。'
          continue
        }
        const pair = [Math.min(left, right), Math.max(left, right)].join(',')
        if (seen.has(pair)) {
          warnings[comparison.id] = '这一对分类已有标注。'
          continue
        }
        seen.add(pair)
        entries.push({ left, right, ...(comparison.format === 'p' ? { pValue } : { label: comparison.format }) })
      }
      return { entries, warnings }
    },
    comparisonWarnings() {
      return this.validComparisons.warnings
    },
    renderOptions() {
      const errors = this.bars.map(bar => {
        if (this.errorMode === 'manual') return enteredNumber(this.manualErrors[bar.key], 1e150)
        return this.isAutomatic && this.isAverage ? (bar[this.errorMode] ?? null) : null
      })
      const comparisons = this.validComparisons.entries
      return {
        ...(errors.some(error => error !== null) ? { errorBars: errors } : {}),
        ...(comparisons.length ? { significance: comparisons } : {}),
      }
    },
  },
  watch: {
    scope() {
      this.errorMode = 'none'
      this.manualErrors = {}
      this.comparisons = []
    },
    renderOptions(options) {
      this.$emit('change', options)
    },
  },
  methods: {
    addComparison() {
      this.comparisons.push({ id: this.nextId++, left: '', right: '', format: 'p', pValue: '' })
    },
    formatNumber(value) {
      return value == null ? '—' : Number(value.toPrecision(5)).toString()
    },
  },
}
</script>

<style scoped>
.chart-statistics h2 { margin: 0 0 12px; color: #15243b; font-size: 17px; }
.statistics-layout { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 250px), 1fr)); gap: 16px; }
.statistics-section { min-width: 0; }
.mode-field, .comparison-heading { display: flex; align-items: center; justify-content: space-between; gap: 8px; min-height: 30px; }
.mode-field strong, h3 { margin: 0; color: #263c5a; font-size: 14px; }
.muted, .validation { margin: 5px 0 8px; color: #52647d; font-size: 12px; line-height: 1.45; }
.validation { margin: 0; color: #a12629; }
.comparison-ready { margin: 0; color: #257044; font-size: 12px; }
.statistics-scroll { max-height: 220px; overflow: auto; border: 1px solid #dfe7f1; border-radius: 6px; }
table { width: 100%; border-spacing: 0; text-align: left; color: #263c5a; font-size: 13px; }
th, td { padding: 5px 6px; border-bottom: 1px solid #e5edf6; }
thead th { position: sticky; top: 0; background: #f3f7fc; white-space: nowrap; }
tbody th { max-width: 110px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-weight: 400; }
.comparison { display: grid; gap: 6px; padding: 8px; margin-bottom: 6px; border: 1px solid #dfe7f1; border-radius: 6px; }
.comparison-pair, .comparison-format { display: flex; align-items: center; gap: 6px; }
.comparison-pair select, .comparison-format select, .comparison-format input { flex: 1; }
input, select, button {
  box-sizing: border-box; min-width: 0; min-height: 28px; padding: 3px 6px;
  border: 1px solid #cdd9e9; border-radius: 5px; background: #fff; color: #172942; font: inherit; font-size: 12px;
}
input { width: 100%; }
button { cursor: pointer; color: #235a9f; white-space: nowrap; }
button:disabled { color: #78879a; cursor: default; }
</style>
