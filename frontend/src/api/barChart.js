async function postChart(action, payload, signal) {
  const response = await fetch(`/api/database/charts/bar/${action}`, {
    method: 'POST',
    cache: 'no-store',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
    signal: typeof AbortSignal.any === 'function' ? AbortSignal.any([signal, AbortSignal.timeout(20000)]) : signal,
  })
  if (!response.ok) {
    const result = await response.json().catch(() => null)
    throw new Error(result?.error?.message || `柱状图请求失败（HTTP ${response.status}）。`)
  }
  return response
}

export async function fetchBarData(selection, signal) {
  const response = await postChart('data', selection, signal)
  const data = (await response.json()).data
  if (selection.groupColumn && !Array.isArray(data.series)) {
    throw new Error('请重新运行 Flask 后端以加载分组和堆叠柱状图。')
  }
  return data
}

export async function renderBarPreview(points, style, signal, series = []) {
  const response = await postChart('render', { points, style, series }, signal)
  if (!response.headers.get('content-type')?.startsWith('image/png')) {
    throw new Error('预览接口没有返回 PNG 图片。')
  }
  const revision = Number(response.headers.get('X-Eye-Bar-Renderer'))
  const required = series.length || style.gradient ? 4 : (style.significance?.length ? 3 : 2)
  if (!Number.isFinite(revision) || revision < required) {
    throw new Error('5111 端口仍在运行旧版 Flask 渲染服务。请重启后端，再刷新图表。')
  }
  return response.blob()
}
