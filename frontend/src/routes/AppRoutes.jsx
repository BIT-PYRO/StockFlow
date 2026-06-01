import { Routes, Route, Navigate } from 'react-router-dom'
import MainLayout from '../layouts/MainLayout'
import Dashboard from '../pages/Dashboard/Dashboard'
import Products from '../pages/Products/Products'
import Customers from '../pages/Customers/Customers'
import Orders from '../pages/Orders/Orders'
import InventoryTransactions from '../pages/InventoryTransactions/InventoryTransactions'

export default function AppRoutes() {
  return (
    <Routes>
      <Route element={<MainLayout />}>
        <Route path="/"                        element={<Dashboard />} />
        <Route path="/products"                element={<Products />} />
        <Route path="/customers"               element={<Customers />} />
        <Route path="/orders"                  element={<Orders />} />
        <Route path="/inventory-transactions"  element={<InventoryTransactions />} />
        <Route path="*"                        element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  )
}
