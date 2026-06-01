import { useEffect } from 'react'
import styles from './FormModal.module.css'

export default function FormModal({ title, onClose, onSubmit, submitLabel = 'Save', loading = false, children }) {
  // Close on Escape key — skip when a submission is in progress
  useEffect(() => {
    const handler = (e) => { if (e.key === 'Escape' && !loading) onClose() }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [onClose, loading])

  return (
    <div className={styles.overlay} onClick={(e) => e.target === e.currentTarget && !loading && onClose()}>
      <div className={styles.modal} role="dialog" aria-modal="true" aria-label={title}>
        <div className={styles.header}>
          <div className={styles.title}>{title}</div>
          <button className={styles.closeBtn} onClick={onClose} aria-label="Close">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>

        <div className={styles.body}>{children}</div>

        <div className={styles.footer}>
          <button className={styles.btnCancel} onClick={onClose} disabled={loading}>
            Cancel
          </button>
          <button className={styles.btnSubmit} onClick={onSubmit} disabled={loading}>
            {loading ? 'Saving…' : submitLabel}
          </button>
        </div>
      </div>
    </div>
  )
}

export { styles as formStyles }
