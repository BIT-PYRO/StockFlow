import styles from './DataTable.module.css'

/**
 * columns: Array<{ key: string, header: string, render?: (row) => ReactNode, width?: string }>
 * rows: Array<object>
 * keyField: string (default 'id')
 */
export default function DataTable({ columns = [], rows = [], keyField = 'id' }) {
  return (
    <div className={styles.wrap}>
      <div className={styles.tableWrap}>
        <table>
          <thead>
            <tr>
              {columns.map((col) => (
                <th key={col.key} style={col.width ? { width: col.width } : undefined}>
                  {col.header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row[keyField]}>
                {columns.map((col) => (
                  <td key={col.key}>
                    {col.render ? col.render(row) : row[col.key] ?? '—'}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
