import { useState, useEffect, useCallback, useMemo } from 'react'
import {
  getOrders,
  createOrder,
  updateOrderStatus,
  deleteOrder,
} from '../../services/orderService'
import { getCustomers } from '../../services/customerService'
import { getProducts }  from '../../services/productService'
import ConfirmDialog    from '../../components/ConfirmDialog/ConfirmDialog'
import { TableSkeleton } from '../../components/LoadingSkeleton/LoadingSkeleton'
import EmptyState       from '../../components/EmptyState/EmptyState'
import styles           from './Orders.module.css'

// ── Constants ─────────────────────────────────────────────────────────────────

const STATUS_META = {
  pending:   { label: 'Pending',   bg: 'var(--status-pending-bg)',   color: 'var(--status-pending-color)',   dot: 'var(--status-pending-dot)'   },
  confirmed: { label: 'Confirmed', bg: 'var(--status-confirmed-bg)', color: 'var(--status-confirmed-color)', dot: 'var(--status-confirmed-dot)' },
  completed: { label: 'Completed', bg: 'var(--status-completed-bg)', color: 'var(--status-completed-color)', dot: 'var(--status-completed-dot)' },
  cancelled: { label: 'Cancelled', bg: 'var(--status-cancelled-bg)', color: 'var(--status-cancelled-color)', dot: 'var(--status-cancelled-dot)' },
}

const STATUS_TABS = ['all', 'pending', 'confirmed', 'completed', 'cancelled']

const TRANSITIONS = {
  pending:   [
    { label: 'Confirm Order',  to: 'confirmed', variant: 'primary' },
    { label: 'Cancel Order',   to: 'cancelled', variant: 'danger'  },
  ],
  confirmed: [
    { label: 'Mark Completed', to: 'completed', variant: 'success' },
    { label: 'Cancel Order',   to: 'cancelled', variant: 'danger'  },
  ],
  completed: [],
  cancelled: [],
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function fmtCurrency(val) {
  return '$' + Number(val).toLocaleString('en-US', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })
}

function fmtDate(iso) {
  return new Date(iso).toLocaleDateString('en-US', {
    month: 'short', day: 'numeric', year: 'numeric',
  })
}

function initials(name) {
  return (name ?? '')
    .split(' ')
    .map((w) => w[0])
    .slice(0, 2)
    .join('')
    .toUpperCase()
}

// ── Main component ────────────────────────────────────────────────────────────

