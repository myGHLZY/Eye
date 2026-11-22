async function postPie(action, payload, signal) {
  const response = await fetch(`/api/database/charts/pie/${action}`, {
    method: 'POST',
    cache: 'no-store',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
    signal: typeof AbortSignal.any === 'function' ? AbortSignal.any([signal, AbortSignal.timeout(20000)]) : signal,
  })
  if (response.ok) return response

  const result = await response.json().catch(() => null)
  if (response.status === 404 && !result) throw new Error('请在 PyCharm 重新运行 Flask 后端以加载饼图接口。')
  throw new Error(result?.error?.message || '饼图请求失败，请检查 Flask 和数据库。')
}

export async function fetchPieData(selection, signal) {
  const response = await postPie('data', selection, signal)
  return (await response.json()).data
}

export async function renderPiePreview(points, style, signal) {
  const response = await postPie('render', { points, style }, signal)
  if (!response.headers.get('Content-Type')?.startsWith('image/png')) throw new Error('预览接口没有返回 PNG 图片。')
  return response.blob()
}
