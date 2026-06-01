import { useState, useEffect, useCallback } from 'react'
import { getInventoryTransactions } from '../../services/inventoryService'
import { getProducts }               from '../../services/productService'
import DataTable                     from '../../components/DataTable/DataTable'
import { TableSkeleton }             from '../../components/LoadingSkeleton/LoadingSkeleton'
import EmptyState                    from '../../components/EmptyState/EmptyState'
import styles                        from './InventoryTransactions.module.css'

// ── Constants ─────────────────────────────────────────────────────────────────

const TYPE_META = {
  IN:         { label: 'IN',         bg: 'var(--txn-in-bg)',  color: 'var(--txn-in-color)',  dot: 'var(--txn-in-dot)'  },
  OUT:        { label: 'OUT',        bg: 'var(--txn-out-bg)', color: 'var(--txn-out-color)', dot: 'var(--txn-out-dot)' },
  ADJUSTMENT: { label: 'ADJUSTMENT', bg: 'var(--txn-adj-bg)', color: 'var(--txn-adj-color)', dot: 'var(--txn-adj-dot)' },
}

const PAGE_SIZE = 20

// ── Helpers ───────────────────────────────────────────────────────────────────

function fmtDateTime(iso) {
  return new Date(iso).toLocaleString('en-US', {
    month: 'short', day: 'numeric', year: 'numeric',
    hour: 'numeric', minute: '2-digit', hour12: true,
  })
}

function today() {
  return new Date().toISOString().slice(0, 10)
}

// ── Component ─────────────────────────────────────────────────────────────────

