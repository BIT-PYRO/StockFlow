import api from './api'

export const getProducts = (params = {}) =>
  api.get('/products', { params }).then((r) => r.data)

export const getProduct = (id) =>
  api.get(`/products/${id}`).then((r) => r.data)

export const createProduct = (data) =>
  api.post('/products', data).then((r) => r.data)

export const updateProduct = (id, data) =>
  api.put(`/products/${id}`, data).then((r) => r.data)

export const deleteProduct = (id) =>
  api.delete(`/products/${id}`)

export const restockProduct = (id, data) =>
  api.post(`/products/${id}/restock`, data).then((r) => r.data)
