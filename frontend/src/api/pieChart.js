import { fetchChartData, renderChartImage } from './chart.js'

export function fetchPieData(selection, signal) {
  return fetchChartData('pie', selection, signal)
}

export function renderPiePreview(points, style, signal) {
  return renderChartImage('pie', { points, style }, signal)
}
