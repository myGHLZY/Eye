const numberType = /^(tinyint|smallint|mediumint|int|integer|bigint|decimal|numeric|float|double|real|year)\b/i

export const maxDrafts = 10
export const maxComputeOperands = 32
export const viewOperations = {
  join: '两表连接', pivot: '长表转宽表', filter: '筛选行', project: '选择与重命名字段',
  compute: '计算新列', bin: '分箱', unpivot: '宽表转长表', dedupe: '去重或保留最新记录', window: '排名与累计',
}
export const visualViewModes = ['join', 'pivot', 'unpivot']

export function numericColumn(column) {
  return numberType.test(column.type)
}

export function uniqueAlias(base, existing) {
  const names = new Set(existing.map(name => name.toLowerCase()))
  let alias = base.slice(0, 64)
  for (let i = 2; names.has(alias.toLowerCase()); i++) {
    const suffix = '_' + i
    alias = base.slice(0, 64 - suffix.length) + suffix
  }
  return alias
}

export function setJoinSource(spec, side, source) {
  if (spec[side] === source) return
  spec[side] = source
  spec.conditions.forEach(condition => { condition[side] = '' })
  spec.columns = spec.columns.filter(column => column.side !== side)
}

export function addJoinOutput(spec, side, name) {
  if (spec.columns.length >= 64 || spec.columns.some(column => column.side === side && column.name === name)) return
  spec.columns.push({ side, name, alias: uniqueAlias(name, spec.columns.map(column => column.alias)) })
}

export function addPivotValue(spec, value) {
  if (spec.columns.length >= 16 || spec.columns.some(column => column.value === value)) return
  const base = value.trim().slice(0, 60) || '空字符串'
  const alias = uniqueAlias(base, [spec.row, ...spec.columns.map(column => column.alias)])
  spec.columns.push({ value, alias })
}

export function newViewSpec(mode) {
  if (mode === 'join') return { mode, left: '', right: '', joinType: 'inner', conditions: [{ left: '', right: '' }], columns: [] }
  if (mode === 'pivot') return { mode, source: '', row: '', category: '', metric: '', aggregation: 'sum', columns: [] }
  if (mode === 'filter') return { mode, source: '', match: 'all', conditions: [newFilterCondition()] }
  if (mode === 'project') return { mode, source: '', columns: [] }
  if (mode === 'compute') return {
    mode, source: '', inputMode: 'fields', operands: [newComputeOperand(), newComputeOperand()], expression: '', alias: '',
  }
  if (mode === 'bin') return { mode, source: '', field: '', boundaries: ['', ''], alias: '' }
  if (mode === 'unpivot') return { mode, source: '', keys: [], columns: [], categoryAlias: '类别', valueAlias: '数值' }
  if (mode === 'dedupe') return { mode, source: '', method: 'distinct', keys: [], order: '', tie: '' }
  if (mode === 'window') return {
    mode, source: '', scope: 'group', operation: 'summary', keys: [], summaryAlias: '汇总值',
    aggregation: 'sum', partitionKeys: [], order: '', tie: '', direction: 'desc', metric: '', alias: '',
  }
  return { mode: 'sql', sql: '' }
}

export function restoreViewSpec(spec) {
  if (spec.mode === 'compute' && !Array.isArray(spec.operands)) {
    const { left, right, operator, ...rest } = spec
    return {
      ...newViewSpec('compute'), ...rest, operands: [
        { ...newComputeOperand(), ...left },
        { ...newComputeOperand(), ...right, operator: operator || 'add' },
      ],
    }
  }
  if (spec.mode !== 'window') return spec
  return { ...newViewSpec('window'), scope: 'detail', ...spec }
}

export function newComputeOperand() {
  return { kind: 'field', value: '', operator: 'add' }
}

export function newFilterCondition() {
  return { field: '', operator: 'eq', value: '' }
}

export function needsFilterValue(operator) {
  return operator !== 'isNull' && operator !== 'notNull'
}

export function sourcesFor(spec) {
  if (spec.mode === 'join') return [spec.left, spec.right].filter(Boolean)
  return spec.source ? [spec.source] : []
}

export function relevantDrafts(spec, drafts) {
  const bySource = new Map(drafts.map(draft => ['draft:' + draft.id, draft]))
  const required = new Map()
  const visit = source => {
    const draft = bySource.get(source)
    if (!draft || required.has(draft.id)) return
    required.set(draft.id, { id: draft.id, spec: draft.spec })
    sourcesFor(draft.spec).forEach(visit)
  }
  sourcesFor(spec).forEach(visit)
  return [...required.values()]
}

export function hasViewSelection(spec) {
  if (spec.mode === 'sql') return Boolean(spec.sql.trim())
  if (spec.columns && (!spec.columns.length || spec.columns.some(column => !column.alias.trim()))) return false
  if (spec.mode === 'join') {
    return Boolean(spec.left && spec.right && spec.conditions.every(condition => condition.left && condition.right))
  }
  if (!spec.source) return false
  switch (spec.mode) {
    case 'pivot': return Boolean(spec.row && spec.category && (spec.aggregation === 'count' || spec.metric))
    case 'filter': return spec.conditions.every(condition => condition.field)
    case 'project': return true
    case 'compute': {
      const input = restoreViewSpec(spec)
      return Boolean(input.alias && (input.inputMode === 'formula'
        ? input.expression.trim()
        : input.operands.length >= 2 && input.operands.every(item => item.value !== '')))
    }
    case 'bin': return Boolean(spec.field && spec.alias && spec.boundaries.every(value => value !== ''))
    case 'unpivot': return Boolean(spec.categoryAlias && spec.valueAlias)
    case 'dedupe': return spec.method === 'distinct' || Boolean(spec.order && spec.keys.length)
    case 'window':
      if (spec.scope === 'group') {
        return Boolean(spec.keys.length && spec.summaryAlias && (spec.aggregation === 'count' || spec.metric) &&
          (spec.operation === 'summary' || spec.alias))
      }
      return Boolean(spec.order && spec.alias && (spec.operation !== 'runningSum' || spec.metric))
    default: return false
  }
}

export function draftStorageKey(connectionId) {
  return 'eye:views:drafts:' + connectionId
}
