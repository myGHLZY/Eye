<template>
  <module-overview description="集中管理 Eye 的显示偏好。">
    <li>设置界面主题与日期显示格式</li>
    <li>设置数据预览的默认每页条数</li>
  </module-overview>
</template>

<script>
import ModuleOverview from '../components/ModuleOverview.vue'

export default {
  name: 'GeneralSettingsView',
  components: { ModuleOverview },
}
</script>