export default function Orders() {
  // Data
  const [orders,      setOrders]      = useState([])
  const [loading,     setLoading]     = useState(true)
  const [error,       setError]       = useState(null)
  const [customerMap, setCustomerMap] = useState({})
  const [productMap,  setProductMap]  = useState({})

  // UI
  const [statusFilter,     setStatusFilter]     = useState('all')
  const [selectedOrderId,  setSelectedOrderId]  = useState(null)
  const [updatingStatus,   setUpdatingStatus]   = useState(false)
  const [actionError,      setActionError]      = useState(null)
  const [deleteTarget,     setDeleteTarget]     = useState(null)
  const [deleting,         setDeleting]         = useState(false)

  // New order modal
  const [newOpen,   setNewOpen]   = useState(false)
  const [newForm,   setNewForm]   = useState({ customer_id: '', items: [] })
  const [newError,  setNewError]  = useState(null)
  const [newSaving, setNewSaving] = useState(false)

  // ── Load ────────────────────────────────────────────────────────────
  const loadOrders = useCallback(() => {
    setLoading(true)
    setError(null)
    getOrders({ limit: 200 })
      .then(setOrders)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  const reloadProductMap = useCallback(() => {
    getProducts({ limit: 500 })
      .then((prods) => setProductMap(Object.fromEntries(prods.map((p) => [p.id, p]))))
      .catch(() => {})
  }, [])

  useEffect(() => {
    loadOrders()
    Promise.all([
      getCustomers({ limit: 500 }),
      getProducts({ limit: 500 }),
    ]).then(([custs, prods]) => {
      setCustomerMap(Object.fromEntries(custs.map((c) => [c.id, c])))
      setProductMap(Object.fromEntries(prods.map((p) => [p.id, p])))
    }).catch(() => {})
  }, [loadOrders])

  // ESC closes new-order modal
  useEffect(() => {
    if (!newOpen) return
    const h = (e) => { if (e.key === 'Escape' && !newSaving) setNewOpen(false) }
    window.addEventListener('keydown', h)
    return () => window.removeEventListener('keydown', h)
  }, [newOpen, newSaving])

  // Clear action error when selected order changes
  useEffect(() => { setActionError(null) }, [selectedOrderId])

  // ── Derived ─────────────────────────────────────────────────────────
  const filtered = useMemo(() =>
    statusFilter === 'all'
      ? orders
      : orders.filter((o) => o.order_status === statusFilter),
    [orders, statusFilter],
  )

  const selectedOrder = useMemo(() =>
    selectedOrderId != null ? (orders.find((o) => o.id === selectedOrderId) ?? null) : null,
    [orders, selectedOrderId],
  )

  const activeProducts = useMemo(() =>
    Object.values(productMap).filter((p) => p.status === 'active'),
    [productMap],
  )

  const newOrderTotal = useMemo(() =>
    newForm.items.reduce((sum, item) => {
      const price = parseFloat(productMap[item.product_id]?.price ?? 0)
      const qty   = parseInt(item.quantity, 10) || 0
      return sum + price * qty
    }, 0),
    [newForm.items, productMap],
  )

  // ── Status update ────────────────────────────────────────────────────
  async function handleStatusUpdate(orderId, newStatus) {
    setActionError(null)
    setUpdatingStatus(true)
    try {
      await updateOrderStatus(orderId, newStatus)
      setOrders((prev) =>
        prev.map((o) => o.id === orderId ? { ...o, order_status: newStatus } : o),
      )
    } catch (e) {
      setActionError(e.message ?? 'Failed to update order status.')
    } finally {
      setUpdatingStatus(false)
    }
  }

  // ── Delete ───────────────────────────────────────────────────────────
  async function handleDelete() {
    setDeleting(true)
    try {
      await deleteOrder(deleteTarget.id)
      setOrders((prev) => prev.filter((o) => o.id !== deleteTarget.id))
      if (selectedOrderId === deleteTarget.id) setSelectedOrderId(null)
      setDeleteTarget(null)
    } catch (e) {
      setDeleteTarget(null)
      setActionError(e.message ?? 'Failed to delete order.')
    } finally {
      setDeleting(false)
    }
  }

  // ── New order helpers ────────────────────────────────────────────────
  function openNewOrder() {
    setNewForm({
      customer_id: '',
      items: [{ _key: Date.now(), product_id: '', quantity: 1 }],
    })
    setNewError(null)
    setNewOpen(true)
  }

  function addItem() {
    setNewForm((f) => ({
      ...f,
      items: [...f.items, { _key: Date.now(), product_id: '', quantity: 1 }],
    }))
  }

  function removeItem(key) {
    setNewForm((f) => ({ ...f, items: f.items.filter((i) => i._key !== key) }))
  }

  function updateItem(key, field, value) {
    setNewForm((f) => ({
      ...f,
      items: f.items.map((i) => i._key === key ? { ...i, [field]: value } : i),
    }))
  }

  async function handleCreateOrder() {
    setNewError(null)
    if (!newForm.customer_id)       return setNewError('Please select a customer.')
    if (newForm.items.length === 0) return setNewError('Add at least one product.')
    for (const item of newForm.items) {
      if (!item.product_id)                    return setNewError('Each item must have a product selected.')
      if (!item.quantity || parseInt(item.quantity) < 1)
                                               return setNewError('Each item must have a quantity of at least 1.')
    }
    const ids = newForm.items.map((i) => i.product_id)
    if (new Set(ids).size !== ids.length)      return setNewError('Duplicate products — combine into one item instead.')

    const payload = {
      customer_id: parseInt(newForm.customer_id, 10),
      items: newForm.items.map((i) => ({
        product_id: parseInt(i.product_id, 10),
        quantity:   parseInt(i.quantity,   10),
      })),
    }

    setNewSaving(true)
    try {
      const created = await createOrder(payload)
      setNewOpen(false)
      loadOrders()
      reloadProductMap()
      setSelectedOrderId(created.id)
    } catch (e) {
      const detail = e.response?.data?.detail
      setNewError(
        Array.isArray(detail)
          ? detail.map((d) => d.msg).join(', ')
          : (detail ?? e.message),
      )
    } finally {
      setNewSaving(false)
    }
  }

  // ── Render ────────────────────────────────────────────────────────────
  return (
    <div className={styles.page}>

      {/* ── LEFT PANEL ── */}
      <div className={styles.listPanel}>

        {/* Toolbar */}
        <div className={styles.toolbar}>
          <div className={styles.tabs}>
            {STATUS_TABS.map((tab) => (
              <button
                key={tab}
                className={`${styles.tab} ${statusFilter === tab ? styles.tabActive : ''}`}
                onClick={() => setStatusFilter(tab)}
              >
                {tab === 'all' ? 'All' : STATUS_META[tab].label}
                <span className={styles.tabCount}>
                  {tab === 'all'
                    ? orders.length
                    : orders.filter((o) => o.order_status === tab).length}
                </span>
              </button>
            ))}
          </div>
          <button className={styles.btnPrimary} onClick={openNewOrder}>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2.5} strokeLinecap="round" strokeLinejoin="round" width={15} height={15}>
              <line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>
            </svg>
            New Order
          </button>
        </div>

        {/* Error */}
        {error && (
          <div className={styles.errorBanner}>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} width={16} height={16}>
              <circle cx="12" cy="12" r="10"/>
              <line x1="12" y1="8" x2="12" y2="12"/>
              <line x1="12" y1="16" x2="12.01" y2="16"/>
            </svg>
            {error}
          </div>
        )}

        {/* List */}
        <div className={styles.listCard}>
          {loading ? (
            <div className={styles.skeletonPad}><TableSkeleton rows={8} /></div>
          ) : filtered.length === 0 ? (
            <EmptyState
              title={statusFilter !== 'all' ? `No ${statusFilter} orders` : 'No orders yet'}
              description={
                statusFilter !== 'all'
                  ? 'Try a different status filter.'
                  : 'Create your first order to get started.'
              }
              actionLabel={statusFilter === 'all' ? 'New Order' : undefined}
              onAction={statusFilter === 'all' ? openNewOrder : undefined}
            />
          ) : (
            <ul className={styles.orderList}>
              {filtered.map((order) => {
                const customer   = customerMap[order.customer_id]
                const meta       = STATUS_META[order.order_status] ?? STATUS_META.pending
                const isSelected = order.id === selectedOrderId
                return (
                  <li
                    key={order.id}
                    className={`${styles.orderRow} ${isSelected ? styles.orderRowSelected : ''}`}
                    onClick={() => setSelectedOrderId(isSelected ? null : order.id)}
                  >
                    <div className={styles.orderRowLeft}>
                      <div className={styles.orderNum}>#{String(order.id).padStart(4, '0')}</div>
                      <div className={styles.customerName}>
                        {customer?.full_name ?? `Customer #${order.customer_id}`}
                      </div>
                      <div className={styles.orderMeta}>
                        {order.items.length} item{order.items.length !== 1 ? 's' : ''} · {fmtDate(order.created_at)}
                      </div>
                    </div>
                    <div className={styles.orderRowRight}>
                      <div className={styles.orderTotal}>{fmtCurrency(order.total_amount)}</div>
                      <span
                        className={styles.statusBadge}
                        style={{ background: meta.bg, color: meta.color }}
                      >
                        <span className={styles.statusDot} style={{ background: meta.dot }} />
                        {meta.label}
                      </span>
                    </div>
                  </li>
                )
              })}
            </ul>
          )}
        </div>
      </div>

      {/* ── RIGHT PANEL (detail) ── */}
      <div className={styles.detailPanel}>
        {!selectedOrder ? (
          <div className={styles.emptyDetail}>
            <div className={styles.emptyDetailIcon}>
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} strokeLinecap="round" strokeLinejoin="round">
                <path d="M9 5H7a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2h-2"/>
                <rect x="9" y="3" width="6" height="4" rx="2"/>
                <line x1="9" y1="12" x2="15" y2="12"/>
                <line x1="9" y1="16" x2="12" y2="16"/>
              </svg>
            </div>
            <div className={styles.emptyDetailTitle}>Select an order</div>
            <div className={styles.emptyDetailSub}>Click any order on the left to view its details.</div>
          </div>
        ) : (
          <OrderDetail
            key={selectedOrder.id}
            order={selectedOrder}
            customerMap={customerMap}
            productMap={productMap}
            updatingStatus={updatingStatus}
            actionError={actionError}
            onClearError={() => setActionError(null)}
            onStatusUpdate={handleStatusUpdate}
            onDelete={() => setDeleteTarget(selectedOrder)}
            onClose={() => { setSelectedOrderId(null); setActionError(null) }}
          />
        )}
      </div>

      {/* ── NEW ORDER MODAL ── */}
      {newOpen && (
        <div
          className={styles.overlay}
          onClick={(e) => { if (e.target === e.currentTarget && !newSaving) setNewOpen(false) }}
        >
          <div className={styles.wideModal}>
            {/* Header */}
            <div className={styles.modalHeader}>
              <span className={styles.modalTitle}>New Order</span>
              <button
                className={styles.modalCloseBtn}
                onClick={() => !newSaving && setNewOpen(false)}
                aria-label="Close"
              >
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" width={18} height={18}>
                  <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
                </svg>
              </button>
            </div>

            {/* Body */}
            <div className={styles.modalBody}>
              {newError && <div className={styles.formError}>{newError}</div>}

              {/* Customer */}
              <div className={styles.formField}>
                <label className={styles.formLabel}>
                  Customer <span className={styles.required}>*</span>
                </label>
                <select
                  className={styles.formSelect}
                  value={newForm.customer_id}
                  onChange={(e) => setNewForm((f) => ({ ...f, customer_id: e.target.value }))}
                >
                  <option value="">— Select a customer —</option>
                  {Object.values(customerMap).map((c) => (
                    <option key={c.id} value={c.id}>{c.full_name} ({c.email})</option>
                  ))}
                </select>
              </div>

              {/* Items */}
              <div className={styles.itemsSection}>
                <div className={styles.itemsSectionHeader}>
                  <label className={styles.formLabel}>
                    Order Items <span className={styles.required}>*</span>
                  </label>
                  <button className={styles.addItemBtn} onClick={addItem} type="button">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2.5} strokeLinecap="round" strokeLinejoin="round" width={13} height={13}>
                      <line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>
                    </svg>
                    Add Item
                  </button>
                </div>

                {newForm.items.length === 0 ? (
                  <div className={styles.noItems}>
                    No items yet. Click "Add Item" above to begin.
                  </div>
                ) : (
                  <>
                    <div className={styles.itemsHeader}>
                      <span style={{ flex: 1 }}>Product</span>
                      <span style={{ width: 68, textAlign: 'center' }}>Qty</span>
                      <span style={{ width: 88, textAlign: 'right' }}>Line Total</span>
                      <span style={{ width: 32 }} />
                    </div>
                    {newForm.items.map((item) => {
                      const prod     = productMap[item.product_id]
                      const price    = parseFloat(prod?.price ?? 0)
                      const qty      = parseInt(item.quantity, 10) || 0
                      const lineTotal = price * qty
                      return (
                        <div key={item._key} className={styles.itemRow}>
                          <select
                            className={`${styles.formSelect} ${styles.itemProductSelect}`}
                            value={item.product_id}
                            onChange={(e) => updateItem(item._key, 'product_id', e.target.value)}
                          >
                            <option value="">— Select product —</option>
                            {activeProducts.map((p) => (
                              <option key={p.id} value={p.id}>
                                {p.name} — Stock: {p.stock_quantity}
                              </option>
                            ))}
                          </select>
                          <input
                            type="number"
                            min="1"
                            step="1"
                            className={`${styles.formInput} ${styles.itemQtyInput}`}
                            value={item.quantity}
                            onChange={(e) => updateItem(item._key, 'quantity', e.target.value)}
                          />
                          <span className={styles.itemLineTotal}>
                            {fmtCurrency(lineTotal)}
                          </span>
                          <button
                            className={styles.removeItemBtn}
                            onClick={() => removeItem(item._key)}
                            type="button"
                            title="Remove"
                            disabled={newForm.items.length === 1}
                          >
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" width={14} height={14}>
                              <line x1="18" y1="6" x2="6" y2="18"/>
                              <line x1="6" y1="6" x2="18" y2="18"/>
                            </svg>
                          </button>
                        </div>
                      )
                    })}
                  </>
                )}
              </div>

              {/* Estimated total */}
              {newForm.items.length > 0 && (
                <div className={styles.newOrderTotal}>
                  <span>Estimated Total</span>
                  <span className={styles.newOrderTotalAmt}>{fmtCurrency(newOrderTotal)}</span>
                </div>
              )}
            </div>

            {/* Footer */}
            <div className={styles.modalFooter}>
              <button
                className={styles.btnCancel}
                onClick={() => !newSaving && setNewOpen(false)}
                disabled={newSaving}
              >
                Cancel
              </button>
              <button
                className={styles.btnPrimary}
                onClick={handleCreateOrder}
                disabled={newSaving}
              >
                {newSaving ? 'Creating…' : 'Create Order'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── DELETE CONFIRM ── */}
      {deleteTarget && (
        <ConfirmDialog
          title="Delete Order"
          message={`Order #${String(deleteTarget.id).padStart(4, '0')} will be permanently deleted. This cannot be undone.`}
          confirmLabel="Delete Order"
          onConfirm={handleDelete}
          onCancel={() => setDeleteTarget(null)}
          loading={deleting}
        />
      )}
    </div>
  )
}

