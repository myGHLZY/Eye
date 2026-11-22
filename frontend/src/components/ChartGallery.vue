<template>
  <section aria-labelledby="page-title">
    <p class="gallery-description">彩色图例已支持制作。点击图例打开对应页面。</p>

    <div class="gallery-grid">
      <router-link
        v-for="chart in charts"
        :key="chart.id"
        :to="{ name: chart.id === 'subplot_overlay' ? chart.editorRoute : 'chart-workbench', params: { chartId: chart.id } }"
        :aria-label="'打开' + chart.title"
        class="chart-card"
      >
        <div class="chart-image" :class="{ 'pending-preview': !chart.editorRoute }">
          <img :src="chart.image" :alt="chart.title + '预览'" loading="lazy" decoding="async">
        </div>
        <span class="chart-title">{{ chart.title }}</span>
      </router-link>
    </div>
  </section>
</template>

<script>
import { chartExamples } from '../data/chartExamples.js'
import '../assets/chart-preview.css'

export default {
  name: 'ChartGallery',
  props: {
    category: { type: String, required: true },
  },
  computed: {
    charts() {
      return chartExamples.filter(chart => chart.category === this.category)
        .sort((left, right) => Number(Boolean(right.editorRoute)) - Number(Boolean(left.editorRoute)))
    },
  },
}
</script>

<style scoped>
.gallery-description {
  margin: 0 0 24px;
  color: #52647d;
  font-size: 14px;
}

.gallery-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(min(100%, 228px), 1fr));
  gap: 16px;
}

.chart-card {
  display: flex;
  min-width: 0;
  flex-direction: column;
  overflow: hidden;
  border: 1px solid #dfe7f1;
  border-radius: 10px;
  color: #17233b;
  background: #fff;
  text-decoration: none;
  transition: border-color 150ms, box-shadow 150ms;
}

.chart-card:hover,
.chart-card:focus-visible {
  border-color: #80a9dd;
  box-shadow: 0 5px 15px #1c35511a;
}

.chart-card:focus-visible {
  outline: 2px solid #235a9f;
  outline-offset: 2px;
}

.chart-image {
  box-sizing: border-box;
  display: flex;
  align-items: center;
  justify-content: center;
  aspect-ratio: 4 / 3;
  padding: 12px;
  border-bottom: 1px solid #edf0f5;
}

.chart-image img {
  width: 100%;
  height: 100%;
  min-width: 0;
  object-fit: contain;
}

.chart-title {
  display: flex;
  align-items: center;
  min-height: 44px;
  padding: 0 14px;
  font-size: 14px;
  font-weight: 600;
}
</style>
