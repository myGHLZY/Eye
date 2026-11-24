<template>
  <el-container class="eye-layout">
    <el-aside width="228px" class="eye-sidebar">
      <div class="eye-brand">
        <span class="brand-icon"><i class="el-icon-s-data" aria-hidden="true"></i></span>
        <span>EyeChart</span>
      </div>

      <nav aria-label="主导航">
        <el-menu
          class="eye-menu"
          :default-active="activeMenu"
          :default-openeds="openedMenus"
          router
          unique-opened
          background-color="#14233b"
          text-color="#bfd0e4"
          active-text-color="#ffffff"
        >
          <template v-for="entry in navigation">
            <el-submenu v-if="entry.items" :key="`submenu-${entry.name}`" :index="entry.name">
              <template slot="title">
                <i :class="[entry.icon, 'nav-icon']" aria-hidden="true"></i>
                <span>{{ entry.title }}</span>
              </template>
              <template v-if="entry.name === 'database'">
                <el-submenu v-if="connections.length" key="saved-connections" index="database-connections">
                  <template slot="title">
                    <router-link
                      class="connection-link"
                      :to="{ name: 'data-sources' }"
                      exact
                      @click.native.stop
                    >数据库连接</router-link>
                  </template>
                  <el-menu-item
                    v-for="connection in connections"
                    :key="connection.id"
                    :index="connection.id"
                    :route="{ name: 'database-schema', params: { connectionId: connection.id } }"
                    :aria-current="activeMenu === connection.id ? 'page' : null"
                    :title="`${connection.database} · ${connection.host}:${connection.port} · ${connection.username}`"
                    class="nav-item database-menu-item"
                  >{{ connection.database }}</el-menu-item>
                </el-submenu>
                <el-menu-item
                  v-else
                  key="new-connection"
                  index="data-sources"
                  :route="{ name: 'data-sources' }"
                  :aria-current="activeMenu === 'data-sources' ? 'page' : null"
                  class="nav-item"
                >数据库连接</el-menu-item>
                <el-menu-item
                  index="database-views"
                  :route="{ name: 'database-views' }"
                  :aria-current="activeMenu === 'database-views' ? 'page' : null"
                  class="nav-item"
                >视图</el-menu-item>
              </template>
              <template v-else>
                <el-menu-item
                  v-for="item in entry.items"
                  :key="item.name"
                  :index="item.name"
                  :route="{ name: item.name }"
                  :aria-current="activeMenu === item.name ? 'page' : null"
                  class="nav-item"
                >{{ item.title }}</el-menu-item>
              </template>
            </el-submenu>

            <el-menu-item
              v-else
              :key="`menu-item-${entry.name}`"
              :index="entry.name"
              :route="{ name: entry.name }"
              :aria-current="activeMenu === entry.name ? 'page' : null"
              class="nav-item"
            >
              <i :class="[entry.icon, 'nav-icon']" aria-hidden="true"></i>
              <span>{{ entry.title }}</span>
            </el-menu-item>
          </template>
        </el-menu>
      </nav>
    </el-aside>

    <el-container direction="vertical" class="eye-content">
      <el-header height="64px" class="eye-header">
        <el-breadcrumb separator="/" aria-label="当前位置">
          <el-breadcrumb-item v-if="$route.meta.section">
            {{ $route.meta.section }}
          </el-breadcrumb-item>
          <el-breadcrumb-item>{{ pageLabel }}</el-breadcrumb-item>
          <el-breadcrumb-item v-if="showDatabaseDiagram">ER 图</el-breadcrumb-item>
        </el-breadcrumb>
      </el-header>

      <el-main class="eye-main" aria-labelledby="page-title">
        <div class="main-inner" :class="{ 'main-inner-wide': showDatabaseDiagram }">
          <div class="page-heading">
            <h1 id="page-title">{{ showDatabaseDiagram ? `${pageLabel} ER 图` : pageLabel }}</h1>
            <el-button
              v-if="databaseSchemaRoute"
              size="small"
              type="danger"
              plain
              :loading="disconnectingId === $route.params.connectionId"
              :disabled="Boolean(disconnectingId)"
              @click="disconnectCurrentDatabase"
            >断开连接</el-button>
          </div>
          <el-alert
            v-if="databaseSchemaRoute && disconnectError && disconnectError.id === $route.params.connectionId"
            class="connection-action-error"
            :title="disconnectError.message"
            type="error"
            :closable="false"
            show-icon
          />
          <router-view
            :key="databaseSchemaRoute ? $route.params.connectionId : (dataChartEditorRoute ? $route.params.chartId : undefined)"
            @connections-changed="refreshConnections"
          />
        </div>
      </el-main>

      <el-footer height="52px" class="eye-footer">Eye · 数据库可视化</el-footer>
    </el-container>
  </el-container>
