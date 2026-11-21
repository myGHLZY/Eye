<template>
  <module-overview description="查看字段、主键和外键，了解数据表之间的关系。">
    <li>浏览数据库中的表与字段类型</li>
    <li>查看主外键和表关系图</li>
  </module-overview>
</template>

<script>
import ModuleOverview from '../components/ModuleOverview.vue'

export default {
  name: 'TableSchemaView',
  components: { ModuleOverview },
}
</script>
