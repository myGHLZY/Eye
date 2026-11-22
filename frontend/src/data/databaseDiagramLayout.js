import dagre from '@dagrejs/dagre'

export function layoutDatabaseDiagram(tables, links) {
  const graph = new dagre.graphlib.Graph()
    .setGraph({ rankdir: 'LR', ranksep: 185, nodesep: 55 })
    .setDefaultEdgeLabel(() => ({}))
  const connected = new Set()

  for (const [source, target] of links) {
    if (source === target) continue
    connected.add(source.id)
    connected.add(target.id)
    graph.setNode(source.id, { width: source.width, height: source.height })
    graph.setNode(target.id, { width: target.width, height: target.height })
    graph.setEdge(source.id, target.id)
  }

  const positions = new Map()
  let bottom = 0
  if (connected.size) {
    dagre.layout(graph)
    for (const id of connected) {
      const { x, y, width, height } = graph.node(id)
      positions.set(id, { x: x - width / 2, y: y - height / 2 })
      bottom = Math.max(bottom, y + height / 2)
    }
  }

  const isolated = tables.filter(table => !connected.has(table.id))
  const columns = Math.min(4, Math.ceil(Math.sqrt(isolated.length)))
  let y = connected.size ? bottom + 72 : 0
  for (let index = 0; index < isolated.length; index += columns) {
    const row = isolated.slice(index, index + columns)
    let x = 0
    for (const table of row) {
      positions.set(table.id, { x, y })
      x += table.width + 90
    }
    y += Math.max(...row.map(table => table.height)) + 62
  }

  return positions
}
