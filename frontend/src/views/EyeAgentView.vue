<template>
  <module-overview description="通过自然语言提出分析问题，获取数据整理和图表建议。">
    <li>描述想分析的问题和数据范围</li>
    <li>获取可能的表关联、计算指标和图表建议</li>
    <li>确认方案后预览 Python 生成的图表</li>
  </module-overview>
</template>

<script>
import ModuleOverview from '../components/ModuleOverview.vue'

export default {
  name: 'EyeAgentView',
  components: { ModuleOverview },
}
</script>
