<template>
  <section class="chart-workbench">
    <router-link :to="{ name: chart ? chart.galleryRoute : 'chart-types' }" class="gallery-link">
      <i class="el-icon-arrow-left" aria-hidden="true"></i> 返回图例图库
    </router-link>

    <template v-if="chart">
      <div class="chart-heading">
        <h2>{{ chart.title }}</h2>
        <el-button v-if="chart.editorRoute" type="primary" @click="openChartEditor">
          制作{{ chart.title }}
        </el-button>
      </div>

      <div class="workbench-content">
        <el-card shadow="never" class="workbench-card">
          <div slot="header" class="preview-heading">
            <h3>图例预览</h3>
            <a v-if="chart.source" :href="chart.source" target="_blank" rel="noopener noreferrer">查看示例代码</a>
          </div>
          <div class="workbench-preview" :class="{ 'pending-preview': !chart.editorRoute }">
            <img :src="chart.image" :alt="chart.title + '示例'" class="plot-preview">
          </div>
        </el-card>

        <el-card v-if="chart.editorRoute" shadow="never" class="workbench-card fields-card">
          <h3>所需字段</h3>
          <p>{{ chart.fields }}</p>
        </el-card>
        <module-overview v-else :description="'所需字段：' + chart.fields">
          <li>选择数据表或查询结果</li>
          <li>将数据列映射到当前图表字段</li>
          <li>预览 Python 生成的图表</li>
        </module-overview>
      </div>
    </template>

    <p v-else class="empty-message">
      {{ $route.params.chartId ? '图例不存在，请返回图库重新选择。' : '请先从图库选择一种图表。' }}
    </p>
  </section>
</template>

<script>
import ElButton from 'element-ui/lib/button'
import ElCard from 'element-ui/lib/card'
import ModuleOverview from '../components/ModuleOverview.vue'
import { findChartExample } from '../data/chartExamples.js'

import 'element-ui/lib/theme-chalk/button.css'
import 'element-ui/lib/theme-chalk/card.css'
import '../assets/chart-preview.css'

export default {
  name: 'ChartWorkbenchView',
  components: { ElButton, ElCard, ModuleOverview },
  computed: {
    chart() {
      return findChartExample(this.$route.params.chartId)
    },
  },
  methods: {
    openChartEditor() {
      this.$router.push({ name: this.chart.editorRoute, params: { chartId: this.chart.id } })
    },
  },
}
</script>

<style scoped>
.gallery-link,
.preview-heading a {
  color: #235a9f;
  font-size: 14px;
}

.gallery-link {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  margin: 4px 0 14px;
  text-decoration: none;
}

.gallery-link:hover {
  text-decoration: underline;
}

.chart-heading,
.preview-heading {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 10px 16px;
}

.chart-heading {
  margin-bottom: 16px;
}

.chart-heading h2 {
  margin: 0;
  color: #14233b;
  font-size: 23px;
}

.workbench-content {
  display: grid;
  grid-template-columns: minmax(0, 2.3fr) minmax(220px, 1fr);
  gap: 18px;
  align-items: start;
}

.workbench-card {
  min-width: 0;
  border-color: #dfe7f1;
  border-radius: 10px;
}

.workbench-card h3 {
  margin: 0;
  color: #14233b;
  font-size: 16px;
}

.workbench-preview {
  display: grid;
  place-items: center;
  min-height: 200px;
  overflow: hidden;
  border-radius: 6px;
  background: #f8faff;
}

.plot-preview {
  display: block;
  max-width: 100%;
  max-height: 420px;
  object-fit: contain;
}

.fields-card p {
  margin: 10px 0 0;
  color: #52647d;
  line-height: 1.6;
}

.empty-message {
  margin: 0;
  color: #52647d;
}

@media (max-width: 960px) {
  .workbench-content {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
