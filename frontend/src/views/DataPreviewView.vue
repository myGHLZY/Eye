<template>
  <module-overview description="查看表中的样例记录，确认字段内容和数据质量。">
    <li>分页预览所选表的数据</li>
    <li>按字段筛选和排序</li>
  </module-overview>
</template>

<script>
import ModuleOverview from '../components/ModuleOverview.vue'

export default {
  name: 'DataPreviewView',
  components: { ModuleOverview },
}
</script>
