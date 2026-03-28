import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { io } from 'socket.io-client'

const API = ''

export const useDashboardStore = defineStore('dashboard', () => {
  const products = ref([])
  const orders = ref([])
  const scans = ref([])
  const camera = ref({ image: null, detections: 0, timestamp: null })
  const cameraHistory = ref([])
  const storageEnabled = ref(true)
  const loading = ref(false)
  const lastUpdate = ref(null)
  const toasts = ref([])
  const connected = ref(false)
  let socket = null

  const pendingOrders = computed(() => orders.value.filter(o => o.status === 'PENDING'))
  const deliveredOrders = computed(() => orders.value.filter(o => o.status === 'DELIVERED'))

  const productMap = computed(() => {
    const map = {}
    products.value.forEach(p => { map[p.prod_id] = p })
    return map
  })

  const latestScanMap = computed(() => {
    const map = {}
    scans.value.forEach(s => {
      if (!map[s.prod_id] || new Date(s.scanned_at) > new Date(map[s.prod_id].scanned_at)) {
        map[s.prod_id] = s
      }
    })
    return map
  })

  const stats = computed(() => {
    let ok = 0, low = 0
    products.value.forEach(p => {
      const stock = p.sap_stock ?? 0
      if (stock <= p.min_qty) low++
      else ok++
    })
    return {
      total: products.value.length,
      ok,
      low,
      pendingOrders: pendingOrders.value.length,
    }
  })

  function showToast(message, type = 'success') {
    const id = Date.now()
    toasts.value.push({ id, message, type })
    setTimeout(() => {
      toasts.value = toasts.value.filter(t => t.id !== id)
    }, 3000)
  }

  function initSocket() {
    if (socket) return

    socket = io(API || window.location.origin, {
      transports: ['websocket', 'polling'],
      reconnection: true,
      reconnectionDelay: 1000,
    })

    socket.on('connect', () => {
      connected.value = true
      console.log('[WS] Verbunden')
    })

    socket.on('disconnect', () => {
      connected.value = false
      console.log('[WS] Getrennt')
    })

    socket.on('dashboard_update', (data) => {
      products.value = data.products
      orders.value = data.orders
      scans.value = data.scans
      lastUpdate.value = new Date()
      console.log('[WS] Dashboard-Update empfangen')
    })

    socket.on('camera_update', (data) => {
      camera.value = data
      console.log('[WS] Kamerabild empfangen')
    })

    socket.on('scan_update', (data) => {
      showToast(`Neuer Scan: ${data.prod_id} → ${data.count} Stk (${data.shelf_id})`)
    })
  }

  function destroySocket() {
    if (socket) {
      socket.disconnect()
      socket = null
      connected.value = false
    }
  }

  async function fetchDashboard() {
    loading.value = true
    try {
      const resp = await fetch(API + '/api/dashboard')
      const data = await resp.json()
      products.value = data.products
      orders.value = data.orders
      scans.value = data.scans
      lastUpdate.value = new Date()
    } catch (err) {
      console.error('Dashboard-Fehler:', err)
    } finally {
      loading.value = false
    }
  }

  async function fetchCamera() {
    try {
      const resp = await fetch(API + '/api/camera')
      if (resp.ok) {
        const data = await resp.json()
        camera.value = data
      }
    } catch (err) { /* kein Bild */ }
  }

  async function fetchHistory() {
    try {
      const resp = await fetch(API + '/api/camera/history')
      if (resp.ok) {
        const data = await resp.json()
        cameraHistory.value = data.images || []
      }
    } catch (err) { /* keine History */ }
  }

  async function fetchStorageStatus() {
    try {
      const resp = await fetch(API + '/api/camera/storage')
      if (resp.ok) {
        const data = await resp.json()
        storageEnabled.value = data.enabled
      }
    } catch (err) { /* ignore */ }
  }

  async function toggleStorage() {
    try {
      const resp = await fetch(API + '/api/camera/storage', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ enabled: !storageEnabled.value }),
      })
      if (resp.ok) {
        const data = await resp.json()
        storageEnabled.value = data.enabled
        showToast(data.enabled ? 'Bildspeicherung aktiviert' : 'Bildspeicherung deaktiviert')
      }
    } catch (err) {
      showToast('Verbindungsfehler', 'error')
    }
  }

  async function saveProduct(prodId, updates) {
    try {
      const resp = await fetch(`${API}/api/product/${prodId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updates),
      })
      const data = await resp.json()
      if (data.status === 'OK') {
        showToast(`Produkt ${prodId} aktualisiert`)
      } else {
        showToast('Fehler: ' + (data.error || 'Unbekannt'), 'error')
      }
    } catch (err) {
      showToast('Verbindungsfehler', 'error')
    }
  }

  async function saveEmail(prodId, email) {
    return saveProduct(prodId, { supplier_email: email })
  }

  async function syncSAP() {
    try {
      const resp = await fetch(`${API}/api/products/sync`, { method: 'POST' })
      const data = await resp.json()
      if (data.status === 'OK') {
        showToast(`SAP Sync: ${data.count} Produkte importiert`)
        await fetchDashboard()
      } else {
        showToast('SAP Sync Fehler: ' + (data.error || 'Unbekannt'), 'error')
      }
    } catch (err) {
      showToast('Verbindungsfehler', 'error')
    }
  }

  async function completeOrder(prodId, qty) {
    try {
      const resp = await fetch(`${API}/api/order/complete`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prod_id: prodId, received_qty: qty }),
      })
      const data = await resp.json()
      if (data.status === 'OK') {
        showToast(`Bestellung für ${prodId} abgeschlossen (${qty} Stk erhalten)`)
        await fetchDashboard()
      } else {
        showToast('Fehler: ' + (data.error || 'Unbekannt'), 'error')
      }
    } catch (err) {
      showToast('Verbindungsfehler', 'error')
    }
  }

  return {
    products, orders, scans, camera, cameraHistory, storageEnabled, loading, lastUpdate, toasts, connected,
    pendingOrders, deliveredOrders, productMap, latestScanMap, stats,
    initSocket, destroySocket, fetchDashboard, fetchCamera, fetchHistory, fetchStorageStatus, toggleStorage, saveProduct, saveEmail, syncSAP, completeOrder, showToast,
  }
})
