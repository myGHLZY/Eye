<template>
  <section>
    <p class="workspace-description">从查看数据表和关系开始，再选择合适的图表展示分析结果。</p>

    <div class="shortcut-grid" aria-label="常用入口">
      <el-card v-for="item in shortcuts" :key="item.name" class="shortcut-card" shadow="hover">
        <div class="shortcut-icon">
          <i :class="item.icon" aria-hidden="true"></i>
        </div>
        <h2>{{ item.title }}</h2>
        <p>{{ item.description }}</p>
        <router-link
          class="shortcut-link"
          :to="{ name: item.name }"
          :aria-label="'打开' + item.title"
        >
          打开<i class="el-icon-arrow-right" aria-hidden="true"></i>
        </router-link>
      </el-card>
    </div>
  </section>
</template>

<script>
import ElCard from 'element-ui/lib/card'

import 'element-ui/lib/theme-chalk/card.css'

const shortcuts = [
  {
    name: 'data-sources',
    title: '数据库连接',
    icon: 'el-icon-connection',
    description: '测试并保存 MySQL 连接。',
  },
  {
    name: 'table-schema',
    title: '表与关系',
    icon: 'el-icon-share',
    description: '查看字段、主键和外键，了解数据表之间的关系。',
  },
  {
    name: 'chart-types',
    title: '图例图库',
    icon: 'el-icon-data-analysis',
    description: '浏览五类 Matplotlib 图例，选择图表进入工作台。',
  },
  {
    name: 'preferences',
    title: '通用设置',
    icon: 'el-icon-setting',
    description: '集中管理 Eye 的显示偏好。',
  },
]

export default {
  name: 'WorkspaceView',
  components: { ElCard },
  data() {
    return { shortcuts }
  },
}
</script>

<style scoped>
h2,
p {
  margin: 0;
}

h2 {
  font-size: 17px;
}

p {
  color: #52647d;
  font-size: 14px;
}

.workspace-description {
  margin-bottom: 26px;
}

.shortcut-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(min(100%, 220px), 1fr));
  gap: 16px;
}

.shortcut-card {
  border-color: #dfe7f1;
  border-radius: 10px;
}

.shortcut-icon {
  display: grid;
  place-items: center;
  width: 34px;
  height: 34px;
  margin-bottom: 12px;
  border-radius: 8px;
  color: #235a9f;
  background: #ebf3ff;
  font-size: 18px;
}

.shortcut-card p {
  margin-top: 8px;
  min-height: 42px;
}

.shortcut-link {
  display: inline-block;
  padding: 9px 0;
  color: #235a9f;
  font-size: 14px;
  text-decoration: none;
}

.shortcut-link:hover {
  text-decoration: underline;
}

.shortcut-link i {
  margin-left: 4px;
}
</style>
