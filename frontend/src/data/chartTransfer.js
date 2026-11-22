let pieSnapshot = null

export function transferBarToPie(points, seriesName, title) {
  // Grouped and stacked charts already expose the category totals as point values.
  const entries = points.filter(point => point.value > 0)
    .map((point, index) => ({ key: 'bar-' + index, label: point.label, value: point.value }))
    .sort((left, right) => right.value - left.value)
  const total = entries.reduce((sum, point) => sum + point.value, 0)
  const combined = entries.length > 12
  if (combined) {
    const other = entries.splice(11).reduce((sum, point) => sum + point.value, 0)
    entries.push({ key: 'others', label: '其他分类', value: other })
  }
  pieSnapshot = { points: entries, total, seriesName, combined, title: title.slice(0, 60), fromBar: true }
}

export function takePieSnapshot() {
  // Keep chart data in memory just long enough to hand it to the pie editor.
  const snapshot = pieSnapshot
  pieSnapshot = null
  return snapshot
}
