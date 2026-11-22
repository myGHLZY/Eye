export async function checkHealth() {
  const response = await fetch('/api/health', {
    cache: 'no-store',
    signal: AbortSignal.timeout(5000),
  })
  if (!response.ok) {
    throw new Error(`请求返回 HTTP ${response.status}。`)
  }

  const payload = await response.json()
  if (payload?.data?.status !== 'ok') {
    throw new Error('健康接口返回了非预期的状态。')
  }

  return payload
}
