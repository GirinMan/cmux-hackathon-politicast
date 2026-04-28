import { describe, expect, it } from 'vitest';

import { ADMIN_TOKEN_KEY, createApi } from '../lib/api';

describe('api client', () => {
  it('attaches Bearer header for /admin/api/* when token present', async () => {
    localStorage.setItem(ADMIN_TOKEN_KEY, 'tok-xyz');
    const api = createApi('http://localhost:0');
    const cfg = await (api.interceptors.request as unknown as { handlers: Array<{ fulfilled: Function }> })
      .handlers[0]
      .fulfilled({ url: '/admin/api/sim-runs', headers: { set: function (k: string, v: string) { (this as Record<string, string>)[k] = v; } } });
    expect(cfg.headers.Authorization).toBe('Bearer tok-xyz');
    localStorage.removeItem(ADMIN_TOKEN_KEY);
  });

  it('does not attach Bearer header for public /api/* routes', async () => {
    localStorage.setItem(ADMIN_TOKEN_KEY, 'tok-xyz');
    const api = createApi('http://localhost:0');
    const cfg = await (api.interceptors.request as unknown as { handlers: Array<{ fulfilled: Function }> })
      .handlers[0]
      .fulfilled({ url: '/api/public/regions', headers: { set: function (k: string, v: string) { (this as Record<string, string>)[k] = v; } } });
    expect(cfg.headers.Authorization).toBeUndefined();
    localStorage.removeItem(ADMIN_TOKEN_KEY);
  });
});
