import api from './api'

export const getInventoryTransactions = (params = {}) =>
  api.get('/inventory-transactions', { params }).then((r) => r.data)
