<template>
  <section class="cloud-page">
    <aside class="cloud-controls" aria-label="点云设置">
      <section class="panel">
        <h2>上传点云文件</h2>
        <div class="drop-zone" :class="{ dragging }" @dragover.prevent="dragging = true"
          @dragleave="leaveDropZone" @drop.prevent="dropFile">
          <i class="el-icon-upload" aria-hidden="true"></i>
          <button class="primary-button" type="button" @click="$refs.fileInput.click()">选择文件</button>
          <input ref="fileInput" type="file" :accept="accept" hidden @change="changeFile">
          <p>也可以把文件拖到这里</p>
        </div>
        <p class="note">支持 PLY、PCD、LAS、LAZ、XYZ、XYZRGB、PTS、CSV、TSV、TXT、ASC，单个文件最大 128 MiB。</p>
        <div v-if="pendingFile" class="upload-status">
          <span role="status">正在上传并解析 {{ pendingFile }}</span>
          <button class="secondary-button" type="button" @click="cancelUpload">取消</button>
        </div>
        <p v-if="error" class="error" role="alert">{{ error }}</p>
      </section>
      <section v-if="cloud" class="panel">
        <h2>显示设置</h2>
        <label class="field">点颜色
          <select v-model="colorMode">
            <option v-if="cloud.colors" value="original">原始 RGB</option>
            <option value="height">按 Z 高度</option>
            <option value="solid">单色</option>
          </select>
        </label>
        <label class="field">点大小（{{ pointSize }} px）
          <input v-model.number="pointSize" type="range" min="1" max="8" step="0.5">
        </label>
        <label class="checkbox"><input v-model="showAxes" type="checkbox">显示坐标轴和网格</label>
      </section>
    </aside>
    <section class="panel preview-panel" aria-label="点云预览" :aria-busy="Boolean(pendingFile)">
      <header class="preview-heading">
        <div class="preview-title">
          <h2>点云预览</h2>
          <p v-if="cloud" class="filename" :title="filename">{{ filename }}</p>
        </div>
        <button v-if="cloud" class="secondary-button" type="button" @click="$refs.viewer.resetView()">重置视角</button>
      </header>
      <div class="preview-stage">
        <point-cloud-viewer v-if="cloud" ref="viewer" :cloud="cloud" :color-mode="colorMode"
          :point-size="pointSize" :show-axes="showAxes" />
        <div v-else class="empty-preview">
          <i class="el-icon-data-analysis" aria-hidden="true"></i>
          <p>{{ pendingFile ? '正在读取点云…' : '上传点云文件后即可查看 3D 预览' }}</p>
        </div>
      </div>
      <template v-if="cloud">
        <div class="preview-info">
          <span>{{ cloud.format.toUpperCase() }} · {{ formatCount(cloud.pointCount) }} 个有效点</span>
          <span v-if="cloud.previewCount < cloud.pointCount">抽样显示 {{ formatCount(cloud.previewCount) }} 点</span>
          <span v-if="cloud.inputCount > cloud.pointCount">已跳过 {{ formatCount(cloud.inputCount - cloud.pointCount) }} 个无效点</span>
        </div>
        <p class="note">拖动旋转，滚轮缩放，右键拖动平移。触屏可用双指缩放和平移。</p>
      </template>
    </section>
  </section>
</template>

<script>
import { fetchPointCloud, maxPointCloudBytes, pointCloudExtensions } from '../api/pointCloud.js'

const counts = new Intl.NumberFormat('zh-CN')