</template>

<script>
import ElAlert from 'element-ui/lib/alert'
import ElAside from 'element-ui/lib/aside'
import ElBreadcrumb from 'element-ui/lib/breadcrumb'
import ElBreadcrumbItem from 'element-ui/lib/breadcrumb-item'
import ElButton from 'element-ui/lib/button'
import ElContainer from 'element-ui/lib/container'
import ElFooter from 'element-ui/lib/footer'
import ElHeader from 'element-ui/lib/header'
import ElMain from 'element-ui/lib/main'
import ElMenu from 'element-ui/lib/menu'
import ElMenuItem from 'element-ui/lib/menu-item'
import ElSubmenu from 'element-ui/lib/submenu'
import { disconnectDatabaseConnection, listDatabaseConnections } from '../api/database.js'
import { findChartExample, visualizationCategories } from '../data/chartExamples.js'

import 'element-ui/lib/theme-chalk/alert.css'
import 'element-ui/lib/theme-chalk/aside.css'
import 'element-ui/lib/theme-chalk/breadcrumb.css'
import 'element-ui/lib/theme-chalk/breadcrumb-item.css'
import 'element-ui/lib/theme-chalk/button.css'
import 'element-ui/lib/theme-chalk/container.css'
import 'element-ui/lib/theme-chalk/footer.css'
import 'element-ui/lib/theme-chalk/header.css'
import 'element-ui/lib/theme-chalk/icon.css'
import 'element-ui/lib/theme-chalk/main.css'
import 'element-ui/lib/theme-chalk/menu.css'
import 'element-ui/lib/theme-chalk/menu-item.css'
import 'element-ui/lib/theme-chalk/submenu.css'

const navigation = [
  {
    name: 'main',
    path: '',
    title: '工作台',
    icon: 'el-icon-house',
    component: () => import('./WorkspaceView.vue'),
  },
  {
    name: 'database',
    title: '数据库',
    icon: 'el-icon-coin',
    items: [
      {
        name: 'data-sources',
        path: 'database/sources',
        title: '数据库连接',
        component: () => import('./DatabaseConnectionView.vue'),
      },
      {
        name: 'database-views',
        path: 'database/views',
        title: '视图',
        component: () => import('./DatabaseViewsView.vue'),
      },
    ],
  },
  {
    name: 'visualization',
    title: '可视化',
    icon: 'el-icon-data-analysis',
    items: [
      {
        name: 'chart-showcase',
        path: 'visualization/showcase',
        title: '展示',
        component: () => import('./ChartShowcaseView.vue'),
      },
      {
        ...visualizationCategories.lines_bars_and_markers,
        component: () => import('./ChartTypesView.vue'),
      },
      {
        ...visualizationCategories.images_contours_and_fields,
        component: () => import('./ImagesContoursView.vue'),
      },
      {
        ...visualizationCategories.statistics,
        component: () => import('./StatisticsView.vue'),
      },
      {
        ...visualizationCategories.pie_and_polar_charts,
        component: () => import('./PiePolarView.vue'),
      },
      {
        ...visualizationCategories.subplots_axes_and_figures,
        component: () => import('./SubplotsAxesView.vue'),
      },
      {
        ...visualizationCategories.specialty_plots,
        component: () => import('./SpecialtyPlotsView.vue'),
      },
    ],
  },
  {
    name: 'eye-agent',
    path: 'eye-agent',
    title: 'EyeAgent',
    icon: 'el-icon-chat-dot-round',
    component: () => import('./EyeAgentView.vue'),
  },
  {
    name: 'settings',
    title: '系统设置',
    icon: 'el-icon-setting',
    items: [
      {
        name: 'preferences',
        path: 'settings/general',
        title: '通用设置',
        component: () => import('./GeneralSettingsView.vue'),
      },
      {
        name: 'service-config',
        path: 'settings/service',
        title: '服务配置',
        component: () => import('./ServiceSettingsView.vue'),
      },
    ],
  },
]

