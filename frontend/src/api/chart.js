async function postChart(kind, action, payload, signal) {
  const requestSignal = typeof AbortSignal.any === 'function' && typeof AbortSignal.timeout === 'function'
    ? AbortSignal.any([...(signal ? [signal] : []), AbortSignal.timeout(20000)])
    : signal
  const response = await fetch(`/api/database/charts/${kind}/${action}`, {
    method: 'POST', cache: 'no-store', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload), signal: requestSignal,
  })
  if (response.ok) return response
  const result = await response.json().catch(() => null)
  if (response.status === 404 && !result) throw new Error('请重新运行 Flask 后端以加载图表接口。')
  throw new Error(result?.error?.message || `图表请求失败（HTTP ${response.status}）。`)
}

export async function fetchChartData(kind, selection, signal) {
  const response = await postChart(kind, 'data', selection, signal)
  return (await response.json()).data
}

export async function renderChartImage(kind, payload, signal, validateResponse) {
  const response = await postChart(kind, 'render', payload, signal)
  if (!response.headers.get('Content-Type')?.startsWith('image/png')) {
    throw new Error('渲染接口没有返回 PNG 图片。')
  }
  validateResponse?.(response)
  return response.blob()
}
