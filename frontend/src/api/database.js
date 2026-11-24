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

export function listDatabaseConnections() {
  return requestDatabase('/api/database/connections', 'GET')
}

export function disconnectDatabaseConnection(connectionId) {
  return requestDatabase(`/api/database/connections/${encodeURIComponent(connectionId)}`, 'DELETE')
}

function databasePath(path, connectionId, params = {}) {
  const query = new URLSearchParams(params)
  if (connectionId) query.set('connectionId', connectionId)
  const search = query.toString()
  return search ? `${path}?${search}` : path
}

function readSchema(path, connectionId, params = {}) {
  return requestDatabase(databasePath(path, connectionId, params), 'GET')
}

export function listDatabaseTables(connectionId) {
  return readSchema('/api/database/tables', connectionId)
}

export function getDatabaseTable(name, connectionId) {
  return readSchema('/api/database/tables/detail', connectionId, { name })
}

export function listChartSources(connectionId) {
  return readSchema('/api/database/sources', connectionId)
}

export function getChartSource(name, connectionId) {
  return readSchema('/api/database/sources/detail', connectionId, { name })
}

export function previewView(payload) {
  return requestDatabase('/api/database/views/preview', 'POST', payload)
}

export function listViewCategories(payload) {
  return requestDatabase('/api/database/views/categories', 'POST', payload)
}

export function createDatabaseView(payload) {
  return requestDatabase('/api/database/views', 'POST', payload)
}

export function previewSavedView(connectionId, name) {
  return readSchema('/api/database/views/rows', connectionId, { name })
}

export function getDatabaseDiagram(connectionId) {
  return readSchema('/api/database/schema/diagram', connectionId)
}

const rowsPath = '/api/database/tables/rows'

export function listTableRows(connectionId, name, params) {
  return readSchema(rowsPath, connectionId, { name, ...params })
}

export function createTableRow(connectionId, name, values) {
  return requestDatabase(databasePath(rowsPath, connectionId, { name }), 'POST', { values })
}

export function updateTableRow(connectionId, name, key, values) {
  return requestDatabase(databasePath(rowsPath, connectionId, { name }), 'PATCH', { key, values })
}

export function deleteTableRow(connectionId, name, key) {
  return requestDatabase(databasePath(rowsPath, connectionId, { name }), 'DELETE', { key })
}
