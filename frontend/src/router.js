import { createRouter, createWebHistory } from 'vue-router'
import Dashboard from './views/Dashboard.vue'

const routes = [
  { path: '/', name: 'Dashboard', component: Dashboard },
  { path: '/products', name: 'Products', component: () => import('./views/Products.vue') },
  { path: '/orders', name: 'Orders', component: () => import('./views/Orders.vue') },
  { path: '/scans', name: 'Scans', component: () => import('./views/Scans.vue') },
  { path: '/camera', name: 'Camera', component: () => import('./views/Camera.vue') },
]

export default createRouter({
  history: createWebHistory(),
  routes,
})
