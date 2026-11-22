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
  return (await response.json()).data
}

export async function renderBarPreview(points, style, signal) {
  const response = await postChart('render', { points, style }, signal)
  if (!response.headers.get('content-type')?.startsWith('image/png')) {
    throw new Error('预览接口没有返回 PNG 图片。')
  }
  const revision = response.headers.get('X-Eye-Bar-Renderer')
  if (revision !== '3' && (revision !== '2' || style.significance?.length)) {
    throw new Error('5111 端口仍在运行旧版 Flask 渲染服务。请重启后端，再刷新图表。')
  }
  return response.blob()
}
