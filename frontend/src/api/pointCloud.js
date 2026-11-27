export const pointCloudExtensions = ['ply', 'pcd', 'las', 'laz', 'xyz', 'xyzrgb', 'pts', 'csv', 'tsv', 'txt', 'asc']
export const maxPointCloudBytes = 128 * 1024 ** 2

function decodeBytes(encoded) {
  const decoded = atob(encoded)
  const bytes = new Uint8Array(decoded.length)
  for (let index = 0; index < bytes.length; index += 1) bytes[index] = decoded.charCodeAt(index)
  return bytes
}

export async function fetchPointCloud(file, signal) {
  const body = new FormData()
  body.append('file', file)
  let response
  try {
    response = await fetch('/api/point-clouds/preview', { method: 'POST', body, signal })
  } catch (error) {
    if (error.name === 'AbortError') throw error
    throw new Error('无法连接点云处理服务，请确认 Flask 后端已启动。')
  }
  const result = await response.json().catch(() => null)
  if (!response.ok || !result?.data) {
    const fallback = response.status === 413
      ? '文件超过上传上限。'
      : response.status === 404 ? '点云接口不可用，请重新启动 Flask 后端。' : '无法获取点云预览。'
    throw new Error(result?.error?.message || fallback)
  }
  const data = result.data
  const positions = new Float32Array(decodeBytes(data.positions).buffer)
  const colors = data.colors ? decodeBytes(data.colors) : null
  if (positions.length !== data.previewCount * 3 || (colors && colors.length !== positions.length)) {
    throw new Error('返回的点云数据不完整。')
  }
  return Object.freeze({ ...data, positions, colors })
}
