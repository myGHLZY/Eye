import { numericColumn, uniqueAlias } from './viewWorkspace.js'

export function connectCanvasFields(spec, from, to) {
  // 将两张卡片上的字段连接更新到同一份查询配置。
  if (from.side === to.side) return ''
  const condition = from.side === 'left'
    ? { left: from.field.name, right: to.field.name }
    : { left: to.field.name, right: from.field.name }
  const complete = spec.conditions.filter(item => item.left && item.right)
  if (complete.some(item => item.left === condition.left && item.right === condition.right)) return '这两个字段已经连接。'
  if (complete.length >= 8) return '两表连接最多支持 8 个条件。'
  spec.conditions = [...complete, condition]
  return ''
}

export function placeCanvasField(spec, role, field) {
  // 角色区只接受当前操作可以使用的字段。
  if (spec.mode === 'pivot') {
    const collision = (role === 'row' && spec.category === field.name) ||
      (role === 'category' && spec.row === field.name)
    if (collision) return '请用不同的字段作为行和列类别。'
    if (role === 'metric' && !numericColumn(field)) return '请拖入一个数值字段。'
    spec[role] = field.name
    return ''
  }
  if (role === 'keys') {
    if (spec.keys.includes(field.name)) return ''
    if (spec.keys.length >= 64) return '最多保留 64 个字段。'
    spec.keys.push(field.name)
    spec.columns = spec.columns.filter(column => column.name !== field.name)
  } else {
    if (spec.columns.some(column => column.name === field.name)) return ''
    if (spec.columns.length >= 16) return '一次最多展开 16 个字段。'
    spec.keys = spec.keys.filter(name => name !== field.name)
    spec.columns.push({ name: field.name, alias: uniqueAlias(field.name, spec.columns.map(column => column.alias)) })
  }
  return ''
}

export function resetCanvasSource(spec, source) {
  spec.source = source
  spec.columns = []
  if (spec.mode === 'pivot') {
    spec.row = spec.category = spec.metric = ''
  } else {
    spec.keys = []
  }
}
