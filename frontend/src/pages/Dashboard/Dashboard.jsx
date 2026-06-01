import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { getDashboard } from '../../services/dashboardService'
import { getOrders } from '../../services/orderService'
import { getCustomers } from '../../services/customerService'
import KPICard from '../../components/KPICard/KPICard'
import { TableSkeleton, KPIGridSkeleton } from '../../components/LoadingSkeleton/LoadingSkeleton'
import styles from './Dashboard.module.css'

const STATUS_CONFIG = {
  pending:   { color: 'var(--status-pending-color)',   bg: 'var(--status-pending-bg)',   label: 'Pending'   },
  confirmed: { color: 'var(--status-confirmed-color)', bg: 'var(--status-confirmed-bg)', label: 'Confirmed' },
  completed: { color: 'var(--status-completed-color)', bg: 'var(--status-completed-bg)', label: 'Completed' },
  cancelled: { color: 'var(--status-cancelled-color)', bg: 'var(--status-cancelled-bg)', label: 'Cancelled' },
}

function StatusBadge({ status }) {
  const cfg = STATUS_CONFIG[status] ?? STATUS_CONFIG.pending
  return (
    <span className={styles.statusBadge} style={{ background: cfg.bg, color: cfg.color }}>
      {cfg.label}
    </span>
  )
}

function stockLevel(qty) {
  if (qty === 0 || qty <= 3) return { color: 'var(--badge-stock-empty-color)', bg: 'var(--badge-stock-empty-bg)' }
  return                          { color: 'var(--badge-stock-low-color)',   bg: 'var(--badge-stock-low-bg)'   }
}

const fmt = (n) => Number(n ?? 0).toLocaleString()
const fmtCurrency = (n) =>
  Number(n ?? 0).toLocaleString('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 2 })
const fmtDate = (iso) =>
  new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })

