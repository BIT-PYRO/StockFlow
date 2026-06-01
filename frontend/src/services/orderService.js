import api from './api'

export const getOrders = (params = {}) =>
  api.get('/orders', { params }).then((r) => r.data)

export const getOrder = (id) =>
  api.get(`/orders/${id}`).then((r) => r.data)

export const createOrder = (data) =>
  api.post('/orders', data).then((r) => r.data)

export const updateOrderStatus = (id, status) =>
  api.patch(`/orders/${id}/status`, { status }).then((r) => r.data)

export const deleteOrder = (id) =>
  api.delete(`/orders/${id}`)
