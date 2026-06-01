import styles from './KPICard.module.css'

const VARIANT_STYLES = {
  primary: { bg: 'var(--color-primary-light)', color: 'var(--color-primary)' },
  success: { bg: 'var(--color-success-bg)',    color: 'var(--color-success)' },
  warning: { bg: 'var(--color-warning-bg)',    color: 'var(--color-warning)' },
  danger:  { bg: 'var(--color-danger-bg)',     color: 'var(--color-danger)'  },
  info:    { bg: 'var(--color-info-bg)',       color: 'var(--color-info)'    },
}

export default function KPICard({ label, value, icon, variant = 'primary', sub }) {
  const vs = VARIANT_STYLES[variant] ?? VARIANT_STYLES.primary
  return (
    <div className={styles.card}>
      <div className={styles.iconWrap} style={{ background: vs.bg, color: vs.color }}>
        {icon}
      </div>
      <div className={styles.body}>
        <div className={styles.label}>{label}</div>
        <div className={styles.value}>{value}</div>
        {sub && <div className={styles.sub}>{sub}</div>}
      </div>
    </div>
  )
}
