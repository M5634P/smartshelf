<script setup>
import { useDashboardStore } from '../stores/dashboard'
import { LayoutDashboard, Package, ClipboardList, Activity, Camera, RefreshCw } from 'lucide-vue-next'

const store = useDashboardStore()

function formatTime(date) {
  if (!date) return ''
  return date.toLocaleTimeString('de-CH', { hour: '2-digit', minute: '2-digit' }) + ' Uhr'
}

const navItems = [
  { path: '/', label: 'Dashboard', icon: LayoutDashboard },
  { path: '/products', label: 'Produkte', icon: Package },
  { path: '/orders', label: 'Bestellungen', icon: ClipboardList },
  { path: '/scans', label: 'Scans', icon: Activity },
  { path: '/camera', label: 'Kamera', icon: Camera },
]
</script>

<template>
  <nav class="topbar px-6 lg:px-8 py-3">
    <div class="max-w-7xl mx-auto flex items-center justify-between">
      <div class="flex items-center gap-4">
        <div class="flex items-center gap-2.5">
          <img src="/logo-dataunit.png" alt="DataUnit Logo" class="h-8 w-auto" />
          <div class="hidden sm:block">
            <h1 class="text-white text-[15px] font-semibold tracking-tight m-0" style="font-family: var(--font-heading);">SmartShelf</h1>
          </div>
        </div>
        <div class="hidden lg:block h-5 w-px bg-white/10"></div>
        <div class="hidden lg:flex items-center gap-1.5 text-xs">
          <span class="w-1.5 h-1.5 rounded-full"
            :class="store.connected ? 'bg-emerald-400 pulse-dot' : 'bg-amber-400'"></span>
          <span class="text-navy-400 text-[11px]">
            {{ store.connected ? 'Verbunden' : 'Verbinde...' }}
          </span>
        </div>
      </div>

      <div class="flex items-center gap-4">
        <div class="hidden md:flex items-center gap-1">
          <router-link
            v-for="item in navItems"
            :key="item.path"
            :to="item.path"
            class="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-[13px] font-medium transition-colors"
            :class="$route.path === item.path
              ? 'bg-white/10 text-white'
              : 'text-navy-400 hover:text-navy-200'"
          >
            <component :is="item.icon" class="w-3.5 h-3.5" />
            <span class="hidden lg:inline">{{ item.label }}</span>
          </router-link>
        </div>

        <div class="flex items-center gap-2.5">
          <span class="text-navy-500 text-[11px] hidden lg:block">{{ formatTime(store.lastUpdate) }}</span>
          <button @click="store.fetchDashboard()" class="btn-accent px-3 py-1.5 rounded-md text-[12px] font-medium flex items-center gap-1.5">
            <RefreshCw class="w-3 h-3" :class="{ 'animate-spin': store.loading }" />
            Sync
          </button>
        </div>
      </div>
    </div>
  </nav>
</template>
