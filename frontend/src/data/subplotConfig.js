import { createScatterStyle } from './scatterStyle.js'

export const layerKinds = { bar: '柱状图', line: '折线图', scatter: '散点图' }
export const kinds = { ...layerKinds, bar_line: '柱状图＋折线图', overlay: '重合子图' }

function createLayerStyle(index, overrides = {}) {
  return {
    ...createScatterStyle(), markerSize: 28,
    color: index === 0 ? '#4281bb' : '#bb5635',
    opacity: index === 0 ? 0.82 : 0.75,
    legendLabel: '', lineStyle: 'solid', lineWidth: 1.8, markers: true,
    lineMarker: 'circle', lineMarkerSize: 4, ...overrides,
  }
}

export function createPanel(id, kind = 'bar') {
  // 独立保存子图的数据选择和样式，切换图形时可保留样式。
  return {
    id, kind, selection: null, title: '', xLabel: '', yLabel: '', rightLabel: '', rightAxis: false,
    layers: [
      {
        kind: 'bar', selection: null, seriesMode: 'single',
        style: createLayerStyle(0, { color: '#ff8000', opacity: 1 }),
        secondSeriesStyle: createLayerStyle(0, { color: '#8000c5', opacity: 1, lineStyle: 'dashed' }),
      },
      {
        kind: 'line', selection: null, seriesMode: 'single',
        style: createLayerStyle(1, { color: '#dd2222', opacity: 1, lineMarker: 'triangle', lineMarkerSize: 7 }),
        secondSeriesStyle: createLayerStyle(1, {
          color: '#2548d8', opacity: 1, lineStyle: 'dashed', lineMarker: 'square', lineMarkerSize: 5,
        }),
      },
    ],
    primaryStyle: createLayerStyle(0),
    secondaryStyle: createLayerStyle(1),
    style: {
      backgroundColor: '#ffffff', grid: 'both', frame: 'box', legend: 'inherit', legendFrame: kind === 'overlay',
      tickRotation: null, yMin: null, yMax: null, rightYMin: null, rightYMax: null,
    },
  }
}

export function isMultiSeries(layer) {
  return layer.kind === 'scatter' ? Boolean(layer.selection?.groupColumn) : layer.seriesMode !== 'single'
}

export function subplotPayload(panels, style) {
  // 只提交当前图形所使用的配置。
  return {
    style,
    panels: panels.map(panel => {
      const { kind, title, xLabel, yLabel, rightLabel, rightAxis } = panel
      const base = { kind, title, xLabel, yLabel, rightLabel, rightAxis, style: panel.style }
      if (kind === 'overlay') {
        return {
          ...base,
          layers: panel.layers.map(layer => ({
            kind: layer.kind, selection: layer.selection, style: layer.style,
            ...(isMultiSeries(layer) ? { secondSeriesStyle: layer.secondSeriesStyle } : {}),
          })),
        }
      }
      return {
        ...base, selection: panel.selection, primaryStyle: panel.primaryStyle,
        ...(kind === 'bar_line' ? { secondaryStyle: panel.secondaryStyle } : {}),
      }
    }),
  }
}
