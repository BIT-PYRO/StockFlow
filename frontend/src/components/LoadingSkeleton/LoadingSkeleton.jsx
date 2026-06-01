import styles from './LoadingSkeleton.module.css'

export function SkeletonCard() {
  return <div className={styles.skeletonCard} />
}

export function SkeletonRow() {
  return <div className={styles.skeletonRow} />
}

export function SkeletonText({ width = '100%' }) {
  return <div className={styles.skeletonText} style={{ width }} />
}

export function KPIGridSkeleton({ count = 4 }) {
  return (
    <div className={styles.grid} style={{ gridTemplateColumns: `repeat(${count}, 1fr)` }}>
      {Array.from({ length: count }).map((_, i) => (
        <SkeletonCard key={i} />
      ))}
    </div>
  )
}

export function TableSkeleton({ rows = 6 }) {
  return (
    <div>
      {Array.from({ length: rows }).map((_, i) => (
        <SkeletonRow key={i} />
      ))}
    </div>
  )
}
