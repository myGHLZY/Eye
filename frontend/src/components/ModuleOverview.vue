<template>
  <section>
    <p class="module-description">{{ description }}</p>
    <el-card class="module-card" shadow="never">
      <el-tag size="small" type="info" effect="plain">待接入</el-tag>
      <h2>功能规划</h2>
      <ul><slot /></ul>
    </el-card>
  </section>
</template>

<script>
import ElCard from 'element-ui/lib/card'
import ElTag from 'element-ui/lib/tag'

import 'element-ui/lib/theme-chalk/card.css'
import 'element-ui/lib/theme-chalk/tag.css'

export default {
  name: 'ModuleOverview',
  components: { ElCard, ElTag },
  props: {
    description: { type: String, required: true },
  },
}
</script>

<style scoped>
.module-description,
.module-card ul {
  color: #52647d;
  font-size: 14px;
}

.module-description {
  margin: 0 0 26px;
}

.module-card {
  max-width: 720px;
  border-color: #dfe7f1;
  border-radius: 10px;
}

.module-card h2 {
  margin: 12px 0 0;
  font-size: 17px;
}

.module-card ul {
  margin: 10px 0 0;
  padding-left: 20px;
  line-height: 1.9;
}
</style>
