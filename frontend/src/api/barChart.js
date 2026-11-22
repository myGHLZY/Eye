import { fetchChartData, renderChartImage } from './chart.js'

export async function fetchBarData(selection, signal) {
  const data = await fetchChartData('bar', selection, signal)
  if (selection.groupColumn && !Array.isArray(data.series)) {
    throw new Error('请重新运行 Flask 后端以加载分组和堆叠柱状图。')
  }
  return data
}

export function renderBarPreview(points, style, signal, series = []) {
  return renderChartImage('bar', { points, style, series }, signal, response => {
    const revision = Number(response.headers.get('X-Eye-Bar-Renderer'))
    const required = series.length || style.gradient ? 4 : (style.significance?.length ? 3 : 2)
    if (!Number.isFinite(revision) || revision < required) {
      throw new Error('5111 端口仍在运行旧版 Flask 渲染服务。请重启后端，再刷新图表。')
    }
  })
}
