<script setup>
import { computed } from 'vue'
import { useDashboardStore } from '../stores/dashboard'
import { Activity, ScanLine, ShoppingCart, Check } from 'lucide-vue-next'

const store = useDashboardStore()

function formatTime(dateStr) {
  const d = new Date(dateStr)
  return d.toLocaleDateString('de-CH') + ' ' + d.toLocaleTimeString('de-CH', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

const criticalCount = computed(() => store.scans.filter(s => {
  const p = store.productMap[s.prod_id]
  return p && s.count <= p.min_qty
}).length)
</script>

<template>
  <div class="flex items-center justify-between mb-5">
    <div class="section-header">
      <div class="icon-wrap bg-violet-50">
        <Activity class="w-4.5 h-4.5 text-violet-600" />
      </div>
      <div>
        <h2 class="text-lg font-semibold text-navy-900 m-0">Scan-Verlauf</h2>
        <p class="text-[11px] text-navy-400">{{ store.scans.length }} Einträge &middot; Letzte 50 Scans</p>
      </div>
    </div>
    <div class="flex items-center gap-2">
      <span class="badge" style="background: #f5f3ff; color: #7c3aed;">{{ store.scans.length }} Scans</span>
      <span v-if="criticalCount > 0" class="badge badge-low">{{ criticalCount }} Kritisch</span>
    </div>
  </div>

  <div class="card">
    <div class="overflow-x-auto">
      <table class="w-full text-sm">
        <thead>
          <tr>
            <th class="text-left py-3 px-5">Zeitpunkt</th>
            <th class="text-left py-3 px-4">Regal</th>
            <th class="text-left py-3 px-4">Produkt</th>
            <th class="text-right py-3 px-4">Anzahl</th>
            <th class="text-right py-3 px-4">Min</th>
            <th class="text-left py-3 px-5">Status</th>
            <th class="text-center py-3 px-4">Bestellung</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="s in store.scans" :key="s.id"
            class="data-row border-b border-navy-100">
            <td class="py-3 px-5 text-navy-600 text-[13px]">{{ formatTime(s.scanned_at) }}</td>
            <td class="py-3 px-4">
              <span class="font-mono text-[11px] bg-navy-50 text-navy-600 px-1.5 py-0.5 rounded font-medium">{{ s.shelf_id }}</span>
            </td>
            <td class="py-3 px-4">
              <span class="text-navy-900 font-medium text-[13px]">{{ store.productMap[s.prod_id]?.prod_name || s.prod_id }}</span>
              <span class="text-navy-400 text-[11px] ml-1 font-mono">{{ s.prod_id }}</span>
            </td>
            <td class="py-3 px-4 text-right font-mono font-semibold text-[14px]"
              :class="store.productMap[s.prod_id] && s.count <= store.productMap[s.prod_id].min_qty ? 'text-red-600' : 'text-emerald-600'">
              {{ s.count }}
            </td>
            <td class="py-3 px-4 text-right text-navy-400 text-[13px]">{{ store.productMap[s.prod_id]?.min_qty ?? '-' }}</td>
            <td class="py-3 px-5">
              <span class="badge"
                :class="store.productMap[s.prod_id] && s.count <= store.productMap[s.prod_id].min_qty ? 'badge-low' : 'badge-ok'">
                {{ store.productMap[s.prod_id] && s.count <= store.productMap[s.prod_id].min_qty ? 'Kritisch' : 'OK' }}
              </span>
            </td>
            <td class="py-3 px-4 text-center">
              <span v-if="store.orders.some(o => o.prod_id === s.prod_id && o.status === 'PENDING')" class="badge badge-pending">
                <ShoppingCart class="w-3 h-3 inline -mt-0.5" /> Bestellt
              </span>
              <span v-else-if="store.orders.some(o => o.prod_id === s.prod_id && o.status === 'DELIVERED')" class="badge badge-ok">
                <Check class="w-3 h-3 inline -mt-0.5" /> Geliefert
              </span>
              <span v-else class="text-navy-300 text-[12px]">&ndash;</span>
            </td>
          </tr>
          <tr v-if="!store.scans.length">
            <td colspan="7" class="py-10 text-center">
              <Activity class="w-8 h-8 text-navy-300 mx-auto mb-3" />
              <p class="text-navy-500 text-sm font-medium">Keine Scan-Daten vorhanden</p>
              <p class="text-navy-400 text-xs mt-1">Scans erscheinen automatisch nach Erkennung</p>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
