import { BrowserRouter, Route, Routes } from 'react-router-dom'
import AuthCallback from '../pages/AuthCallback'
import Home from '../pages/Home'
import Login from '../pages/Login'
import ProtectedRoute from './ProtectedRoute'

const Router = () => {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/auth/callback" element={<AuthCallback />} />
        <Route element={<ProtectedRoute />}>
          <Route path="/" element={<Home />} />
          <Route path="*" element={<p>Page not found</p>} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}

export default Router