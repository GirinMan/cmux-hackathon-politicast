import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from 'react';
import type { ReactNode } from 'react';

import { anonApi } from '../lib/anonApi';
import {
  AnonUserCache,
  clearAllAnonState,
  readConsent,
  readUserCache,
  writeConsent,
  writeUserCache,
} from '../lib/cookies';

interface AnonUserState {
  userId: string | null;
  displayName: string | null;
  hasConsented: boolean;

  /** Show consent banner / 즉시 consent + register. */
  bannerOpen: boolean;
  openBanner: () => void;
  closeBanner: () => void;

  /** consent → POST /api/v1/users/anonymous; cookie set by backend */
  consent: () => Promise<void>;
  /** consent + run a deferred write action after registration */
  ensureConsented: (then?: () => void | Promise<void>) => Promise<void>;

  updateNickname: (nickname: string) => Promise<void>;
  logout: () => Promise<void>;
  refresh: () => Promise<void>;
}

const Ctx = createContext<AnonUserState | null>(null);

export function AnonUserProvider({ children }: { children: ReactNode }) {
  const cached = readUserCache();
  const [user, setUser] = useState<AnonUserCache | null>(cached);
  const [hasConsented, setHasConsented] = useState<boolean>(readConsent());
  const [bannerOpen, setBannerOpen] = useState<boolean>(false);
  const [pendingAction, setPendingAction] = useState<(() => void | Promise<void>) | null>(null);

  // 초기 mount: consent 가 있고 cache 가 비어있으면 me() 시도.
  useEffect(() => {
    let cancelled = false;
    if (hasConsented && !user) {
      anonApi
        .me()
        .then((u) => {
          if (cancelled) return;
          const cache: AnonUserCache = {
            user_id: u.user_id,
            display_name: u.display_name,
            fetched_at: new Date().toISOString(),
          };
          writeUserCache(cache);
          setUser(cache);
        })
        .catch(() => {
          // me() 401/404 → consent 정리 (backend 가 cookie 만료)
          if (cancelled) return;
          writeConsent(false);
          setHasConsented(false);
        });
    }
    return () => {
      cancelled = true;
    };
  }, [hasConsented, user]);

  const consent = useCallback(async () => {
    const u = await anonApi.register();
    const cache: AnonUserCache = {
      user_id: u.user_id,
      display_name: u.display_name,
      fetched_at: new Date().toISOString(),
    };
    writeConsent(true);
    writeUserCache(cache);
    setHasConsented(true);
    setUser(cache);
  }, []);

  const ensureConsented = useCallback(
    async (then?: () => void | Promise<void>) => {
      if (hasConsented && user) {
        if (then) await then();
        return;
      }
      // Banner 띄우고 consent 직후 then 실행하도록 보류.
      setPendingAction(() => then ?? null);
      setBannerOpen(true);
    },
    [hasConsented, user],
  );

  // Banner 측에서 consent() 성공 후 pendingAction 자동 실행.
  useEffect(() => {
    if (hasConsented && user && pendingAction) {
      const action = pendingAction;
      setPendingAction(null);
      Promise.resolve(action()).catch(() => {
        /* 콜러가 처리 */
      });
    }
  }, [hasConsented, user, pendingAction]);

  const updateNickname = useCallback(async (nickname: string) => {
    const u = await anonApi.updateNickname(nickname);
    const cache: AnonUserCache = {
      user_id: u.user_id,
      display_name: u.display_name,
      fetched_at: new Date().toISOString(),
    };
    writeUserCache(cache);
    setUser(cache);
  }, []);

  const logout = useCallback(async () => {
    try {
      await anonApi.logout();
    } catch {
      /* backend 없어도 클라이언트 상태는 정리 */
    }
    clearAllAnonState();
    setUser(null);
    setHasConsented(false);
  }, []);

  const refresh = useCallback(async () => {
    const u = await anonApi.me();
    const cache: AnonUserCache = {
      user_id: u.user_id,
      display_name: u.display_name,
      fetched_at: new Date().toISOString(),
    };
    writeUserCache(cache);
    setUser(cache);
  }, []);

  const value = useMemo<AnonUserState>(
    () => ({
      userId: user?.user_id ?? null,
      displayName: user?.display_name ?? null,
      hasConsented,
      bannerOpen,
      openBanner: () => setBannerOpen(true),
      closeBanner: () => setBannerOpen(false),
      consent,
      ensureConsented,
      updateNickname,
      logout,
      refresh,
    }),
    [user, hasConsented, bannerOpen, consent, ensureConsented, updateNickname, logout, refresh],
  );

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useAnonUser(): AnonUserState {
  const v = useContext(Ctx);
  if (!v) throw new Error('useAnonUser must be used inside <AnonUserProvider>');
  return v;
}
