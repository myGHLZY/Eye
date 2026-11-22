import Vue from 'vue'
import VueRouter from 'vue-router'
import MainView, { mainRoutes } from '../views/MainView.vue'

Vue.use(VueRouter)

export default new VueRouter({
  routes: [{ path: '/', component: MainView, children: mainRoutes }],
  scrollBehavior(_to, _from, savedPosition) {
    return savedPosition || { x: 0, y: 0 }
  },
})