export default function InventoryTransactions() {
  // Data
  const [data, setData]         = useState({ transactions: [], total: 0, total_pages: 1, page: 1, page_size: PAGE_SIZE })
  const [loading, setLoading]   = useState(true)
  const [error, setError]       = useState(null)
  const [products, setProducts] = useState([])

  // Filters
  const [productFilter, setProductFilter] = useState('')
  const [typeFilter,    setTypeFilter]    = useState('')
  const [startDate,     setStartDate]     = useState('')
  const [endDate,       setEndDate]       = useState('')
  const [page,          setPage]          = useState(1)

  // track whether filters are "active" (for reset button)
  const hasFilters = productFilter || typeFilter || startDate || endDate

  // ── Load products for dropdown ─────────────────────────────────────
  useEffect(() => {
    getProducts({ limit: 500, status: 'active' })
      .then(setProducts)
      .catch(() => {})
  }, [])

  // ── Load transactions ──────────────────────────────────────────────
  const load = useCallback(() => {
    setLoading(true)
    setError(null)
    const params = { page, page_size: PAGE_SIZE }
    if (productFilter) params.product_id       = productFilter
    if (typeFilter)    params.transaction_type = typeFilter
    if (startDate)     params.start_date       = startDate
    if (endDate)       params.end_date         = endDate
    getInventoryTransactions(params)
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }, [page, productFilter, typeFilter, startDate, endDate])

  useEffect(() => { load() }, [load])

  // ── Filter helpers ─────────────────────────────────────────────────
  function changeFilter(setter) {
    return (e) => { setter(e.target.value); setPage(1) }
  }

  function resetFilters() {
    setProductFilter('')
    setTypeFilter('')
    setStartDate('')
    setEndDate('')
    setPage(1)
  }

  // ── Table columns ──────────────────────────────────────────────────
  const columns = [
    {
      key: 'created_at', header: 'Timestamp', width: '170px',
      render: (r) => (
        <span className={styles.timestamp}>{fmtDateTime(r.created_at)}</span>
      ),
    },
    {
      key: 'product_name', header: 'Product',
      render: (r) => (
        <div className={styles.productCell}>
          <span className={styles.productName}>{r.product_name}</span>
        </div>
      ),
    },
    {
      key: 'sku', header: 'SKU', width: '120px',
      render: (r) => <span className={styles.sku}>{r.sku}</span>,
    },
    {
      key: 'transaction_type', header: 'Type', width: '120px',
      render: (r) => {
        const m = TYPE_META[r.transaction_type] ?? TYPE_META.ADJUSTMENT
        return (
          <span className={styles.typeBadge} style={{ background: m.bg, color: m.color }}>
            <span className={styles.typeDot} style={{ background: m.dot }} />
            {m.label}
          </span>
        )
      },
    },
    {
      key: 'quantity', header: 'Quantity', width: '90px',
      render: (r) => {
        const m    = TYPE_META[r.transaction_type] ?? TYPE_META.ADJUSTMENT
        const sign = r.transaction_type === 'OUT' ? '−' : '+'
        return (
          <span className={styles.qty} style={{ color: m.color }}>
            {sign}{r.quantity}
          </span>
        )
      },
    },
    {
      key: 'previous_stock', header: 'Prev. Stock', width: '100px',
      render: (r) => <span className={styles.stockNum}>{r.previous_stock}</span>,
    },
    {
      key: 'new_stock', header: 'New Stock', width: '100px',
      render: (r) => {
        const up = r.new_stock > r.previous_stock
        const dn = r.new_stock < r.previous_stock
        return (
          <span
            className={styles.newStock}
            style={{
              color: up ? 'var(--color-success)' : dn ? 'var(--color-danger)' : 'var(--color-text-secondary)',
            }}
          >
            {r.new_stock}
            {up && (
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2.5} strokeLinecap="round" strokeLinejoin="round" width={12} height={12}>
                <line x1="12" y1="19" x2="12" y2="5"/><polyline points="5 12 12 5 19 12"/>
              </svg>
            )}
            {dn && (
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2.5} strokeLinecap="round" strokeLinejoin="round" width={12} height={12}>
                <line x1="12" y1="5" x2="12" y2="19"/><polyline points="19 12 12 19 5 12"/>
              </svg>
            )}
          </span>
        )
      },
    },
  ]

  // ── Summary counts ─────────────────────────────────────────────────
  const typeCounts = data.transactions.reduce((acc, t) => {
    acc[t.transaction_type] = (acc[t.transaction_type] ?? 0) + 1
    return acc
  }, {})

  // ── Render ─────────────────────────────────────────────────────────
  return (
    <div className={styles.page}>

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

      {/* ── Toolbar ── */}
      <div className={styles.toolbar}>
        <div className={styles.filters}>

          {/* Product filter */}
          <div className={styles.filterWrap}>
            <svg className={styles.filterIcon} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
              <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/>
            </svg>
            <select
              className={styles.filterSelect}
              value={productFilter}
              onChange={changeFilter(setProductFilter)}
            >
              <option value="">All Products</option>
              {products.map((p) => (
                <option key={p.id} value={p.id}>{p.name}</option>
              ))}
            </select>
          </div>

          {/* Type filter */}
          <select
            className={styles.filterSelect}
            value={typeFilter}
            onChange={changeFilter(setTypeFilter)}
          >
            <option value="">All Types</option>
            <option value="IN">IN — Restock / Return</option>
            <option value="OUT">OUT — Sale / Deduction</option>
            <option value="ADJUSTMENT">ADJUSTMENT — Correction</option>
          </select>

          {/* Date range */}
          <div className={styles.dateRange}>
            <input
              type="date"
              className={styles.dateInput}
              value={startDate}
              max={endDate || today()}
              onChange={changeFilter(setStartDate)}
              title="Start date"
            />
            <span className={styles.dateRangeSep}>→</span>
            <input
              type="date"
              className={styles.dateInput}
              value={endDate}
              min={startDate || undefined}
              max={today()}
              onChange={changeFilter(setEndDate)}
              title="End date"
            />
          </div>

          {hasFilters && (
            <button className={styles.resetBtn} onClick={resetFilters} title="Clear all filters">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" width={13} height={13}>
                <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
              </svg>
              Clear
            </button>
          )}
        </div>

        {/* Total badge */}
        {!loading && (
          <div className={styles.totalBadge}>
            {data.total.toLocaleString()} record{data.total !== 1 ? 's' : ''}
          </div>
        )}
      </div>

      {/* ── Type summary chips (visible when data loaded) ── */}
      {!loading && data.transactions.length > 0 && (
        <div className={styles.summaryRow}>
          {['IN', 'OUT', 'ADJUSTMENT'].map((type) => {
            const m = TYPE_META[type]
            const n = typeCounts[type] ?? 0
            return (
              <button
                key={type}
                className={`${styles.summaryChip} ${typeFilter === type ? styles.summaryChipActive : ''}`}
                style={typeFilter === type ? { borderColor: m.dot, background: m.bg } : {}}
                onClick={() => {
                  setTypeFilter(typeFilter === type ? '' : type)
                  setPage(1)
                }}
                title={`Filter by ${type}`}
              >
                <span className={styles.summaryDot} style={{ background: m.dot }} />
                <span style={{ color: m.color, fontWeight: 600 }}>{type}</span>
                <span className={styles.summaryCount}>{n}</span>
              </button>
            )
          })}
        </div>
      )}

      {/* ── Table card ── */}
      <div className={styles.card}>
        {loading ? (
          <div className={styles.skeletonPad}><TableSkeleton rows={10} /></div>
        ) : data.transactions.length === 0 ? (
          <EmptyState
            title={hasFilters ? 'No transactions match your filters' : 'No transactions yet'}
            description={
              hasFilters
                ? 'Try adjusting the product, type, or date range filters.'
                : 'Stock movements are recorded here automatically when orders are placed or products are restocked.'
            }
            actionLabel={hasFilters ? 'Clear Filters' : undefined}
            onAction={hasFilters ? resetFilters : undefined}
          />
        ) : (
          <>
            <DataTable columns={columns} rows={data.transactions} keyField="transaction_id" />

            <div className={styles.pagination}>
              <span className={styles.paginationInfo}>
                Page <strong>{data.page}</strong> of <strong>{data.total_pages}</strong>
                <span className={styles.paginationTotal}> — {data.total.toLocaleString()} total</span>
              </span>
              <div className={styles.paginationBtns}>
                <button
                  className={styles.pageBtn}
                  disabled={page === 1}
                  onClick={() => setPage(page - 1)}
                >
                  ← Previous
                </button>

                {/* Page number pills */}
                {data.total_pages <= 7
                  ? Array.from({ length: data.total_pages }, (_, i) => i + 1).map((p) => (
                      <button
                        key={p}
                        className={`${styles.pageNumBtn} ${p === page ? styles.pageNumBtnActive : ''}`}
                        onClick={() => setPage(p)}
                      >
                        {p}
                      </button>
                    ))
                  : null}

                <button
                  className={styles.pageBtn}
                  disabled={page >= data.total_pages}
                  onClick={() => setPage(page + 1)}
                >
                  Next →
                </button>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
