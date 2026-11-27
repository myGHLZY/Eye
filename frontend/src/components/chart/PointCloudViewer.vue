<template>
  <div class="cloud-viewport">
    <canvas ref="canvas" tabindex="0" aria-label="交互式三维点云"
      @webglcontextlost.prevent="contextLost" @webglcontextrestored="contextRestored" />
    <p v-if="renderError" class="viewer-error" role="alert">{{ renderError }}</p>
  </div>
</template>

<script>
import {
  AxesHelper, BufferAttribute, BufferGeometry, Color, GridHelper, PerspectiveCamera, Points,
  PointsMaterial, Scene, SRGBColorSpace, Vector3, WebGLRenderer,
} from 'three'
import { OrbitControls } from 'three/addons/controls/OrbitControls.js'

const rgbToLinear = Float32Array.from({ length: 256 }, (_, level) => new Color()
  .setRGB(level / 255, 0, 0, SRGBColorSpace).r)
const lowColor = new Color('#42a5ff')
const middleColor = new Color('#89e9da')
const highColor = new Color('#ffcb78')

export default {
  name: 'PointCloudViewer',
  props: {
    cloud: { type: Object, required: true },
    colorMode: { type: String, required: true },
    pointSize: { type: Number, required: true },
    showAxes: { type: Boolean, required: true },
  },
  data() {
    return { renderError: '' }
  },
  watch: {
    cloud() { this.loadCloud() },
    colorMode() { this.updateColors() },
    pointSize(size) {
      if (!this._points) return
      this._points.material.size = size
      this.scheduleRender()
    },
    showAxes(visible) {
      if (!this._grid) return
      this._grid.visible = this._axes.visible = visible
      this.scheduleRender()
    },
  },
  mounted() {
    try {
      this._renderer = new WebGLRenderer({ canvas: this.$refs.canvas, antialias: true })
    } catch {
      this.renderError = '当前浏览器无法启动 WebGL 2，请检查浏览器的图形加速设置。'
      return
    }
    this._renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2))
    this._scene = new Scene()
    this._scene.background = new Color('#0f1d30')
    this._camera = new PerspectiveCamera(45, 1, 0.02, 200)
    this._camera.up.set(0, 0, 1)
    this._controls = new OrbitControls(this._camera, this.$refs.canvas)
    this._controls.minDistance = 0.06
    this._controls.maxDistance = 130
    this._controls.listenToKeyEvents(this.$refs.canvas)
    this._controls.addEventListener('change', this.scheduleRender)
    this._grid = new GridHelper(3, 12, '#405570', '#283c53')
    this._grid.rotation.x = Math.PI / 2
    this._axes = new AxesHelper(0.34)
    this._grid.visible = this._axes.visible = this.showAxes
    this._scene.add(this._grid, this._axes)
    this._resizeObserver = new ResizeObserver(this.resize)
    this._resizeObserver.observe(this.$el)
    this.resize()
    this.loadCloud()
  },
  beforeDestroy() {
    this._resizeObserver?.disconnect()
    cancelAnimationFrame(this._frame)
    this._controls?.dispose()
    this.disposeCloud()
    for (const helper of [this._grid, this._axes]) {
      helper?.geometry.dispose()
      helper?.material.dispose()
    }
    this._renderer?.dispose()
  },
  methods: {
    resize() {
      const { clientWidth: width, clientHeight: height } = this.$el
      if (!width || !height || !this._renderer) return
      this._renderer.setSize(width, height, false)
      this._camera.aspect = width / height
      this._camera.updateProjectionMatrix()
      this.scheduleRender()
    },
    loadCloud() {
      if (!this._scene) return
      this.disposeCloud()
      const geometry = new BufferGeometry()
      geometry.setAttribute('position', new BufferAttribute(this.cloud.positions, 3))
      geometry.computeBoundingSphere()
      const material = new PointsMaterial({ size: this.pointSize, sizeAttenuation: false, color: '#81c5ff' })
      this._points = new Points(geometry, material)
      this._scene.add(this._points)
      const floor = (this.cloud.bounds.min[2] - this.cloud.origin[2]) / this.cloud.scale - 0.035
      this._grid.position.z = floor
      this._axes.position.set(-1.33, -1.33, floor)
      this.updateColors()
      this.resetView()
    },
    updateColors() {
      if (!this._points) return
      const { geometry, material } = this._points
      const { positions, colors, bounds, origin, scale } = this.cloud
      const original = this.colorMode === 'original' && colors
      const height = this.colorMode === 'height'
      if (original || height) {
        const attribute = geometry.getAttribute('color') || new BufferAttribute(new Float32Array(positions.length), 3)
        const values = attribute.array
        if (original) {
          for (let index = 0; index < colors.length; index += 1) values[index] = rgbToLinear[colors[index]]
        } else {
          const low = (bounds.min[2] - origin[2]) / scale
          const high = (bounds.max[2] - origin[2]) / scale
          const color = new Color()
          for (let index = 0; index < positions.length; index += 3) {
            const fraction = high === low ? 0.5 : Math.max(0, Math.min(1, (positions[index + 2] - low) / (high - low)))
            if (fraction < 0.5) color.copy(lowColor).lerp(middleColor, 2 * fraction)
            else color.copy(middleColor).lerp(highColor, 2 * fraction - 1)
            color.toArray(values, index)
          }
        }
        geometry.setAttribute('color', attribute)
        attribute.needsUpdate = true
      }
      material.vertexColors = Boolean(original || height)
      material.color.set(material.vertexColors ? '#ffffff' : '#81c5ff')
      material.needsUpdate = true
      this.scheduleRender()
    },
    resetView() {
      if (!this._controls || !this._points) return
      const angle = Math.atan(Math.tan(this._camera.fov * Math.PI / 360) * Math.min(1, this._camera.aspect))
      const radius = Math.max(0.15, this._points.geometry.boundingSphere.radius)
      const target = this._points.geometry.boundingSphere.center
      const distance = Math.min(120, Math.max(2.7, radius * 1.13 / Math.sin(angle)))
      this._camera.position.copy(new Vector3(1.4, -1.8, 1.2).setLength(distance).add(target))
      this._controls.target.copy(target)
      this._controls.update()
      this.scheduleRender()
    },
    scheduleRender() {
      if (this._frame || !this._renderer || this.renderError) return
      this._frame = requestAnimationFrame(() => {
        this._frame = null
        if (!this.renderError) this._renderer.render(this._scene, this._camera)
      })
    },
    disposeCloud() {
      if (!this._points) return
      this._scene.remove(this._points)
      this._points.geometry.dispose()
      this._points.material.dispose()
      this._points = null
    },
    contextLost() {
      this.renderError = '浏览器的 3D 绘图环境暂时不可用。'
    },
    contextRestored() {
      this.renderError = ''
      this.scheduleRender()
    },
  },
}
</script>

<style scoped>
.cloud-viewport { position: relative; width: 100%; height: 100%; min-height: 0; }
canvas { display: block; width: 100%; height: 100%; touch-action: none; cursor: grab; }
canvas:active { cursor: grabbing; }
canvas:focus-visible { outline: 2px solid #89e9da; outline-offset: -4px; }
.viewer-error {
  position: absolute; inset: 0; display: grid; place-content: center; margin: 0; padding: 24px;
  color: #fbd8d7; background: #0f1d30; text-align: center;
}
</style>