export const mainRoutes = [
  ...navigation.flatMap((entry) =>
    (entry.items || [entry]).map(({ name, path, title, component }) => ({
      name,
      path,
      component,
      meta: { title, section: entry.items ? entry.title : null },
    })),
  ),
  {
    name: 'database-schema',
    path: 'database/connections/:connectionId',
    component: () => import('./TableSchemaView.vue'),
    props: true,
    meta: { title: '数据库结构', section: '数据库连接' },
  },
  {
    path: 'database/schema',
    redirect: { name: 'data-sources' },
  },
  {
    name: 'chart-workbench',
    path: 'visualization/workbench/:chartId?',
    component: () => import('./ChartWorkbenchView.vue'),
    meta: { title: '图表工作台', section: '可视化', activeMenu: 'chart-types' },
  },
  {
    name: 'bar-chart-editor',
    path: 'visualization/bar-chart/:chartId',
    component: () => import('./BarChartEditorView.vue'),
    meta: { title: '制作柱状图', section: '可视化', activeMenu: 'chart-types' },
  },
  {
    name: 'pie-chart-editor',
    path: 'visualization/pie-chart/:chartId',
    component: () => import('./PieChartEditorView.vue'),
    meta: { title: '制作饼图', section: '可视化', activeMenu: 'pie-polar-charts' },
  },
  {
    name: 'special-chart-editor',
    path: 'visualization/special-chart/:chartId(radar_chart|sankey_basics|specialty_heatmap)',
    component: () => import('./SpecialChartEditorView.vue'),
    meta: { title: '制作图表', section: '可视化', activeMenu: 'specialty-charts' },
  },
  {
    name: 'cartesian-chart-editor',
    path: 'visualization/cartesian-chart/:chartId(simple_plot|scatter_with_legend|scatter_hist|stackplot_demo)',
    component: () => import('./SpecialChartEditorView.vue'),
    meta: { title: '制作图表', section: '可视化', activeMenu: 'chart-types' },
  },
  {
    name: 'chart-editor',
    path: 'visualization/chart-editor/:chartId(hist|boxplot_demo|bar_of_pie|errorbar|confidence_ellipse|histogram_cumulative|hexbin_demo|violinplot)',
    component: () => import('./SpecialChartEditorView.vue'),
    meta: { title: '制作图表', section: '可视化', activeMenu: 'statistics-charts' },
  },
  {
    name: 'subplot-chart-editor',
    path: 'visualization/subplot-chart/:chartId(subplot|subplot_overlay)',
    component: () => import('./SubplotChartEditorView.vue'),
    meta: { title: '制作多子图组合', section: '可视化', activeMenu: 'subplot-charts' },
  },
]

