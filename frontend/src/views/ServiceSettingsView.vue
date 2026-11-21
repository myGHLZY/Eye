<template>
  <module-overview description="管理 Eye 与 Flask 服务之间的连接参数。">
    <li>配置后端服务地址</li>
    <li>调整接口请求超时时间</li>
  </module-overview>
</template>

<script>
import ModuleOverview from '../components/ModuleOverview.vue'

export default {
  name: 'ServiceSettingsView',
  components: { ModuleOverview },
}
</script>
