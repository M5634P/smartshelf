<script setup>
import { onMounted } from 'vue'
import { useDashboardStore } from '../stores/dashboard'
import { Camera, CameraOff, RefreshCw, Box, Wifi, Clock, Download, Image as ImageIcon, Trash2, HardDrive } from 'lucide-vue-next'

const store = useDashboardStore()

onMounted(() => {
  store.fetchHistory()
  store.fetchStorageStatus()
})

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

function formatTimestamp(ts) {
  if (!ts || ts.length < 15) return ts
  return `${ts.slice(6,8)}.${ts.slice(4,6)}.${ts.slice(0,4)} ${ts.slice(9,11)}:${ts.slice(11,13)}:${ts.slice(13,15)}`
}

function formatSize(bytes) {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(0) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

function downloadLatest() {
  const a = document.createElement('a')
  a.href = '/api/camera/latest.jpg'
  a.download = 'smartshelf_latest.jpg'
  a.click()
}

function downloadImage(filename) {
  const a = document.createElement('a')
  a.href = `/api/camera/history/${filename}`
  a.download = filename
  a.click()
}

function refreshAll() {
  store.fetchCamera()
  store.fetchHistory()
}
</script>

<template>
  <div class="flex items-center justify-between mb-5">
    <div class="section-header">
      <div class="icon-wrap bg-emerald-50">
        <Camera class="w-4.5 h-4.5 text-emerald-600" />
      </div>
      <div>
        <h2 class="text-lg font-semibold text-navy-900 m-0">Live-Kamerabild</h2>
        <p class="text-[11px] text-navy-400">Raspberry Pi Kamera &middot; Automatisch alle 10 Sekunden</p>
      </div>
    </div>
    <div class="flex items-center gap-2">
      <button @click="store.toggleStorage()" class="px-3 py-1.5 rounded-md text-[12px] font-medium flex items-center gap-1.5 transition-colors" :class="store.storageEnabled ? 'bg-emerald-50 text-emerald-700 hover:bg-emerald-100' : 'bg-red-50 text-red-600 hover:bg-red-100'">
        <HardDrive class="w-3 h-3" />
        {{ store.storageEnabled ? 'Speicherung AN' : 'Speicherung AUS' }}
      </button>
      <button v-if="store.camera.image" @click="downloadLatest" class="btn-ghost px-3 py-1.5 rounded-md text-[12px] font-medium flex items-center gap-1.5">
        <Download class="w-3 h-3" />
        Download
      </button>
      <button @click="refreshAll" class="btn-accent px-3 py-1.5 rounded-md text-[12px] font-medium flex items-center gap-1.5">
        <RefreshCw class="w-3 h-3" />
        Aktualisieren
      </button>
    </div>
  </div>

  <!-- Info-Karten -->
  <div class="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-5">
    <div class="card p-4 flex items-center gap-3">
      <div class="w-9 h-9 rounded-lg bg-emerald-50 flex items-center justify-center">
        <Wifi class="w-4 h-4 text-emerald-600" />
      </div>
      <div>
        <p class="text-[11px] text-navy-400 font-semibold uppercase tracking-wide">Status</p>
        <p class="text-[13px] font-semibold" :class="store.camera.image ? 'text-emerald-600' : 'text-navy-400'">
          {{ store.camera.image ? 'Verbunden' : 'Offline' }}
        </p>
      </div>
    </div>
    <div class="card p-4 flex items-center gap-3">
      <div class="w-9 h-9 rounded-lg bg-navy-50 flex items-center justify-center">
        <Box class="w-4 h-4 text-navy-600" />
      </div>
      <div>
        <p class="text-[11px] text-navy-400 font-semibold uppercase tracking-wide">Erkannt</p>
        <p class="text-[13px] font-semibold text-navy-900">{{ store.camera.detections ?? 0 }} Objekte</p>
      </div>
    </div>
    <div class="card p-4 flex items-center gap-3">
      <div class="w-9 h-9 rounded-lg bg-violet-50 flex items-center justify-center">
        <Clock class="w-4 h-4 text-violet-600" />
      </div>
      <div>
        <p class="text-[11px] text-navy-400 font-semibold uppercase tracking-wide">Letzte Aufnahme</p>
        <p class="text-[13px] font-semibold text-navy-900">{{ store.camera.timestamp ? timeAgo(store.camera.timestamp) : '-' }}</p>
      </div>
    </div>
  </div>

  <!-- Kamerabild -->
  <div class="card mb-6">
    <div class="px-5 py-4 flex items-center justify-between">
      <div class="flex items-center gap-2">
        <span v-if="store.camera.image" class="flex items-center gap-1.5 text-red-600 text-[11px] font-semibold">
          <span class="w-1.5 h-1.5 bg-red-500 rounded-full pulse-dot"></span>
          Live Feed
        </span>
        <span v-else class="text-[13px] text-navy-400">Warte auf Signal...</span>
      </div>
      <span class="text-[11px] text-navy-400" v-if="store.camera.timestamp">{{ camTime(store.camera.timestamp) }}</span>
    </div>
    <div class="glass-divider"></div>
    <div class="p-4">
      <div class="relative rounded-lg overflow-hidden bg-navy-50 flex items-center justify-center" style="min-height: 440px;">
        <template v-if="store.camera.image">
          <img :src="'data:image/jpeg;base64,' + store.camera.image" class="w-full rounded-lg" alt="Live-Kamerabild" />
          <div class="absolute top-2.5 left-2.5 flex items-center gap-1.5 bg-black/60 text-white text-[10px] font-semibold px-2.5 py-1 rounded-md">
            <span class="w-1.5 h-1.5 bg-red-500 rounded-full pulse-dot"></span>
            LIVE
          </div>
          <div class="absolute bottom-2.5 right-2.5 flex items-center gap-1.5 bg-black/60 text-white text-[10px] font-semibold px-2.5 py-1 rounded-md">
            <Box class="w-3 h-3" />
            {{ store.camera.detections }} Objekte
          </div>
        </template>
        <template v-else>
          <div class="text-center py-16">
            <CameraOff class="w-10 h-10 text-navy-300 mx-auto mb-3" />
            <p class="text-navy-500 text-sm font-medium">Kein Kamerabild verfügbar</p>
            <p class="text-navy-400 text-xs mt-1.5 max-w-sm mx-auto">Das Bild erscheint automatisch, sobald der Raspberry Pi den nächsten Scan-Zyklus abschliesst</p>
          </div>
        </template>
      </div>
    </div>
  </div>

  <!-- Bildverlauf -->
  <div class="card">
    <div class="px-5 py-4 flex items-center justify-between">
      <div class="section-header">
        <div class="icon-wrap bg-violet-50">
          <ImageIcon class="w-4 h-4 text-violet-600" />
        </div>
        <div>
          <h2 class="font-semibold text-navy-900 m-0 text-[14px]">Bildverlauf</h2>
          <p class="text-[11px] text-navy-400">{{ store.cameraHistory.length }} gespeicherte Aufnahmen</p>
        </div>
      </div>
      <button @click="store.fetchHistory()" class="btn-ghost px-3 py-1.5 rounded-md text-[12px] font-medium flex items-center gap-1.5">
        <RefreshCw class="w-3 h-3" />
      </button>
    </div>
    <div class="glass-divider"></div>
    <div class="p-4">
      <div v-if="store.cameraHistory.length === 0" class="text-center py-10">
        <ImageIcon class="w-8 h-8 text-navy-300 mx-auto mb-2" />
        <p class="text-navy-500 text-sm">Noch keine Bilder gespeichert</p>
      </div>
      <div v-else class="overflow-x-auto">
        <table class="w-full text-[12px]">
          <thead>
            <tr class="text-navy-400 uppercase tracking-wide text-[10px]">
              <th class="text-left pb-3 font-semibold">Zeitpunkt</th>
              <th class="text-left pb-3 font-semibold">Dateiname</th>
              <th class="text-right pb-3 font-semibold">Grösse</th>
              <th class="text-right pb-3 font-semibold">Aktion</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="img in store.cameraHistory" :key="img.filename" class="border-t border-navy-50 hover:bg-navy-50/50 transition-colors">
              <td class="py-2.5 text-navy-700 font-medium">{{ formatTimestamp(img.timestamp) }}</td>
              <td class="py-2.5 text-navy-500 font-mono text-[11px]">{{ img.filename }}</td>
              <td class="py-2.5 text-navy-500 text-right">{{ formatSize(img.size) }}</td>
              <td class="py-2.5 text-right">
                <a :href="'/api/camera/history/' + img.filename" :download="img.filename" class="inline-flex items-center gap-1 text-emerald-600 hover:text-emerald-700 font-medium cursor-pointer">
                  <Download class="w-3 h-3" />
                  Download
                </a>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>
