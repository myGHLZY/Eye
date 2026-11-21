import Vue from 'vue'
import 'element-ui/lib/theme-chalk/base.css'
import App from './App.vue'
import router from './router/index.js'

new Vue({
  router,
  render: (createElement) => createElement(App),
}).$mount('#app')
