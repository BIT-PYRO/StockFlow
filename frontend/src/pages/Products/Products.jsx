import { useState, useEffect, useCallback } from 'react'
import {
  getProducts,
  createProduct,
  updateProduct,
  deleteProduct,
  restockProduct,
} from '../../services/productService'
import DataTable from '../../components/DataTable/DataTable'
import FormModal, { formStyles } from '../../components/FormModal/FormModal'
import ConfirmDialog from '../../components/ConfirmDialog/ConfirmDialog'
import { TableSkeleton } from '../../components/LoadingSkeleton/LoadingSkeleton'
import EmptyState from '../../components/EmptyState/EmptyState'
import styles from './Products.module.css'

const PAGE_SIZE = 20

const EMPTY_FORM = {
  name: '', sku: '', description: '', price: '',
  stock_quantity: '', category: '', status: 'active',
}

function stockBadge(qty) {
  if (qty === 0) return { bg: 'var(--badge-stock-empty-bg)', color: 'var(--badge-stock-empty-color)' }
  if (qty < 10)  return { bg: 'var(--badge-stock-low-bg)',   color: 'var(--badge-stock-low-color)'   }
  return               { bg: 'var(--badge-stock-ok-bg)',    color: 'var(--badge-stock-ok-color)'    }
}

export default function Products() {
  const [products, setProducts] = useState([])
  const [loading, setLoading]   = useState(true)
  const [error, setError]       = useState(null)

  // filters
  const [search,   setSearch]   = useState('')
  const [category, setCategory] = useState('')
  const [status,   setStatus]   = useState('')
  const [skip,     setSkip]     = useState(0)

  // modal state
  const [modalOpen,   setModalOpen]   = useState(false)
  const [editTarget,  setEditTarget]  = useState(null)   // null = Add, obj = Edit
  const [form,        setForm]        = useState(EMPTY_FORM)
  const [formError,   setFormError]   = useState(null)
  const [saving,      setSaving]      = useState(false)

  // delete confirm
  const [deleteTarget, setDeleteTarget] = useState(null)
  const [deleting,     setDeleting]     = useState(false)
  const [deleteError,  setDeleteError]  = useState(null)

  // restock modal
  const [restockTarget, setRestockTarget] = useState(null)
  const [restockQty,    setRestockQty]    = useState('')
  const [restockSaving, setRestockSaving] = useState(false)
  const [restockError,  setRestockError]  = useState(null)

  // ── Load ──────────────────────────────────────────────────────────
  const load = useCallback(() => {
    setLoading(true)
    setError(null)
    const params = { skip, limit: PAGE_SIZE }
    if (search)   params.search   = search
    if (category) params.category = category
    if (status)   params.status   = status
    getProducts(params)
      .then(setProducts)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }, [skip, search, category, status])

  useEffect(() => { load() }, [load])

  // ── Modal helpers ─────────────────────────────────────────────────
  function openAdd() {
    setEditTarget(null)
    setForm(EMPTY_FORM)
    setFormError(null)
    setModalOpen(true)
  }

  function openEdit(row) {
    setEditTarget(row)
    setForm({
      name:           row.name,
      sku:            row.sku,
      description:    row.description ?? '',
      price:          String(row.price),
      stock_quantity: String(row.stock_quantity),
      category:       row.category ?? '',
      status:         row.status,
    })
    setFormError(null)
    setModalOpen(true)
  }

  function closeModal() {
    if (saving) return
    setModalOpen(false)
  }

  function setField(key, val) {
    setForm((f) => ({ ...f, [key]: val }))
  }

  async function handleSubmit() {
    setFormError(null)
    if (!form.name.trim())       return setFormError('Product name is required.')
    if (!form.sku.trim())        return setFormError('SKU is required.')
    if (!form.price || Number(form.price) <= 0)
                                  return setFormError('Price must be greater than 0.')
    if (form.stock_quantity === '' || Number(form.stock_quantity) < 0)
                                  return setFormError('Stock quantity must be 0 or more.')

    const payload = {
      name:           form.name.trim(),
      sku:            form.sku.trim(),
      description:    form.description.trim(),
      price:          Number(form.price),
      stock_quantity: Number(form.stock_quantity),
      category:       form.category.trim(),
      status:         form.status,
    }

    setSaving(true)
    try {
      if (editTarget) {
        await updateProduct(editTarget.id, payload)
      } else {
        await createProduct(payload)
      }
      setModalOpen(false)
      setSkip(0)
      load()
    } catch (e) {
      const detail = e.response?.data?.detail
      setFormError(Array.isArray(detail)
        ? detail.map((d) => d.msg).join(', ')
        : (detail ?? e.message))
    } finally {
      setSaving(false)
    }
  }

  // ── Delete ────────────────────────────────────────────────────────
  async function handleDelete() {
    setDeleting(true)
    try {
      await deleteProduct(deleteTarget.id)
      setDeleteTarget(null)
      setDeleteError(null)
      load()
    } catch (e) {
      setDeleteTarget(null)
      setDeleteError(e.message ?? 'Failed to delete product.')
    } finally {
      setDeleting(false)
    }
  }
  // ── Restock ────────────────────────────────────────────────
  function openRestock(product) {
    setRestockTarget(product)
    setRestockQty('')
    setRestockError(null)
  }

  async function handleRestock() {
    const qty = Number(restockQty)
    if (!Number.isInteger(qty) || qty <= 0) {
      return setRestockError('Quantity must be a positive whole number.')
    }
    setRestockError(null)
    setRestockSaving(true)
    try {
      await restockProduct(restockTarget.id, { quantity: qty })
      setRestockTarget(null)
      load()
    } catch (e) {
      setRestockError(e.message ?? 'Restock failed.')
    } finally {
      setRestockSaving(false)
    }
  }
  // ── Table columns ─────────────────────────────────────────────────
  const columns = [
    {
      key: 'sku', header: 'SKU', width: '120px',
      render: (r) => <span className={styles.sku}>{r.sku}</span>,
    },
    { key: 'name', header: 'Product Name' },
    {
      key: 'category', header: 'Category',
      render: (r) => r.category
        ? <span className={styles.categoryTag}>{r.category}</span>
        : <span className={styles.muted}>—</span>,
    },
    {
      key: 'price', header: 'Price', width: '100px',
      render: (r) => <span className={styles.price}>${Number(r.price).toFixed(2)}</span>,
    },
    {
      key: 'stock_quantity', header: 'Stock', width: '90px',
      render: (r) => {
        const { bg, color } = stockBadge(r.stock_quantity)
        return (
          <span className={styles.badge} style={{ background: bg, color }}>
            {r.stock_quantity}
          </span>
        )
      },
    },
    {
      key: 'status', header: 'Status', width: '100px',
      render: (r) => (
        <span
          className={styles.badge}
          style={r.status === 'active'
            ? { background: 'var(--color-success-bg)', color: 'var(--color-success)' }
            : { background: 'var(--color-bg)',         color: 'var(--color-text-muted)' }}
        >
          {r.status}
        </span>
      ),
    },
    {
      key: '_actions', header: '', width: '180px',
      render: (r) => (
        <div className={styles.actions}>
          <button
            className={`${styles.actionBtn} ${styles.restockBtn}`}
            onClick={() => openRestock(r)}
            title="Restock product"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" width={14} height={14}>
              <polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/>
              <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/>
            </svg>
            Restock
          </button>
          <button
            className={`${styles.actionBtn} ${styles.editBtn}`}
            onClick={() => openEdit(r)}
            title="Edit product"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" width={14} height={14}>
              <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
              <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
            </svg>
            Edit
          </button>
          <button
            className={`${styles.actionBtn} ${styles.deleteBtn}`}
            onClick={() => setDeleteTarget(r)}
            title="Delete product"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" width={14} height={14}>
              <polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14H6L5 6"/>
              <path d="M10 11v6"/><path d="M14 11v6"/><path d="M9 6V4h6v2"/>
            </svg>
          </button>
        </div>
      ),
    },
  ]

  return (
    <div className={styles.page}>
      {error && (
        <div className={styles.errorBanner}>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} width={16} height={16}>
            <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
          </svg>
          {error}
        </div>
      )}

      {deleteError && (
        <div className={styles.errorBanner}>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} width={16} height={16}>
            <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
          </svg>
          {deleteError}
          <button
            style={{ marginLeft: 'auto', background: 'none', border: 'none', cursor: 'pointer', color: 'inherit', fontSize: 16, lineHeight: 1 }}
            onClick={() => setDeleteError(null)}
            aria-label="Dismiss error"
          >×</button>
        </div>
      )}


      {/* Toolbar */}
      <div className={styles.toolbar}>
        <div className={styles.filters}>
          <div className={styles.searchWrap}>
            <svg className={styles.searchIcon} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
              <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
            </svg>
            <input
              className={styles.searchInput}
              placeholder="Search by name or SKU…"
              value={search}
              onChange={(e) => { setSearch(e.target.value); setSkip(0) }}
            />
          </div>
          <input
            className={styles.filterSelect}
            placeholder="All categories"
            value={category}
            onChange={(e) => { setCategory(e.target.value); setSkip(0) }}
            style={{ width: 150 }}
          />
          <select
            className={styles.filterSelect}
            value={status}
            onChange={(e) => { setStatus(e.target.value); setSkip(0) }}
          >
            <option value="">All statuses</option>
            <option value="active">Active</option>
            <option value="inactive">Inactive</option>
          </select>
        </div>
        <button className={styles.btnPrimary} onClick={openAdd}>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2.5} strokeLinecap="round" strokeLinejoin="round" width={16} height={16}>
            <line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>
          </svg>
          Add Product
        </button>
      </div>

      {/* Table card */}
      <div className={styles.card}>
        {loading ? (
          <div className={styles.skeletonPad}><TableSkeleton rows={8} /></div>
        ) : products.length === 0 ? (
          <EmptyState
            title="No products found"
            description={search || category || status
              ? 'Try adjusting your search or filters.'
              : 'Get started by adding your first product.'}
            actionLabel={!search && !category && !status ? 'Add Product' : undefined}
            onAction={!search && !category && !status ? openAdd : undefined}
          />
        ) : (
          <>
            <DataTable columns={columns} rows={products} />
            <div className={styles.pagination}>
              <span className={styles.paginationInfo}>
                Showing {skip + 1}–{skip + products.length}
              </span>
              <div className={styles.paginationBtns}>
                <button
                  className={styles.pageBtn}
                  disabled={skip === 0}
                  onClick={() => setSkip(Math.max(0, skip - PAGE_SIZE))}
                >
                  ← Previous
                </button>
                <button
                  className={styles.pageBtn}
                  disabled={products.length < PAGE_SIZE}
                  onClick={() => setSkip(skip + PAGE_SIZE)}
                >
                  Next →
                </button>
              </div>
            </div>
          </>
        )}
      </div>

      {/* Add / Edit Modal */}
      {modalOpen && (
        <FormModal
          title={editTarget ? 'Edit Product' : 'Add New Product'}
          onClose={closeModal}
          onSubmit={handleSubmit}
          submitLabel={editTarget ? 'Save Changes' : 'Create Product'}
          loading={saving}
        >
          {formError && <div className={styles.formError}>{formError}</div>}

          <div className={formStyles.field}>
            <label className={formStyles.label}>
              Product Name <span className={formStyles.required}>*</span>
            </label>
            <input
              className={formStyles.input}
              placeholder="e.g. Wireless Mouse"
              value={form.name}
              onChange={(e) => setField('name', e.target.value)}
              autoFocus
            />
          </div>

          <div className={styles.formRow}>
            <div className={formStyles.field}>
              <label className={formStyles.label}>
                SKU <span className={formStyles.required}>*</span>
              </label>
              <input
                className={formStyles.input}
                placeholder="e.g. WM-001"
                value={form.sku}
                onChange={(e) => setField('sku', e.target.value)}
                disabled={!!editTarget}
                style={editTarget ? { opacity: 0.6, cursor: 'not-allowed' } : {}}
              />
            </div>
            <div className={formStyles.field}>
              <label className={formStyles.label}>Category</label>
              <input
                className={formStyles.input}
                placeholder="e.g. Electronics"
                value={form.category}
                onChange={(e) => setField('category', e.target.value)}
              />
            </div>
          </div>

          <div className={styles.formRow}>
            <div className={formStyles.field}>
              <label className={formStyles.label}>
                Price ($) <span className={formStyles.required}>*</span>
              </label>
              <input
                className={formStyles.input}
                type="number"
                min="0.01"
                step="0.01"
                placeholder="0.00"
                value={form.price}
                onChange={(e) => setField('price', e.target.value)}
              />
            </div>
            <div className={formStyles.field}>
              <label className={formStyles.label}>
                Stock Quantity <span className={formStyles.required}>*</span>
              </label>
              <input
                className={formStyles.input}
                type="number"
                min="0"
                step="1"
                placeholder="0"
                value={form.stock_quantity}
                onChange={(e) => setField('stock_quantity', e.target.value)}
              />
            </div>
          </div>

          <div className={formStyles.field}>
            <label className={formStyles.label}>Description</label>
            <textarea
              className={formStyles.textarea}
              rows={3}
              placeholder="Optional product description…"
              value={form.description}
              onChange={(e) => setField('description', e.target.value)}
              style={{ resize: 'vertical' }}
            />
          </div>

          <div className={formStyles.field} style={{ marginBottom: 0 }}>
            <label className={formStyles.label}>Status</label>
            <select
              className={formStyles.select}
              value={form.status}
              onChange={(e) => setField('status', e.target.value)}
            >
              <option value="active">Active</option>
              <option value="inactive">Inactive</option>
            </select>
          </div>
        </FormModal>
      )}

      {/* Restock Modal */}
      {restockTarget && (
        <FormModal
          title={`Restock — ${restockTarget.name}`}
          onClose={() => !restockSaving && setRestockTarget(null)}
          onSubmit={handleRestock}
          submitLabel="Add Stock"
          loading={restockSaving}
        >
          {restockError && <div className={styles.formError}>{restockError}</div>}
          <p className={styles.restockMeta}>
            Current stock: <strong>{restockTarget.stock_quantity}</strong> units
          </p>
          <div className={formStyles.field}>
            <label className={formStyles.label}>
              Quantity to add <span className={formStyles.required}>*</span>
            </label>
            <input
              className={formStyles.input}
              type="number"
              min="1"
              step="1"
              placeholder="e.g. 50"
              value={restockQty}
              onChange={(e) => setRestockQty(e.target.value)}
              autoFocus
            />
          </div>
        </FormModal>
      )}

      {/* Delete confirm */}
      {deleteTarget && (
        <ConfirmDialog
          title="Delete Product"
          message={`"${deleteTarget.name}" will be permanently deleted. This cannot be undone.`}
          confirmLabel="Delete Product"
          onConfirm={handleDelete}
          onCancel={() => setDeleteTarget(null)}
          loading={deleting}
        />
      )}
    </div>
  )
}
