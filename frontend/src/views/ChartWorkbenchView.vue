<template>
  <section>
    <router-link :to="{ name: chart ? chart.galleryRoute : 'chart-types' }" class="gallery-link">
      <i class="el-icon-arrow-left" aria-hidden="true"></i> 返回图例图库
    </router-link>

    <template v-if="chart">
      <el-card shadow="never" class="preview-card">
        <div class="preview-heading">
          <h2>{{ chart.title }}</h2>
          <a :href="chart.source" target="_blank" rel="noopener noreferrer">查看示例代码</a>
        </div>
        <div class="workbench-preview pending-preview">
          <img :src="chart.image" :alt="chart.title + '示例'" class="plot-preview">
        </div>
      </el-card>

      <module-overview :description="'所需字段：' + chart.fields">
        <li>选择数据表或查询结果</li>
        <li>将数据列映射到当前图表字段</li>
        <li>预览 Python 生成的图表</li>
      </module-overview>
    </template>

    <p v-else class="empty-message">
      {{ $route.params.chartId ? '图例不存在，请返回图库重新选择。' : '请先从图库选择一种图表。' }}
    </p>
  </section>
</template>

<script>
import ElCard from 'element-ui/lib/card'
import ModuleOverview from '../components/ModuleOverview.vue'
import { findChartExample } from '../data/chartExamples.js'

import 'element-ui/lib/theme-chalk/card.css'
import '../assets/chart-preview.css'

export default {
  name: 'ChartWorkbenchView',
  components: { ElCard, ModuleOverview },
  computed: {
    chart() {
      return findChartExample(this.$route.params.chartId)
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
  display: inline-block;
  margin-bottom: 18px;
  text-decoration: none;
}

.gallery-link:hover {
  text-decoration: underline;
}

.preview-card {
  max-width: 720px;
  margin-bottom: 18px;
  border-color: #dfe7f1;
  border-radius: 10px;
}

.preview-heading {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.preview-heading h2 {
  margin: 0;
  font-size: 18px;
}

.workbench-preview {
  margin-top: 12px;
}

.plot-preview {
  display: block;
  max-width: 100%;
  max-height: 390px;
  margin: 0 auto;
  object-fit: contain;
}

.empty-message {
  margin: 0;
  color: #52647d;
}
</style>
