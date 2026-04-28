import { jsx as _jsx } from "react/jsx-runtime";
import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { useAuth } from '../lib/auth';
export default function ProtectedRoute() {
    const { token } = useAuth();
    const location = useLocation();
    if (!token) {
        return _jsx(Navigate, { to: "/admin/login", replace: true, state: { from: location.pathname } });
    }
    return _jsx(Outlet, {});
}
