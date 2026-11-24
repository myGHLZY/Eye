export function drawViewConnections(board, canvas, connections) {
  const surface = board.getBoundingClientRect()
  const scale = Math.min(window.devicePixelRatio || 1, 2)
  canvas.width = Math.round(surface.width * scale)
  canvas.height = Math.round(surface.height * scale)
  const context = canvas.getContext('2d')
  if (!context) return
  context.scale(scale, scale)

  const ports = new Map()
  for (const button of board.querySelectorAll('[data-graph-column]')) {
    const rect = button.getBoundingClientRect()
    const scroller = button.closest('.canvas-column-list').getBoundingClientRect()
    const { side, graphColumn } = button.dataset
    const center = (rect.top + rect.bottom) / 2
    if (center < scroller.top || center > scroller.bottom) continue
    const card = button.closest('.canvas-table').getBoundingClientRect()
    ports.set(side + ':' + graphColumn, {
      x: (side === 'left' ? card.right : card.left) - surface.left,
      y: center - surface.top,
    })
  }

  context.strokeStyle = '#447ed1'
  context.lineWidth = 2
  for (const pair of connections) {
    const start = ports.get('left:' + pair.left)
    const end = ports.get('right:' + pair.right)
    if (!start || !end) continue
    const middle = (start.x + end.x) / 2
    context.beginPath()
    context.moveTo(start.x, start.y)
    context.bezierCurveTo(middle, start.y, middle, end.y, end.x, end.y)
    context.stroke()
  }
}