export default {
  name: 'PointCloudView',
  components: { PointCloudViewer: () => import('../components/chart/PointCloudViewer.vue') },
  data() {
    return {
      accept: pointCloudExtensions.map(extension => '.' + extension).join(','),
      cloud: null, filename: '', colorMode: 'height', pointSize: 2.5, showAxes: true,
      pendingFile: '', dragging: false, error: '',
    }
  },
  beforeDestroy() {
    this.cancelUpload()
  },
  methods: {
    formatCount(value) { return counts.format(value) },
    leaveDropZone(event) {
      if (!event.currentTarget.contains(event.relatedTarget)) this.dragging = false
    },
    changeFile(event) {
      this.selectFiles(event.target.files)
      event.target.value = ''
    },
    dropFile(event) {
      this.dragging = false
      this.selectFiles(event.dataTransfer.files)
    },
    selectFiles(files) {
      if (!files.length) return
      this.cancelUpload()
      if (files.length !== 1) {
        this.error = '请一次上传一个点云文件。'
        return
      }
      const [file] = files
      const extension = /\.([^.]+)$/.exec(file.name.toLowerCase())?.[1]
      if (!pointCloudExtensions.includes(extension)) {
        this.error = '不支持这种点云文件格式。'
        return
      }
      if (file.size > maxPointCloudBytes) {
        this.error = '单个点云文件最多支持 128 MiB。'
        return
      }
      this.loadFile(file)
    },
    async loadFile(file) {
      const request = new AbortController()
      this._upload = request
      this.pendingFile = file.name
      this.error = ''
      try {
        const cloud = await fetchPointCloud(file, request.signal)
        if (this._upload !== request) return
        this.filename = file.name
        this.colorMode = cloud.colors ? 'original' : 'height'
        this.cloud = cloud
      } catch (error) {
        if (this._upload === request && error.name !== 'AbortError') this.error = error.message
      } finally {
        if (this._upload === request) {
          this._upload = null
          this.pendingFile = ''
        }
      }
    },
    cancelUpload() {
      this._upload?.abort()
      this._upload = null
      this.pendingFile = ''
    },
  },
}
</script>

<style scoped>
.cloud-page { display: grid; grid-template-columns: minmax(235px, 280px) minmax(0, 1fr); gap: 16px; align-items: start; }
.cloud-controls { display: grid; gap: 12px; }
.panel { min-width: 0; padding: 16px; border: 1px solid #dfe7f1; border-radius: 10px; background: #fff; }
h2 { margin: 0 0 12px; color: #15243b; font-size: 16px; }
.drop-zone {
  display: grid; justify-items: center; gap: 9px; padding: 16px 8px;
  border: 1px dashed #aabfd8; border-radius: 8px; background: #f4f8fe;
}
.drop-zone.dragging { border-color: #235a9f; background: #e7f2ff; }
.drop-zone i { color: #386ba8; font-size: 25px; }
.drop-zone p, .note { margin: 0; color: #52647d; font-size: 13px; }
.note { margin-top: 9px; }
button, select { padding: 6px 10px; border: 1px solid #cdd9e9; border-radius: 6px; font: inherit; }
button { cursor: pointer; }
.primary-button { border-color: #235a9f; color: #fff; background: #235a9f; }
.primary-button:hover { background: #1b497f; }
.secondary-button { color: #235a9f; background: #fff; }
.secondary-button:hover { background: #eff5ff; }
.field { display: grid; gap: 5px; margin: 10px 0; color: #435774; font-size: 13px; }
.field select { width: 100%; color: #172942; background: #fff; }
.field input[type='range'] { width: 100%; }
.checkbox { display: flex; align-items: center; gap: 6px; color: #435774; font-size: 13px; }
.upload-status { display: flex; align-items: center; justify-content: space-between; gap: 8px; margin-top: 9px; }
.upload-status span { overflow-wrap: anywhere; color: #435774; font-size: 13px; }
.upload-status button { flex: none; }
.error { margin: 9px 0 0; color: #a12629; font-size: 13px; }
.preview-heading { display: flex; align-items: start; justify-content: space-between; gap: 12px; margin-bottom: 12px; }
.preview-heading h2 { margin: 0; }
.preview-heading button { flex: none; }
.preview-title { min-width: 0; }
.filename { margin: 3px 0 0; overflow: hidden; color: #52647d; font-size: 13px; text-overflow: ellipsis; white-space: nowrap; }
.preview-stage { height: clamp(400px, 62vh, 760px); overflow: hidden; border-radius: 8px; background: #0f1d30; }
.empty-preview { display: grid; height: 100%; align-content: center; justify-items: center; color: #cadaed; text-align: center; }
.empty-preview i { color: #80b8e3; font-size: 30px; }
.empty-preview p { margin: 10px 14px 0; }
.preview-info { display: flex; flex-wrap: wrap; gap: 5px 18px; margin-top: 10px; color: #263c5a; font-size: 13px; }
@media (max-width: 960px) {
  .cloud-page { grid-template-columns: minmax(0, 1fr); }
  .preview-stage { height: clamp(340px, 56vh, 600px); }
}
</style>