export default {
  name: 'MainView',
  components: {
    ElAlert,
    ElAside,
    ElBreadcrumb,
    ElBreadcrumbItem,
    ElButton,
    ElContainer,
    ElFooter,
    ElHeader,
    ElMain,
    ElMenu,
    ElMenuItem,
    ElSubmenu,
  },
  data() {
    return {
      navigation,
      connections: [],
      disconnectingId: '',
      disconnectError: null,
    }
  },
  computed: {
    dataChartEditorRoute() {
      return ['special-chart-editor', 'cartesian-chart-editor', 'chart-editor', 'subplot-chart-editor'].includes(this.$route.name)
    },
    databaseSchemaRoute() {
      return this.$route.name === 'database-schema'
    },
    showDatabaseDiagram() {
      return this.databaseSchemaRoute && this.$route.query.view === 'er'
    },
    openedMenus() {
      if (this.databaseSchemaRoute || this.$route.name === 'data-sources') {
        return this.connections.length ? ['database', 'database-connections'] : ['database']
      }
      const parent = this.navigation.find(entry => entry.items?.some(item => item.name === this.activeMenu))
      return parent ? [parent.name] : []
    },
    pageLabel() {
      if (this.dataChartEditorRoute) {
        const chart = findChartExample(this.$route.params.chartId)
        if (chart) return '制作' + chart.title
      }
      if (this.databaseSchemaRoute) {
        const connection = this.connections.find(item => item.id === this.$route.params.connectionId)
        if (connection) return connection.database
      }
      return this.$route.meta.title
    },
    activeMenu() {
      if (this.databaseSchemaRoute) return this.$route.params.connectionId
      if (this.$route.meta.activeMenu) {
        const chart = findChartExample(this.$route.params.chartId)
        return chart?.galleryRoute || this.$route.meta.activeMenu
      }
      return this.$route.name
    },
  },
  created() {
    this._connectionRequest = 0
    this.refreshConnections()
  },
  methods: {
    async disconnectCurrentDatabase() {
      if (this.disconnectingId) return

      const id = this.$route.params.connectionId
      this.disconnectingId = id
      this.disconnectError = null
      try {
        await disconnectDatabaseConnection(id)
        this.connections = this.connections.filter(connection => connection.id !== id)
        this.refreshConnections()
        if (this.databaseSchemaRoute && this.$route.params.connectionId === id) {
          await this.$router.replace({ name: 'data-sources' })
        }
      } catch (error) {
        this.disconnectError = { id, message: error.message }
      } finally {
        this.disconnectingId = ''
      }
    },
    async refreshConnections() {
      const request = ++this._connectionRequest
      try {
        const { connections } = await listDatabaseConnections()
        if (request === this._connectionRequest) this.connections = connections
      } catch {
        // 数据库连接页负责展示后端不可用时的错误。
      }
    },
  },
}
</script>

<style scoped>
.eye-layout {
  min-height: 100vh;
  background: #f5f7fc;
}

.eye-sidebar {
  position: sticky;
  top: 0;
  align-self: flex-start;
  height: 100vh;
  color: #fff;
  background: #14233b;
}

.eye-brand {
  display: flex;
  align-items: center;
  gap: 12px;
  height: 64px;
  margin: 0 20px 10px;
  border-bottom: 1px solid #30415c;
  font-size: 21px;
  font-weight: 650;
}

.brand-icon {
  display: grid;
  place-items: center;
  width: 34px;
  height: 34px;
  border-radius: 8px;
  font-size: 18px;
}

.brand-icon {
  color: #dbeafe;
  background: #263f63;
}

.eye-menu {
  border-right: 0;
}

.nav-icon {
  color: inherit;
}

.connection-link {
  display: block;
  color: inherit;
  text-decoration: none;
}

.connection-link[aria-current='page'] {
  color: #fff;
  font-weight: 600;
}

.database-menu-item {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.nav-item.is-active {
  background: #284973 !important;
  box-shadow: inset 3px 0 #7cb8ff;
}

.eye-content {
  min-width: 0;
}

.eye-header,
.eye-footer {
  display: flex;
  align-items: center;
  padding: 0 clamp(16px, 4vw, 40px);
  background: #fff;
}

.eye-header {
  border-bottom: 1px solid #e1e8f1;
}

.eye-footer {
  border-top: 1px solid #e1e8f1;
  color: #52647d;
  font-size: 13px;
}

.eye-main {
  padding: clamp(20px, 4vw, 40px);
}

.main-inner {
  max-width: 1120px;
  margin: 0 auto;
}

.main-inner-wide {
  max-width: none;
}

.page-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 8px 16px;
  margin-bottom: 8px;
}

.connection-action-error {
  margin-bottom: 12px;
}

h1 {
  margin: 0;
  overflow-wrap: anywhere;
  font-size: clamp(26px, 3.4vw, 34px);
  letter-spacing: -0.02em;
}

@media (max-width: 680px) {
  .eye-layout {
    flex-direction: column;
  }

  .eye-sidebar {
    position: static;
    width: 100% !important;
    height: auto;
  }

  .eye-brand {
    height: 52px;
    margin-bottom: 0;
  }

  .eye-menu {
    max-height: 230px;
    overflow-y: auto;
  }
}
</style>
