<script setup>
import { ref } from 'vue'
import { useDashboardStore } from '../stores/dashboard'
import { ClipboardList, Clock, CheckCircle2, PackageCheck, Send, ArrowDownToLine } from 'lucide-vue-next'

const store = useDashboardStore()
const receivedQty = ref({})
const completing = ref({})

function formatTime(dateStr) {
  const d = new Date(dateStr)
  return d.toLocaleDateString('de-CH') + ' ' + d.toLocaleTimeString('de-CH', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

async function complete(prodId) {
  const qty = parseInt(receivedQty.value[prodId])
  if (isNaN(qty) || qty < 0) {
    store.showToast('Bitte gültige Menge eingeben', 'error')
    return
  }
  completing.value[prodId] = true
  await store.completeOrder(prodId, qty)
  completing.value[prodId] = false
}
</script>

<template>
  <div class="flex items-center justify-between mb-5">
    <div class="section-header">
      <div class="icon-wrap bg-accent-50">
        <ClipboardList class="w-4.5 h-4.5 text-accent-600" />
      </div>
      <div>
        <h2 class="text-lg font-semibold text-navy-900 m-0">Bestellungen</h2>
        <p class="text-[11px] text-navy-400">{{ store.orders.length }} gesamt &middot; {{ store.pendingOrders.length }} offen</p>
      </div>
    </div>
    <div class="flex items-center gap-2">
      <span v-if="store.pendingOrders.length" class="badge badge-pending">{{ store.pendingOrders.length }} Offen</span>
      <span class="badge badge-ok">{{ store.deliveredOrders.length }} Geliefert</span>
    </div>
  </div>

  <div class="card">
    <div class="p-5 space-y-0">
      <div
        v-for="(o, idx) in store.orders"
        :key="o.id || o.prod_id + o.ordered_at"
        class="flex items-center justify-between py-4"
        :class="{ 'border-b border-navy-100': idx < store.orders.length - 1 }"
      >
        <div class="flex items-center gap-3">
          <div class="w-10 h-10 rounded-lg flex items-center justify-center"
            :class="o.status === 'PENDING' ? 'bg-accent-50' : 'bg-emerald-50'">
            <Clock v-if="o.status === 'PENDING'" class="w-4.5 h-4.5 text-accent-600" />
            <PackageCheck v-else class="w-4.5 h-4.5 text-emerald-600" />
          </div>
          <div>
            <p class="font-medium text-navy-900 text-[14px]">{{ store.productMap[o.prod_id]?.prod_name || o.prod_id }}</p>
            <div class="flex items-center gap-2 mt-0.5">
              <span class="font-mono text-[11px] bg-navy-50 text-navy-600 px-1.5 py-0.5 rounded font-medium">{{ o.prod_id }}</span>
              <span class="text-[11px] text-navy-400">&middot; {{ formatTime(o.ordered_at) }}</span>
            </div>
          </div>
        </div>
        <div class="flex items-center gap-4">
          <div class="text-right">
            <p class="font-semibold text-navy-900 text-base">{{ o.quantity }} <span class="text-[12px] text-navy-500">{{ store.productMap[o.prod_id]?.unit || 'Stk' }}</span></p>
            <p class="text-[11px] text-navy-400 flex items-center justify-end gap-1">
              <Send class="w-3 h-3" />
              {{ store.productMap[o.prod_id]?.supplier_email || '-' }}
            </p>
          </div>
          <template v-if="o.status === 'PENDING'">
            <div class="flex items-center gap-2 ml-1">
              <input
                type="number"
                :value="receivedQty[o.prod_id] ?? o.quantity"
                @input="receivedQty[o.prod_id] = $event.target.value"
                min="0"
                class="email-input text-center font-medium"
                style="width: 72px;"
                placeholder="Menge"
              />
              <button
                @click="complete(o.prod_id)"
                :disabled="completing[o.prod_id]"
                class="btn-accent px-3 py-1.5 rounded-md text-[12px] font-medium whitespace-nowrap flex items-center gap-1.5"
              >
                <ArrowDownToLine class="w-3.5 h-3.5" />
                {{ completing[o.prod_id] ? '...' : 'Abschliessen' }}
              </button>
            </div>
          </template>
          <template v-else>
            <span class="badge badge-done">
              <CheckCircle2 class="w-3 h-3" /> Geliefert
            </span>
          </template>
        </div>
      </div>
      <div v-if="!store.orders.length" class="text-center py-10">
        <ClipboardList class="w-8 h-8 text-navy-300 mx-auto mb-3" />
        <p class="text-navy-500 text-sm font-medium">Keine Bestellungen vorhanden</p>
        <p class="text-navy-400 text-xs mt-1">Bestellungen werden automatisch bei niedrigem Bestand ausgelöst</p>
      </div>
    </div>
  </div>
</template>