export default function Dashboard() {
  const [data,          setData]          = useState(null)
  const [orders,        setOrders]        = useState([])
  const [customerMap,   setCustomerMap]   = useState({})
  const [loading,       setLoading]       = useState(true)
  const [loadingOrders, setLoadingOrders] = useState(true)
  const [error,         setError]         = useState(null)

  useEffect(() => {
    getDashboard()
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))

    getOrders({ skip: 0, limit: 5 })
      .then((res) => setOrders(Array.isArray(res) ? res : res.orders ?? []))
      .catch(() => {})
      .finally(() => setLoadingOrders(false))

    getCustomers({ skip: 0, limit: 500 })
      .then((custs) => {
        const arr = Array.isArray(custs) ? custs : custs.customers ?? []
        setCustomerMap(Object.fromEntries(arr.map((c) => [c.id, c])))
      })
      .catch(() => {})
  }, [])

  const totalForPct = (data?.total_orders ?? 0) || 1

  return (
    <div className={styles.page}>
      {error && (
        <div className={styles.errorBanner}>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} width={16} height={16}>
            <circle cx="12" cy="12" r="10" /><line x1="12" y1="8" x2="12" y2="12" /><line x1="12" y1="16" x2="12.01" y2="16" />
          </svg>
          Failed to load dashboard: {error}
        </div>
      )}

      {/* ── 6 KPI Cards ────────────────────────────────────────────────── */}
      {loading ? (
        <KPIGridSkeleton count={6} />
      ) : (
        <div className={styles.kpiGrid}>
          <KPICard
            label="Total Products" value={fmt(data?.total_products)} variant="primary" sub="In catalog"
            icon={<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/></svg>}
          />
          <KPICard
            label="Total Customers" value={fmt(data?.total_customers)} variant="info" sub="Registered"
            icon={<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>}
          />
          <KPICard
            label="Total Orders" value={fmt(data?.total_orders)} variant="warning" sub="All time"
            icon={<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round"><path d="M6 2L3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4z"/><line x1="3" y1="6" x2="21" y2="6"/><path d="M16 10a4 4 0 0 1-8 0"/></svg>}
          />
          <KPICard
            label="Total Revenue" value={fmtCurrency(data?.total_revenue)} variant="success" sub="Completed orders"
            icon={<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round"><line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg>}
          />
          <KPICard
            label="Pending Orders" value={fmt(data?.pending_orders)} variant="warning" sub="Awaiting action"
            icon={<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>}
          />
          <KPICard
            label="Low Stock Products"
            value={fmt(data?.low_stock_products?.length)}
            variant={(data?.low_stock_products?.length ?? 0) > 0 ? 'danger' : 'success'}
            sub={(data?.low_stock_products?.length ?? 0) > 0 ? 'Needs restocking' : 'All stocked'}
            icon={<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>}
          />
        </div>
      )}

      {/* ── Second section: 3 cards ─────────────────────────────────────── */}
      <div className={styles.bottomGrid}>

        {/* Card 1 – Recent Activity */}
        <div className={styles.card}>
          <div className={styles.cardHeader}>
            <div className={styles.cardTitle}>
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" width={16} height={16}>
                <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
              </svg>
              Recent Activity
            </div>
            <Link to="/orders" className={styles.viewAll}>View all →</Link>
          </div>
          <div className={styles.cardBody}>
            {loadingOrders ? (
              <div className={styles.skeletonPad}><TableSkeleton rows={5} /></div>
            ) : orders.length === 0 ? (
              <div className={styles.emptyState}>No orders found.</div>
            ) : (
              <div className={styles.activityList}>
                {orders.map((order) => (
                  <div key={order.id} className={styles.activityRow}>
                    <div className={styles.activityLeft}>
                      <div className={styles.activityIcon}>
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} width={14} height={14}>
                          <path d="M6 2L3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4z"/><line x1="3" y1="6" x2="21" y2="6"/><path d="M16 10a4 4 0 0 1-8 0"/>
                        </svg>
                      </div>
                      <div>
                        <div className={styles.activityOrderId}>Order #{String(order.id).padStart(4, '0')}</div>
                        <div className={styles.activityMeta}>
                          {customerMap[order.customer_id]?.full_name ?? `Customer #${order.customer_id}`} · {fmtDate(order.created_at)}
                        </div>
                      </div>
                    </div>
                    <div className={styles.activityRight}>
                      <div className={styles.activityAmount}>{fmtCurrency(order.total_amount)}</div>
                      <StatusBadge status={order.order_status} />
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Card 2 – Critical Low Stock */}
        <div className={styles.card}>
          <div className={styles.cardHeader}>
            <div className={styles.cardTitle}>
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" width={16} height={16}>
                <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
                <line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>
              </svg>
              Low Stock Alerts
            </div>
            {!loading && (data?.low_stock_products?.length ?? 0) > 0 && (
              <span className={styles.alertCount}>
                {data.low_stock_products.length}
              </span>
            )}
          </div>
          <div className={styles.cardBody}>
            {loading ? (
              <div className={styles.skeletonPad}><TableSkeleton rows={4} /></div>
            ) : (data?.low_stock_products?.length ?? 0) === 0 ? (
              <div className={styles.emptyState}>
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} width={36} height={36} style={{ color: '#16A34A' }}>
                  <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/>
                </svg>
                All products are well stocked!
              </div>
            ) : (
              <div className={styles.stockList}>
                {data.low_stock_products.map((p) => {
                  const { color, bg } = stockLevel(p.stock_quantity)
                  const pct = Math.min((p.stock_quantity / 10) * 100, 100)
                  return (
                    <div key={p.id} className={styles.stockRow}>
                      <div className={styles.stockInfo}>
                        <div className={styles.stockName}>{p.name}</div>
                        <div className={styles.stockSku}>{p.sku}{p.category ? ` · ${p.category}` : ''}</div>
                        <div className={styles.stockBar}>
                          <div className={styles.stockBarFill} style={{ width: `${pct}%`, background: color }} />
                        </div>
                      </div>
                      <span className={styles.stockQty} style={{ background: bg, color }}>
                        {p.stock_quantity}
                      </span>
                    </div>
                  )
                })}
              </div>
            )}
          </div>
        </div>

        {/* Card 3 – Order Status Breakdown */}
        <div className={styles.card}>
          <div className={styles.cardHeader}>
            <div className={styles.cardTitle}>
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" width={16} height={16}>
                <line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/>
              </svg>
              Order Status
            </div>
          </div>
          <div className={styles.cardBody}>
            {loading ? (
              <div className={styles.skeletonPad}><TableSkeleton rows={4} /></div>
            ) : (
              <div className={styles.statusBreakdown}>
                {[
                  { key: 'pending',   count: data?.pending_orders   ?? 0 },
                  { key: 'confirmed', count: data?.confirmed_orders ?? 0 },
                  { key: 'completed', count: data?.completed_orders ?? 0 },
                  { key: 'cancelled', count: data?.cancelled_orders ?? 0 },
                ].map(({ key, count }) => {
                  const cfg = STATUS_CONFIG[key]
                  const pct = Math.round((count / totalForPct) * 100)
                  return (
                    <div key={key} className={styles.statusItem}>
                      <div className={styles.statusItemHeader}>
                        <div className={styles.statusItemLabel}>
                          <div className={styles.dot} style={{ background: cfg.color }} />
                          {cfg.label}
                        </div>
                        <div className={styles.statusItemMeta}>
                          <span className={styles.statusItemCount}>{fmt(count)}</span>
                          <span className={styles.statusItemPct}>{pct}%</span>
                        </div>
                      </div>
                      <div className={styles.progressTrack}>
                        <div
                          className={styles.progressFill}
                          style={{ width: `${pct}%`, background: cfg.color }}
                        />
                      </div>
                    </div>
                  )
                })}
                <div className={styles.totalRow}>
                  <span>Total Orders</span>
                  <strong>{fmt(data?.total_orders)}</strong>
                </div>
              </div>
            )}
          </div>
        </div>

      </div>
    </div>
  )
}
