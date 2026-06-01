import { useState, useEffect, useCallback, useMemo } from 'react'
import {
  getCustomers,
  createCustomer,
  updateCustomer,
  deleteCustomer,
} from '../../services/customerService'
import DataTable from '../../components/DataTable/DataTable'
import FormModal, { formStyles } from '../../components/FormModal/FormModal'
import ConfirmDialog from '../../components/ConfirmDialog/ConfirmDialog'
import { TableSkeleton } from '../../components/LoadingSkeleton/LoadingSkeleton'
import EmptyState from '../../components/EmptyState/EmptyState'
import styles from './Customers.module.css'

const PAGE_SIZE = 20

const EMPTY_FORM = { full_name: '', email: '', phone_number: '', address: '' }

function initials(name) {
  return name
    .split(' ')
    .map((w) => w[0])
    .slice(0, 2)
    .join('')
    .toUpperCase()
}

export default function Customers() {
  const [customers, setCustomers] = useState([])
  const [loading, setLoading]     = useState(true)
  const [error, setError]         = useState(null)
  const [skip, setSkip]           = useState(0)
  const [search, setSearch]       = useState('')

  // modal state
  const [modalOpen,  setModalOpen]  = useState(false)
  const [editTarget, setEditTarget] = useState(null)
  const [form,       setForm]       = useState(EMPTY_FORM)
  const [formError,  setFormError]  = useState(null)
  const [saving,     setSaving]     = useState(false)

  // delete confirm
  const [deleteTarget, setDeleteTarget] = useState(null)
  const [deleting,     setDeleting]     = useState(false)

  // ── Load ──────────────────────────────────────────────────────────
  const load = useCallback(() => {
    setLoading(true)
    setError(null)
    getCustomers({ skip, limit: PAGE_SIZE })
      .then(setCustomers)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }, [skip])

  useEffect(() => { load() }, [load])

  // ── Client-side search filter ─────────────────────────────────────
  const filtered = useMemo(() => {
    if (!search.trim()) return customers
    const q = search.toLowerCase()
    return customers.filter(
      (c) =>
        c.full_name.toLowerCase().includes(q) ||
        c.email.toLowerCase().includes(q) ||
        (c.phone_number ?? '').toLowerCase().includes(q),
    )
  }, [customers, search])

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
      full_name:    row.full_name,
      email:        row.email,
      phone_number: row.phone_number ?? '',
      address:      row.address ?? '',
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
    if (!form.full_name.trim()) return setFormError('Full name is required.')
    if (!form.email.trim())     return setFormError('Email address is required.')
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email))
                                return setFormError('Enter a valid email address.')

    const payload = {
      full_name:    form.full_name.trim(),
      email:        form.email.trim().toLowerCase(),
      phone_number: form.phone_number.trim(),
      address:      form.address.trim(),
    }

    setSaving(true)
    try {
      if (editTarget) {
        await updateCustomer(editTarget.id, payload)
      } else {
        await createCustomer(payload)
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
      await deleteCustomer(deleteTarget.id)
      setDeleteTarget(null)
      load()
    } catch {
      setDeleteTarget(null)
    } finally {
      setDeleting(false)
    }
  }

  // ── Table columns ─────────────────────────────────────────────────
  const columns = [
    {
      key: 'full_name', header: 'Customer Name',
      render: (r) => (
        <div className={styles.nameCell}>
          <div className={styles.avatar}>{initials(r.full_name)}</div>
          <span className={styles.nameText}>{r.full_name}</span>
        </div>
      ),
    },
    {
      key: 'email', header: 'Email',
      render: (r) => (
        <a href={`mailto:${r.email}`} className={styles.emailLink}>{r.email}</a>
      ),
    },
    {
      key: 'phone_number', header: 'Phone', width: '140px',
      render: (r) => r.phone_number
        ? <span>{r.phone_number}</span>
        : <span className={styles.muted}>—</span>,
    },
    {
      key: 'address', header: 'Address',
      render: (r) => r.address
        ? <span className={styles.addressText} title={r.address}>{r.address}</span>
        : <span className={styles.muted}>—</span>,
    },
    {
      key: '_actions', header: '', width: '104px',
      render: (r) => (
        <div className={styles.actions}>
          <button
            className={`${styles.actionBtn} ${styles.editBtn}`}
            onClick={() => openEdit(r)}
            title="Edit customer"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" width={13} height={13}>
              <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
              <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
            </svg>
            Edit
          </button>
          <button
            className={`${styles.actionBtn} ${styles.deleteBtn}`}
            onClick={() => setDeleteTarget(r)}
            title="Delete customer"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" width={13} height={13}>
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

      {/* Toolbar */}
      <div className={styles.toolbar}>
        <div className={styles.filters}>
          <div className={styles.searchWrap}>
            <svg className={styles.searchIcon} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
              <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
            </svg>
            <input
              className={styles.searchInput}
              placeholder="Search by name, email or phone…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
        </div>
        <button className={styles.btnPrimary} onClick={openAdd}>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2.5} strokeLinecap="round" strokeLinejoin="round" width={16} height={16}>
            <line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>
          </svg>
          Add Customer
        </button>
      </div>

      {/* Table card */}
      <div className={styles.card}>
        {loading ? (
          <div className={styles.skeletonPad}><TableSkeleton rows={8} /></div>
        ) : filtered.length === 0 ? (
          <EmptyState
            title={search ? 'No customers match your search' : 'No customers yet'}
            description={search ? 'Try a different name, email or phone number.' : 'Add your first customer to get started.'}
            actionLabel={!search ? 'Add Customer' : undefined}
            onAction={!search ? openAdd : undefined}
          />
        ) : (
          <>
            <DataTable columns={columns} rows={filtered} />
            <div className={styles.pagination}>
              <span className={styles.paginationInfo}>
                {search
                  ? `${filtered.length} result${filtered.length !== 1 ? 's' : ''}`
                  : `Showing ${skip + 1}–${skip + customers.length}`}
              </span>
              {!search && (
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
                    disabled={customers.length < PAGE_SIZE}
                    onClick={() => setSkip(skip + PAGE_SIZE)}
                  >
                    Next →
                  </button>
                </div>
              )}
            </div>
          </>
        )}
      </div>

      {/* Add / Edit Modal */}
      {modalOpen && (
        <FormModal
          title={editTarget ? 'Edit Customer' : 'Add New Customer'}
          onClose={closeModal}
          onSubmit={handleSubmit}
          submitLabel={editTarget ? 'Save Changes' : 'Create Customer'}
          loading={saving}
        >
          {formError && <div className={styles.formError}>{formError}</div>}

          <div className={formStyles.field}>
            <label className={formStyles.label}>
              Full Name <span className={formStyles.required}>*</span>
            </label>
            <input
              className={formStyles.input}
              placeholder="e.g. Jane Smith"
              value={form.full_name}
              onChange={(e) => setField('full_name', e.target.value)}
              autoFocus
            />
          </div>

          <div className={formStyles.field}>
            <label className={formStyles.label}>
              Email Address <span className={formStyles.required}>*</span>
            </label>
            <input
              className={formStyles.input}
              type="email"
              placeholder="e.g. jane@example.com"
              value={form.email}
              onChange={(e) => setField('email', e.target.value)}
            />
          </div>

          <div className={styles.formRow}>
            <div className={formStyles.field}>
              <label className={formStyles.label}>Phone Number</label>
              <input
                className={formStyles.input}
                type="tel"
                placeholder="e.g. +1 555 000 1234"
                value={form.phone_number}
                onChange={(e) => setField('phone_number', e.target.value)}
              />
            </div>
            <div className={formStyles.field} style={{ marginBottom: 0 }}>
              {/* spacer — address below spans full width */}
            </div>
          </div>

          <div className={formStyles.field} style={{ marginBottom: 0 }}>
            <label className={formStyles.label}>Address</label>
            <textarea
              className={formStyles.textarea}
              rows={3}
              placeholder="Street, City, State, ZIP"
              value={form.address}
              onChange={(e) => setField('address', e.target.value)}
              style={{ resize: 'vertical' }}
            />
          </div>
        </FormModal>
      )}

      {/* Delete confirm */}
      {deleteTarget && (
        <ConfirmDialog
          title="Delete Customer"
          message={`"${deleteTarget.full_name}" and all associated data will be permanently deleted.`}
          confirmLabel="Delete Customer"
          onConfirm={handleDelete}
          onCancel={() => setDeleteTarget(null)}
          loading={deleting}
        />
      )}
    </div>
  )
}

