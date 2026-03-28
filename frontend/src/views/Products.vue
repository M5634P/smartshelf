<script setup>
import { ref, computed } from 'vue'
import { useDashboardStore } from '../stores/dashboard'
import { Package, ShoppingCart, RefreshCw, Check, X, Power } from 'lucide-vue-next'

const store = useDashboardStore()
const syncing = ref(false)

const editing = ref({})

const sortedProducts = computed(() =>
  [...store.products].sort((a, b) => (b.active !== false) - (a.active !== false))
)

function isLow(product) {
  const stock = product.sap_stock ?? 0
  return stock <= product.min_qty
}

function startEdit(prodId, product) {
  editing.value[prodId] = {
    prod_name: product.prod_name || '',
    sap_stock: product.sap_stock ?? 0,
    sap_ordered_from_vendors: product.sap_ordered_from_vendors ?? 0,
    sap_ordered_by_customers: product.sap_ordered_by_customers ?? 0,
    min_qty: product.min_qty ?? 0,
    reorder_qty: product.reorder_qty ?? 0,
    supplier_name: product.supplier_name || '',
    supplier_email: product.supplier_email || '',
  }
}

function cancelEdit(prodId) {
  delete editing.value[prodId]
}

async function saveEdit(prodId) {
  const e = editing.value[prodId]
  if (!e) return
  await store.saveProduct(prodId, {
    prod_name: e.prod_name,
    sap_stock: parseInt(e.sap_stock) || 0,
    sap_ordered_from_vendors: parseInt(e.sap_ordered_from_vendors) || 0,
    sap_ordered_by_customers: parseInt(e.sap_ordered_by_customers) || 0,
    min_qty: parseInt(e.min_qty) || 0,
    reorder_qty: parseInt(e.reorder_qty) || 0,
    supplier_name: e.supplier_name,
    supplier_email: e.supplier_email,
  })
  delete editing.value[prodId]
  await store.fetchDashboard()
}

async function toggleActive(prodId, currentState) {
  await store.saveProduct(prodId, { active: !currentState })
  await store.fetchDashboard()
}

function onKey(event, prodId) {
  if (event.key === 'Enter') saveEdit(prodId)
  if (event.key === 'Escape') cancelEdit(prodId)
}

async function doSync() {
  syncing.value = true
  await store.syncSAP()
  syncing.value = false
}
</script>

