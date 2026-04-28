import { Navigate, Outlet, useLocation } from 'react-router-dom';

import { useAuth } from '../lib/auth';

export default function ProtectedRoute() {
  const { token } = useAuth();
  const location = useLocation();
  if (!token) {
    return <Navigate to="/admin/login" replace state={{ from: location.pathname }} />;
  }
  return <Outlet />;
}
