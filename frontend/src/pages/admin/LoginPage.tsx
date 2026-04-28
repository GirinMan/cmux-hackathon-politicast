import { FormEvent, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';

import { useAuth } from '../../lib/auth';

export default function LoginPage() {
  const { login, token } = useAuth();
  const navigate = useNavigate();
  const location = useLocation() as { state?: { from?: string } };
  const from = location.state?.from ?? '/admin';

  const [username, setUsername] = useState('admin');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  if (token) {
    navigate(from, { replace: true });
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await login(username, password);
      navigate(from, { replace: true });
    } catch (err) {
      setError((err as Error).message ?? 'login failed');
    } finally {
      setBusy(false);
    }
  }

  return (
    <main style={{ maxWidth: 360, margin: '6rem auto', padding: '0 1rem' }}>
      <h2>Admin login</h2>
      <form onSubmit={onSubmit} className="card" style={{ display: 'grid', gap: '0.75rem' }}>
        <label>
          <div>Username</div>
          <input
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            required
            style={{ width: '100%', padding: '0.5rem', background: '#0b0e14', color: 'inherit', border: '1px solid #1f2330', borderRadius: 4 }}
          />
        </label>
        <label>
          <div>Password</div>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            style={{ width: '100%', padding: '0.5rem', background: '#0b0e14', color: 'inherit', border: '1px solid #1f2330', borderRadius: 4 }}
          />
        </label>
        {error ? <p style={{ color: 'var(--color-fail)', margin: 0 }}>{error}</p> : null}
        <button type="submit" disabled={busy}>
          {busy ? 'Signing in…' : 'Sign in'}
        </button>
      </form>
    </main>
  );
}
