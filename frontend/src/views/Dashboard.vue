<script setup>
import { useDashboardStore } from '../stores/dashboard'
import StatCard from '../components/StatCard.vue'
import { Package, CheckCircle2, AlertTriangle, Truck, Camera, CameraOff, Activity, ArrowRight, Eye, Box, ShoppingCart, Check } from 'lucide-vue-next'

const store = useDashboardStore()

function formatTime(dateStr) {
  const d = new Date(dateStr)
  return d.toLocaleDateString('de-CH') + ' ' + d.toLocaleTimeString('de-CH', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

function camTime(ts) {
  if (!ts) return ''
  const d = new Date(ts * 1000)
  return d.toLocaleTimeString('de-CH', { hour: '2-digit', minute: '2-digit', second: '2-digit' }) + ' Uhr'
}

function timeAgo(ts) {
  if (!ts) return ''
  const diff = Math.floor((Date.now() / 1000) - ts)
  if (diff < 60) return `vor ${diff}s`
  if (diff < 3600) return `vor ${Math.floor(diff / 60)}min`
  return `vor ${Math.floor(diff / 3600)}h`
}
</script>

<template>
  <!-- Stats -->
  <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
    <StatCard label="Produkte" :value="store.stats.total" sub="Im System erfasst"
      bgColor="bg-navy-50" valueColor="text-navy-900">
      <template #icon><Package class="w-4.5 h-4.5 text-navy-600" /></template>
    </StatCard>
    <StatCard label="Bestand OK" :value="store.stats.ok" sub="Über Mindestbestand"
      bgColor="bg-emerald-50" valueColor="text-emerald-600">
      <template #icon><CheckCircle2 class="w-4.5 h-4.5 text-emerald-600" /></template>
    </StatCard>
    <StatCard label="Kritisch" :value="store.stats.low" sub="Unter Mindestbestand"
      bgColor="bg-red-50" valueColor="text-red-600">
      <template #icon><AlertTriangle class="w-4.5 h-4.5 text-red-500" /></template>
    </StatCard>
    <StatCard label="Bestellungen" :value="store.stats.pendingOrders" sub="Offen / ausstehend"
      bgColor="bg-accent-50" valueColor="text-accent-600">
      <template #icon><Truck class="w-4.5 h-4.5 text-accent-600" /></template>
    </StatCard>
  </div>

  <!-- Two-column: Camera + Quick Actions -->
  <div class="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-6">
    <!-- Live-Kamerabild (2/3) -->
    <div class="lg:col-span-2 card">
      <div class="px-5 py-4 flex items-center justify-between">
        <div class="section-header">
          <div class="icon-wrap bg-emerald-50">
            <Camera class="w-4 h-4 text-emerald-600" />
          </div>
          <div>
            <h2 class="font-semibold text-navy-900 m-0 text-[14px]">Live-Kamerabild</h2>
            <p class="text-[11px] text-navy-400">Raspberry Pi Kamera-Feed</p>
          </div>
        </div>
        <div class="flex items-center gap-3">
          <div v-if="store.camera.detections" class="flex items-center gap-1.5 text-[12px] text-navy-500">
            <Box class="w-3.5 h-3.5" />
            <span>{{ store.camera.detections }} Objekte</span>
          </div>
          <span class="text-[11px] text-navy-400" v-if="store.camera.timestamp">{{ timeAgo(store.camera.timestamp) }}</span>
        </div>
      </div>
      <div class="glass-divider"></div>
      <div class="p-4">
        <div class="relative rounded-lg overflow-hidden bg-navy-50 flex items-center justify-center" style="min-height: 300px;">
          <template v-if="store.camera.image">
            <img :src="'data:image/jpeg;base64,' + store.camera.image" class="w-full rounded-lg" alt="Live-Kamerabild" />
            <div class="absolute top-2.5 left-2.5 flex items-center gap-1.5 bg-black/60 text-white text-[10px] font-semibold px-2.5 py-1 rounded-md">
              <span class="w-1.5 h-1.5 bg-red-500 rounded-full pulse-dot"></span>
              LIVE
            </div>
          </template>
          <template v-else>
            <div class="text-center py-14">
              <CameraOff class="w-10 h-10 text-navy-300 mx-auto mb-3" />
              <p class="text-navy-500 text-sm font-medium">Warte auf Kamerabild...</p>
              <p class="text-navy-400 text-xs mt-1">Bild erscheint nach dem nächsten Scan-Zyklus</p>
            </div>
          </template>
        </div>
      </div>
    </div>

    <!-- Quick Info (1/3) -->
    <div class="space-y-4">
      <div class="card p-5">
        <div class="flex items-center gap-2 mb-3">
          <Eye class="w-4 h-4 text-navy-500" />
          <h3 class="text-[13px] font-semibold text-navy-800 m-0">System-Status</h3>
        </div>
        <div class="space-y-3">
          <div class="flex items-center justify-between">
            <span class="text-[12px] text-navy-500">YOLO Modell</span>
            <span class="badge badge-ok">Aktiv</span>
          </div>
          <div class="flex items-center justify-between">
            <span class="text-[12px] text-navy-500">QR-Scanner</span>
            <span class="badge badge-ok">Aktiv</span>
          </div>
          <div class="flex items-center justify-between">
            <span class="text-[12px] text-navy-500">Kamera</span>
            <span class="badge" :class="store.camera.image ? 'badge-ok' : 'badge-pending'">
              {{ store.camera.image ? 'Verbunden' : 'Warte...' }}
            </span>
          </div>
          <div class="flex items-center justify-between">
            <span class="text-[12px] text-navy-500">Scan-Intervall</span>
            <span class="text-[12px] font-medium text-navy-700">30s</span>
          </div>
        </div>
      </div>

      <div class="card p-5">
        <div class="flex items-center gap-2 mb-3">
          <AlertTriangle class="w-4 h-4 text-red-500" />
          <h3 class="text-[13px] font-semibold text-navy-800 m-0">Kritische Produkte</h3>
        </div>
        <div v-if="store.products.length" class="space-y-2">
          <template v-for="p in store.products" :key="p.prod_id">
            <div v-if="store.latestScanMap[p.prod_id] && store.latestScanMap[p.prod_id].count <= p.min_qty"
              class="flex items-center justify-between py-1.5 px-2.5 bg-red-50 rounded-md">
              <span class="text-[12px] font-medium text-navy-800">{{ p.prod_name }}</span>
              <span class="text-[12px] font-semibold text-red-600">
                {{ store.latestScanMap[p.prod_id].count }} / {{ p.min_qty }}
              </span>
            </div>
          </template>
          <p v-if="store.stats.low === 0" class="text-[12px] text-emerald-600 text-center py-2">
            Alle Bestände in Ordnung
          </p>
        </div>
        <p v-else class="text-[12px] text-navy-400 text-center py-2">Keine Daten</p>
      </div>
    </div>
  </div>

  <!-- Letzte Scans -->
  <div class="card">
    <div class="px-5 py-4 flex items-center justify-between">
      <div class="section-header">
        <div class="icon-wrap bg-violet-50">
          <Activity class="w-4 h-4 text-violet-600" />
        </div>
        <div>
          <h2 class="font-semibold text-navy-900 m-0 text-[14px]">Letzte Scans</h2>
          <p class="text-[11px] text-navy-400">Echtzeit-Scan-Protokoll</p>
        </div>
      </div>
      <router-link to="/scans" class="text-[12px] text-accent-600 hover:text-accent-700 font-medium flex items-center gap-1">
        Alle anzeigen
        <ArrowRight class="w-3.5 h-3.5" />
      </router-link>
    </div>
    <div class="glass-divider"></div>
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
          <tr v-for="s in store.scans.slice(0, 8)" :key="s.id"
            class="data-row border-b border-navy-100">
            <td class="py-3 px-5 text-navy-600 text-[13px]">{{ formatTime(s.scanned_at) }}</td>
            <td class="py-3 px-4">
              <span class="font-mono text-[11px] bg-navy-50 text-navy-600 px-1.5 py-0.5 rounded font-medium">{{ s.shelf_id }}</span>
            </td>
            <td class="py-3 px-4">
              <span class="text-navy-900 font-medium text-[13px]">{{ store.productMap[s.prod_id]?.prod_name || s.prod_id }}</span>
              <span class="text-navy-400 text-[11px] ml-1 font-mono">{{ s.prod_id }}</span>
            </td>
            <td class="py-3 px-4 text-right font-mono font-semibold text-[14px]" :class="store.productMap[s.prod_id] && s.count <= store.productMap[s.prod_id].min_qty ? 'text-red-600' : 'text-emerald-600'">
              {{ s.count }}
            </td>
            <td class="py-3 px-4 text-right text-navy-400 text-[13px]">{{ store.productMap[s.prod_id]?.min_qty ?? '-' }}</td>
            <td class="py-3 px-5">
              <span class="badge" :class="store.productMap[s.prod_id] && s.count <= store.productMap[s.prod_id].min_qty ? 'badge-low' : 'badge-ok'">
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
            <td colspan="7" class="text-navy-400 py-10 text-center text-sm">Keine Scan-Daten vorhanden</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