<template>
  <div class="flex items-center justify-between mb-5">
    <div class="section-header">
      <div class="icon-wrap bg-navy-50">
        <Package class="w-4.5 h-4.5 text-navy-600" />
      </div>
      <div>
        <h2 class="text-lg font-semibold text-navy-900 m-0">Produkt-Bestand</h2>
        <p class="text-[11px] text-navy-400">{{ store.products.length }} Produkte &middot; Klick zum Bearbeiten &middot; Enter = Speichern, Esc = Abbruch</p>
      </div>
    </div>
    <div class="flex items-center gap-2">
      <button @click="doSync" :disabled="syncing"
        class="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg bg-navy-100 text-navy-700 hover:bg-navy-200 transition-colors disabled:opacity-50">
        <RefreshCw class="w-3.5 h-3.5" :class="{ 'animate-spin': syncing }" />
        SAP Sync
      </button>
      <span class="badge badge-ok">{{ store.stats.ok }} OK</span>
      <span v-if="store.stats.low > 0" class="badge badge-low">{{ store.stats.low }} Kritisch</span>
    </div>
  </div>

  <div class="card">
    <div class="overflow-x-auto">
      <table class="w-full text-sm">
        <thead>
          <tr>
            <th class="text-center py-3 px-3 w-16">Aktiv</th>
            <th class="text-center py-3 px-3 w-20">Aktion</th>
            <th class="text-left py-3 px-3">Status</th>
            <th class="text-left py-3 px-3">ItemCode</th>
            <th class="text-left py-3 px-3">Produkt</th>
            <th class="text-right py-3 px-3">Lager</th>
            <th class="text-right py-3 px-3">Best. (Eink.)</th>
            <th class="text-right py-3 px-3">Best. (Kd.)</th>
            <th class="text-right py-3 px-3">Min</th>
            <th class="text-right py-3 px-3">Max/Soll</th>
            <th class="text-left py-3 px-3">Lieferant</th>
            <th class="text-left py-3 px-3">E-Mail</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="p in sortedProducts" :key="p.prod_id"
            class="data-row border-b border-navy-100"
            :class="{ 'bg-blue-50/50': editing[p.prod_id], 'opacity-40': p.active === false }">

            <!-- Aktiv Toggle -->
            <td class="py-2 px-3 text-center">
              <button @click="toggleActive(p.prod_id, p.active !== false)"
                :title="p.active !== false ? 'Deaktivieren' : 'Aktivieren'"
                class="p-1 rounded transition-colors"
                :class="p.active !== false ? 'bg-emerald-100 text-emerald-600 hover:bg-emerald-200' : 'bg-navy-100 text-navy-400 hover:bg-navy-200'">
                <Power class="w-3.5 h-3.5" />
              </button>
            </td>

            <!-- Aktion -->
            <td class="py-2 px-3 text-center">
              <div v-if="editing[p.prod_id]" class="flex items-center gap-1 justify-center">
                <button @click="saveEdit(p.prod_id)" title="Speichern (Enter)"
                  class="p-1 rounded bg-emerald-100 text-emerald-700 hover:bg-emerald-200">
                  <Check class="w-3.5 h-3.5" />
                </button>
                <button @click="cancelEdit(p.prod_id)" title="Abbruch (Esc)"
                  class="p-1 rounded bg-red-100 text-red-600 hover:bg-red-200">
                  <X class="w-3.5 h-3.5" />
                </button>
              </div>
              <span v-else-if="store.orders.some(o => o.prod_id === p.prod_id && o.status === 'PENDING')" class="badge badge-pending">
                <ShoppingCart class="w-3 h-3" />
              </span>
              <span v-else class="text-navy-300 text-[13px]">&ndash;</span>
            </td>

            <td class="py-2 px-3">
              <span class="badge" :class="isLow(p) ? 'badge-low' : 'badge-ok'">
                {{ isLow(p) ? 'Kritisch' : 'OK' }}
              </span>
            </td>
            <td class="py-2 px-3">
              <span class="font-mono text-[11px] bg-navy-50 text-navy-600 px-1.5 py-0.5 rounded font-medium">{{ p.prod_id }}</span>
            </td>

            <td class="py-2 px-3">
              <input v-if="editing[p.prod_id]" v-model="editing[p.prod_id].prod_name" @keydown="onKey($event, p.prod_id)"
                class="w-32 px-1.5 py-0.5 text-xs border border-navy-300 rounded" />
              <span v-else class="font-medium text-navy-900 text-[13px] cursor-pointer hover:text-blue-600" @click="startEdit(p.prod_id, p)">{{ p.prod_name }}</span>
            </td>

            <td class="py-2 px-3 text-right">
              <input v-if="editing[p.prod_id]" v-model="editing[p.prod_id].sap_stock" type="number" @keydown="onKey($event, p.prod_id)"
                class="w-16 px-1.5 py-0.5 text-right text-xs border border-navy-300 rounded" />
              <span v-else class="font-mono font-bold text-lg cursor-pointer" :class="isLow(p) ? 'text-red-600' : 'text-emerald-600'" @click="startEdit(p.prod_id, p)">
                {{ p.sap_stock ?? 0 }}
              </span>
            </td>

            <td class="py-2 px-3 text-right">
              <input v-if="editing[p.prod_id]" v-model="editing[p.prod_id].sap_ordered_from_vendors" type="number" @keydown="onKey($event, p.prod_id)"
                class="w-16 px-1.5 py-0.5 text-right text-xs border border-navy-300 rounded" />
              <span v-else class="text-navy-500 text-[13px] cursor-pointer hover:text-blue-600" @click="startEdit(p.prod_id, p)">{{ p.sap_ordered_from_vendors ?? 0 }}</span>
            </td>

            <td class="py-2 px-3 text-right">
              <input v-if="editing[p.prod_id]" v-model="editing[p.prod_id].sap_ordered_by_customers" type="number" @keydown="onKey($event, p.prod_id)"
                class="w-16 px-1.5 py-0.5 text-right text-xs border border-navy-300 rounded" />
              <span v-else class="text-navy-500 text-[13px] cursor-pointer hover:text-blue-600" @click="startEdit(p.prod_id, p)">{{ p.sap_ordered_by_customers ?? 0 }}</span>
            </td>

            <td class="py-2 px-3 text-right">
              <input v-if="editing[p.prod_id]" v-model="editing[p.prod_id].min_qty" type="number" @keydown="onKey($event, p.prod_id)"
                class="w-16 px-1.5 py-0.5 text-right text-xs border border-navy-300 rounded" />
              <span v-else class="text-navy-500 text-[13px] cursor-pointer hover:text-blue-600" @click="startEdit(p.prod_id, p)">{{ p.min_qty }} {{ p.unit }}</span>
            </td>

            <td class="py-2 px-3 text-right">
              <input v-if="editing[p.prod_id]" v-model="editing[p.prod_id].reorder_qty" type="number" @keydown="onKey($event, p.prod_id)"
                class="w-16 px-1.5 py-0.5 text-right text-xs border border-navy-300 rounded" />
              <span v-else class="text-navy-500 text-[13px] cursor-pointer hover:text-blue-600" @click="startEdit(p.prod_id, p)">{{ p.reorder_qty }} {{ p.unit }}</span>
            </td>

            <td class="py-2 px-3">
              <input v-if="editing[p.prod_id]" v-model="editing[p.prod_id].supplier_name" @keydown="onKey($event, p.prod_id)"
                class="w-28 px-1.5 py-0.5 text-xs border border-navy-300 rounded" />
              <span v-else class="text-navy-700 text-[13px] cursor-pointer hover:text-blue-600" @click="startEdit(p.prod_id, p)">{{ p.supplier_name || '-' }}</span>
            </td>

            <td class="py-2 px-3">
              <input v-if="editing[p.prod_id]" v-model="editing[p.prod_id].supplier_email" type="email" @keydown="onKey($event, p.prod_id)"
                placeholder="email@example.com"
                class="w-40 px-1.5 py-0.5 text-xs border border-navy-300 rounded" />
              <span v-else class="text-navy-500 text-[13px] cursor-pointer hover:text-blue-600" @click="startEdit(p.prod_id, p)">{{ p.supplier_email || '-' }}</span>
            </td>
          </tr>
          <tr v-if="!store.products.length">
            <td colspan="12" class="text-navy-400 py-10 text-center">Keine Produkte geladen &ndash; SAP Sync starten</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
