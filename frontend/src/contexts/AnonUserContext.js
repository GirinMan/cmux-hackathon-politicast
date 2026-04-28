import { jsx as _jsx } from "react/jsx-runtime";
import { createContext, useCallback, useContext, useEffect, useMemo, useState, } from 'react';
import { anonApi } from '../lib/anonApi';
import { clearAllAnonState, readConsent, readUserCache, writeConsent, writeUserCache, } from '../lib/cookies';
const Ctx = createContext(null);
export function AnonUserProvider({ children }) {
    const cached = readUserCache();
    const [user, setUser] = useState(cached);
    const [hasConsented, setHasConsented] = useState(readConsent());
    const [bannerOpen, setBannerOpen] = useState(false);
    const [pendingAction, setPendingAction] = useState(null);
    // 초기 mount: consent 가 있고 cache 가 비어있으면 me() 시도.
    useEffect(() => {
        let cancelled = false;
        if (hasConsented && !user) {
            anonApi
                .me()
                .then((u) => {
                if (cancelled)
                    return;
                const cache = {
                    user_id: u.user_id,
                    display_name: u.display_name,
                    fetched_at: new Date().toISOString(),
                };
                writeUserCache(cache);
                setUser(cache);
            })
                .catch(() => {
                // me() 401/404 → consent 정리 (backend 가 cookie 만료)
                if (cancelled)
                    return;
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
        const cache = {
            user_id: u.user_id,
            display_name: u.display_name,
            fetched_at: new Date().toISOString(),
        };
        writeConsent(true);
        writeUserCache(cache);
        setHasConsented(true);
        setUser(cache);
    }, []);
    const ensureConsented = useCallback(async (then) => {
        if (hasConsented && user) {
            if (then)
                await then();
            return;
        }
        // Banner 띄우고 consent 직후 then 실행하도록 보류.
        setPendingAction(() => then ?? null);
        setBannerOpen(true);
    }, [hasConsented, user]);
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
    const updateNickname = useCallback(async (nickname) => {
        const u = await anonApi.updateNickname(nickname);
        const cache = {
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
        }
        catch {
            /* backend 없어도 클라이언트 상태는 정리 */
        }
        clearAllAnonState();
        setUser(null);
        setHasConsented(false);
    }, []);
    const refresh = useCallback(async () => {
        const u = await anonApi.me();
        const cache = {
            user_id: u.user_id,
            display_name: u.display_name,
            fetched_at: new Date().toISOString(),
        };
        writeUserCache(cache);
        setUser(cache);
    }, []);
    const value = useMemo(() => ({
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
    }), [user, hasConsented, bannerOpen, consent, ensureConsented, updateNickname, logout, refresh]);
    return _jsx(Ctx.Provider, { value: value, children: children });
}
export function useAnonUser() {
    const v = useContext(Ctx);
    if (!v)
        throw new Error('useAnonUser must be used inside <AnonUserProvider>');
    return v;
}
