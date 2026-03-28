<script setup>
import { onMounted, onUnmounted } from 'vue'
import { useDashboardStore } from './stores/dashboard'
import Navbar from './components/Navbar.vue'
import ToastContainer from './components/ToastContainer.vue'

const store = useDashboardStore()

onMounted(() => {
  store.initSocket()
  store.fetchDashboard()
  store.fetchCamera()
})

onUnmounted(() => {
  store.destroySocket()
})
</script>

<template>
  <ToastContainer />
  <Navbar />
  <main class="max-w-7xl mx-auto px-8 py-8">
    <router-view />
  </main>
  <footer class="max-w-7xl mx-auto px-6 py-6 flex items-center justify-between text-[11px] text-navy-400 border-t border-navy-100 mt-4">
    <p>SmartShelf &middot; powered by <span class="font-medium text-navy-600">DATA UNIT AG</span></p>
    <p>Hackathon Baden 2026</p>
  </footer>
</template>
