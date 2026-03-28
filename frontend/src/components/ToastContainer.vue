<script setup>
import { useDashboardStore } from '../stores/dashboard'

const store = useDashboardStore()
</script>

<template>
  <div class="fixed top-6 right-6 z-50 flex flex-col gap-3">
    <div
      v-for="toast in store.toasts"
      :key="toast.id"
      class="toast-enter px-6 py-3.5 rounded-lg text-sm font-medium shadow-lg"
      :class="toast.type === 'success' ? 'bg-navy-900 text-white' : 'bg-red-600 text-white'"
    >
      {{ toast.message }}
    </div>
  </div>
</template>
