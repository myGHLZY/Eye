<template>
  <module-overview description="管理用于分析的数据库连接。">
    <li>选择已有 MySQL 数据源</li>
    <li>配置连接参数并测试连通性</li>
  </module-overview>
</template>

<script>
import ModuleOverview from '../components/ModuleOverview.vue'

export default {
  name: 'DataSourcesView',
  components: { ModuleOverview },
}
</script>
