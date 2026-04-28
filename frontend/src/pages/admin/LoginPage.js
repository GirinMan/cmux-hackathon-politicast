import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../../lib/auth';
export default function LoginPage() {
    const { login, token } = useAuth();
    const navigate = useNavigate();
    const location = useLocation();
    const from = location.state?.from ?? '/admin';
    const [username, setUsername] = useState('admin');
    const [password, setPassword] = useState('');
    const [error, setError] = useState(null);
    const [busy, setBusy] = useState(false);
    if (token) {
        navigate(from, { replace: true });
    }
    async function onSubmit(e) {
        e.preventDefault();
        setBusy(true);
        setError(null);
        try {
            await login(username, password);
            navigate(from, { replace: true });
        }
        catch (err) {
            setError(err.message ?? 'login failed');
        }
        finally {
            setBusy(false);
        }
    }
    return (_jsxs("main", { style: { maxWidth: 360, margin: '6rem auto', padding: '0 1rem' }, children: [_jsx("h2", { children: "Admin login" }), _jsxs("form", { onSubmit: onSubmit, className: "card", style: { display: 'grid', gap: '0.75rem' }, children: [_jsxs("label", { children: [_jsx("div", { children: "Username" }), _jsx("input", { value: username, onChange: (e) => setUsername(e.target.value), required: true, style: { width: '100%', padding: '0.5rem', background: '#0b0e14', color: 'inherit', border: '1px solid #1f2330', borderRadius: 4 } })] }), _jsxs("label", { children: [_jsx("div", { children: "Password" }), _jsx("input", { type: "password", value: password, onChange: (e) => setPassword(e.target.value), required: true, style: { width: '100%', padding: '0.5rem', background: '#0b0e14', color: 'inherit', border: '1px solid #1f2330', borderRadius: 4 } })] }), error ? _jsx("p", { style: { color: 'var(--color-fail)', margin: 0 }, children: error }) : null, _jsx("button", { type: "submit", disabled: busy, children: busy ? 'Signing in…' : 'Sign in' })] })] }));
}
