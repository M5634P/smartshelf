<script setup>
defineProps({
  label: String,
  value: [String, Number],
  sub: String,
  bgColor: { type: String, default: 'bg-navy-50' },
  valueColor: { type: String, default: 'text-navy-900' },
  accentGradient: { type: String, default: '' },
})
</script>

<template>
  <div class="card p-5">
    <div class="flex items-center justify-between mb-3">
      <p class="text-[11px] font-semibold uppercase tracking-wide text-navy-400">{{ label }}</p>
      <div class="stat-card-icon" :class="bgColor">
        <slot name="icon" />
      </div>
    </div>
    <p class="text-3xl font-bold leading-none" :class="valueColor">{{ value }}</p>
    <p class="text-xs text-navy-400 mt-1.5">{{ sub }}</p>
  </div>
</template>
