import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useState } from 'react';
import { useAnonUser } from '../contexts/AnonUserContext';
/**
 * 작성 액션(댓글/토픽/신고) 시 hasConsented=false 면 자동 노출되는 modal.
 * 동의 → POST /api/v1/users/anonymous → backend 가 HttpOnly cookie 발급.
 */
export default function CookieConsentBanner() {
    const { bannerOpen, closeBanner, consent, hasConsented } = useAnonUser();
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState(null);
    if (!bannerOpen || hasConsented)
        return null;
    async function onAccept() {
        setBusy(true);
        setError(null);
        try {
            await consent();
            closeBanner();
        }
        catch (err) {
            setError(err.message ?? '동의 처리에 실패했습니다.');
        }
        finally {
            setBusy(false);
        }
    }
    return (_jsx("div", { role: "dialog", "aria-modal": "true", "aria-labelledby": "consent-title", style: {
            position: 'fixed',
            inset: 0,
            background: 'rgba(0,0,0,0.6)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 100,
        }, onClick: closeBanner, children: _jsxs("div", { className: "card", style: { maxWidth: 480, padding: '1.5rem' }, onClick: (e) => e.stopPropagation(), children: [_jsx("h3", { id: "consent-title", style: { marginTop: 0 }, children: "\uC775\uBA85 \uB2C9\uB124\uC784\uC73C\uB85C \uD568\uAED8 \uC774\uC57C\uAE30\uD558\uAE30" }), _jsxs("p", { style: { lineHeight: 1.6 }, children: ["\uB313\uAE00\u00B7\uAC8C\uC2DC\uD310\uC744 \uC774\uC6A9\uD558\uC2DC\uB824\uBA74 ", _jsx("strong", { children: "\uC784\uC758 \uB2C9\uB124\uC784" }), " \uC774 \uC790\uB3D9\uC73C\uB85C \uB9CC\uB4E4\uC5B4\uC9D1\uB2C8\uB2E4. \uB2C9\uB124\uC784\uC740 \uC5B8\uC81C\uB4E0 \uBC14\uAFB8\uC2E4 \uC218 \uC788\uACE0, \uB530\uB85C \uD68C\uC6D0\uAC00\uC785\uC740 \uD544\uC694\uD558\uC9C0 \uC54A\uC2B5\uB2C8\uB2E4."] }), _jsxs("ul", { style: { fontSize: '0.9rem', lineHeight: 1.6 }, children: [_jsx("li", { children: "\uC800\uC7A5\uB418\uB294 \uD56D\uBAA9: \uC775\uBA85 \uC2DD\uBCC4 \uCFE0\uD0A4 (HttpOnly), \uD45C\uC2DC \uB2C9\uB124\uC784, \uC791\uC131\uD55C \uAE00." }), _jsx("li", { children: "\uC800\uC7A5\uB418\uC9C0 \uC54A\uB294 \uD56D\uBAA9: \uC774\uBA54\uC77C, \uC804\uD654\uBC88\uD638, IP \uC601\uAD6C\uAE30\uB85D." }), _jsx("li", { children: "\uC5B8\uC81C\uB4E0 \uD5E4\uB354\uC758 \"\uB85C\uADF8\uC544\uC6C3\" \uC73C\uB85C \uCFE0\uD0A4\uB97C \uD3D0\uAE30\uD560 \uC218 \uC788\uC2B5\uB2C8\uB2E4." })] }), error ? (_jsx("p", { style: { color: 'var(--color-fail)', marginTop: '0.5rem' }, children: error })) : null, _jsxs("div", { style: { display: 'flex', gap: '0.75rem', justifyContent: 'flex-end', marginTop: '1rem' }, children: [_jsx("button", { onClick: closeBanner, disabled: busy, style: { background: '#1f2330' }, children: "\uB098\uC911\uC5D0" }), _jsx("button", { onClick: onAccept, disabled: busy, children: busy ? '동의 중…' : '동의하고 닉네임 받기' })] })] }) }));
}