// ── Order detail panel ────────────────────────────────────────────────────────

function OrderDetail({ order, customerMap, productMap, updatingStatus, actionError, onClearError, onStatusUpdate, onDelete, onClose }) {
  const customer    = customerMap[order.customer_id]
  const meta        = STATUS_META[order.order_status] ?? STATUS_META.pending
  const transitions = TRANSITIONS[order.order_status] ?? []

  return (
    <div className={styles.detail}>
      {/* Header */}
      <div className={styles.detailHeader}>
        <div className={styles.detailHeaderLeft}>
          <div className={styles.detailOrderNum}>
            Order #{String(order.id).padStart(4, '0')}
          </div>
          <span
            className={styles.statusBadge}
            style={{ background: meta.bg, color: meta.color }}
          >
            <span className={styles.statusDot} style={{ background: meta.dot }} />
            {meta.label}
          </span>
        </div>
        <button className={styles.detailClose} onClick={onClose} title="Close">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" width={18} height={18}>
            <line x1="18" y1="6" x2="6" y2="18"/>
            <line x1="6" y1="6" x2="18" y2="18"/>
          </svg>
        </button>
      </div>

      {/* Scrollable body */}
      <div className={styles.detailBody}>

        {/* Timestamps */}
        <div className={styles.detailDates}>
          <div className={styles.detailDateItem}>
            <span className={styles.detailDateLabel}>Placed</span>
            <span className={styles.detailDateValue}>{fmtDate(order.created_at)}</span>
          </div>
          <div className={styles.detailDateItem}>
            <span className={styles.detailDateLabel}>Last Updated</span>
            <span className={styles.detailDateValue}>{fmtDate(order.updated_at)}</span>
          </div>
        </div>

        {/* Customer */}
        <div className={styles.detailSection}>
          <div className={styles.detailSectionTitle}>Customer</div>
          <div className={styles.customerCard}>
            <div className={styles.customerAvatar}>
              {initials(customer?.full_name ?? '')}
            </div>
            <div className={styles.customerInfo}>
              <div className={styles.customerInfoName}>
                {customer?.full_name ?? `Customer #${order.customer_id}`}
              </div>
              {customer?.email && (
                <a href={`mailto:${customer.email}`} className={styles.customerInfoEmail}>
                  {customer.email}
                </a>
              )}
              {customer?.phone_number && (
                <div className={styles.customerInfoPhone}>{customer.phone_number}</div>
              )}
            </div>
          </div>
        </div>

        {/* Items */}
        <div className={styles.detailSection}>
          <div className={styles.detailSectionTitle}>
            Items
            <span className={styles.itemsCountBadge}>{order.items.length}</span>
          </div>
          <div className={styles.itemsTable}>
            <div className={styles.itemsTableHead}>
              <span style={{ flex: 1 }}>Product</span>
              <span style={{ width: 44, textAlign: 'center' }}>Qty</span>
              <span style={{ width: 78, textAlign: 'right' }}>Unit</span>
              <span style={{ width: 88, textAlign: 'right' }}>Total</span>
            </div>
            {order.items.map((item) => {
              const prod = productMap[item.product_id]
              return (
                <div key={item.id} className={styles.itemsTableRow}>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div className={styles.itemName}>
                      {prod?.name ?? `Product #${item.product_id}`}
                    </div>
                    {prod?.sku && (
                      <div className={styles.itemSku}>{prod.sku}</div>
                    )}
                  </div>
                  <span style={{ width: 44, textAlign: 'center', color: 'var(--color-text-secondary)', fontSize: 13.5 }}>
                    {item.quantity}
                  </span>
                  <span style={{ width: 78, textAlign: 'right', fontSize: 13.5, color: 'var(--color-text-secondary)' }}>
                    {fmtCurrency(item.price)}
                  </span>
                  <span style={{ width: 88, textAlign: 'right', fontWeight: 500, fontSize: 13.5 }}>
                    {fmtCurrency(item.line_total)}
                  </span>
                </div>
              )
            })}
          </div>
        </div>

        {/* Order total */}
        <div className={styles.detailTotal}>
          <span className={styles.detailTotalLabel}>Order Total</span>
          <span className={styles.detailTotalAmt}>{fmtCurrency(order.total_amount)}</span>
        </div>

        {/* Action error */}
        {actionError && (
          <div className={styles.actionError}>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} width={14} height={14}>
              <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
            </svg>
            {actionError}
            <button className={styles.actionErrorDismiss} onClick={onClearError} aria-label="Dismiss error">×</button>
          </div>
        )}

        {/* Status transitions */}
        {transitions.length > 0 && (
          <div className={styles.detailSection}>
            <div className={styles.detailSectionTitle}>Update Status</div>
            <div className={styles.statusActions}>
              {transitions.map((t) => (
                <button
                  key={t.to}
                  className={`${styles.statusActionBtn} ${styles[`statusActionBtn_${t.variant}`]}`}
                  onClick={() => onStatusUpdate(order.id, t.to)}
                  disabled={updatingStatus}
                >
                  {updatingStatus ? '…' : t.label}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Danger zone */}
        <div className={styles.dangerZone}>
          <button className={styles.deleteOrderBtn} onClick={onDelete}>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" width={14} height={14}>
              <polyline points="3 6 5 6 21 6"/>
              <path d="M19 6l-1 14H6L5 6"/>
              <path d="M10 11v6"/><path d="M14 11v6"/>
              <path d="M9 6V4h6v2"/>
            </svg>
            Delete Order
          </button>
        </div>
      </div>
    </div>
  )
}


