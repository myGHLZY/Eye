async function requestDatabase(path, method, settings) {
  const options = {
    method,
    cache: 'no-store',
    signal: AbortSignal.timeout(20000),
  }
  if (settings) {
    options.headers = { 'Content-Type': 'application/json' }
    options.body = JSON.stringify(settings)
  }

  let response
  try {
    response = await fetch(path, options)
  } catch (error) {
    if (error.name === 'TimeoutError') {
      throw new Error('请求超时，请检查 Flask 和 MySQL 服务。')
    }
    throw new Error('无法访问 Flask 服务，请确认后端已启动。')
  }

  const payload = await response.json().catch(() => null)
  if (!response.ok || !payload?.data) {
    throw new Error(payload?.error?.message || '无法读取后端响应，请确认 Flask 服务已在 5111 端口启动。')
  }
  return payload.data
}

export function getDatabaseConnection() {
  return requestDatabase('/api/database/connection', 'GET')
}

export function testDatabaseConnection(settings) {
  return requestDatabase('/api/database/test-connection', 'POST', settings)
}

export function saveDatabaseConnection(settings) {
  return requestDatabase('/api/database/connection', 'PUT', settings)
}

export function listDatabaseTables() {
  return requestDatabase('/api/database/tables', 'GET')
}

export function getDatabaseTable(name) {
  const params = new URLSearchParams({ name })
  return requestDatabase(`/api/database/tables/detail?${params}`, 'GET')
}

export function getDatabaseDiagram() {
  return requestDatabase('/api/database/schema/diagram', 'GET')
}
