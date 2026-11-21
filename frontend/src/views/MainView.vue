<template>
  <el-container class="eye-layout">
    <el-aside width="228px" class="eye-sidebar">
      <div class="eye-brand">
        <span class="brand-icon"><i class="el-icon-s-data" aria-hidden="true"></i></span>
        <span>Eye</span>
      </div>

      <nav aria-label="主导航">
        <el-menu
          class="eye-menu"
          :default-active="activeMenu"
          router
          unique-opened
          background-color="#14233b"
          text-color="#bfd0e4"
          active-text-color="#ffffff"
        >
          <template v-for="entry in navigation">
            <el-submenu v-if="entry.items" :key="entry.name" :index="entry.name">
              <template slot="title">
                <i :class="[entry.icon, 'nav-icon']" aria-hidden="true"></i>
                <span>{{ entry.title }}</span>
              </template>
              <el-menu-item
                v-for="item in entry.items"
                :key="item.name"
                :index="item.name"
                :route="{ name: item.name }"
                :aria-current="activeMenu === item.name ? 'page' : null"
                class="nav-item"
              >
                {{ item.title }}
              </el-menu-item>
            </el-submenu>

            <el-menu-item
              v-else
              :key="entry.name"
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
          <el-breadcrumb-item>{{ $route.meta.title }}</el-breadcrumb-item>
        </el-breadcrumb>
      </el-header>

      <el-main class="eye-main" aria-labelledby="page-title">
        <div class="main-inner">
          <h1 id="page-title">{{ $route.meta.title }}</h1>
          <router-view />
        </div>
      </el-main>

      <el-footer height="52px" class="eye-footer">Eye · 数据库可视化</el-footer>
    </el-container>
  </el-container>
</template>

<script>
import ElAside from 'element-ui/lib/aside'
import ElBreadcrumb from 'element-ui/lib/breadcrumb'
import ElBreadcrumbItem from 'element-ui/lib/breadcrumb-item'
import ElContainer from 'element-ui/lib/container'
import ElFooter from 'element-ui/lib/footer'
import ElHeader from 'element-ui/lib/header'
import ElMain from 'element-ui/lib/main'
import ElMenu from 'element-ui/lib/menu'
import ElMenuItem from 'element-ui/lib/menu-item'
import ElSubmenu from 'element-ui/lib/submenu'
import { findChartExample, visualizationCategories } from '../data/chartExamples.js'

import 'element-ui/lib/theme-chalk/aside.css'
import 'element-ui/lib/theme-chalk/breadcrumb.css'
import 'element-ui/lib/theme-chalk/breadcrumb-item.css'
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
        title: '数据源管理',
        component: () => import('./DataSourcesView.vue'),
      },
      {
        name: 'table-schema',
        path: 'database/schema',
        title: '表与关系',
        component: () => import('./TableSchemaView.vue'),
      },
      {
        name: 'data-preview',
        path: 'database/preview',
        title: '数据预览',
        component: () => import('./DataPreviewView.vue'),
      },
    ],
  },
  {
    name: 'visualization',
    title: '可视化',
    icon: 'el-icon-data-analysis',
    items: [
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
    name: 'chart-workbench',
    path: 'visualization/workbench/:chartId?',
    component: () => import('./ChartWorkbenchView.vue'),
    meta: { title: '图表工作台', section: '可视化', activeMenu: 'chart-types' },
  },
]

export default {
  name: 'MainView',
  components: {
    ElAside,
    ElBreadcrumb,
    ElBreadcrumbItem,
    ElContainer,
    ElFooter,
    ElHeader,
    ElMain,
    ElMenu,
    ElMenuItem,
    ElSubmenu,
  },
  data() {
    return { navigation }
  },
  computed: {
    activeMenu() {
      if (this.$route.name === 'chart-workbench') {
        const chart = findChartExample(this.$route.params.chartId)
        return chart?.galleryRoute || this.$route.meta.activeMenu
      }
      return this.$route.name
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

h1 {
  margin: 0 0 8px;
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
