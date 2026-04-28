import { Fragment as _Fragment, jsxs as _jsxs, jsx as _jsx } from "react/jsx-runtime";
import { useState } from 'react';
import { useAnonUser } from '../contexts/AnonUserContext';
/**
 * 헤더 우상단에 노출. 클릭 시 dialog 로 닉네임 변경.
 * 동의 전이라면 banner 를 먼저 띄운다.
 */
export default function NicknameEditor() {
    const { displayName, hasConsented, ensureConsented, updateNickname, openBanner, logout } = useAnonUser();
    const [open, setOpen] = useState(false);
    const [draft, setDraft] = useState(displayName ?? '');
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState(null);
    function trigger() {
        if (!hasConsented) {
            openBanner();
            return;
        }
        setDraft(displayName ?? '');
        setOpen(true);
    }
    async function onSubmit(e) {
        e.preventDefault();
        if (!draft.trim()) {
            setError('닉네임을 입력해 주세요.');
            return;
        }
        setBusy(true);
        setError(null);
        try {
            await updateNickname(draft.trim());
            setOpen(false);
        }
        catch (err) {
            setError(err.message ?? '닉네임 변경에 실패했습니다.');
        }
        finally {
            setBusy(false);
        }
    }
    return (_jsxs(_Fragment, { children: [_jsx("button", { type: "button", onClick: trigger, title: "\uB2C9\uB124\uC784 \uBCC0\uACBD", style: { background: 'transparent', color: 'inherit', padding: '0.25rem 0.5rem' }, children: hasConsented ? (_jsxs(_Fragment, { children: ["\uD83D\uDC64 ", displayName ?? '닉네임 받기'] })) : (_jsx(_Fragment, { children: "\uD83D\uDC64 \uC775\uBA85\uC73C\uB85C \uC2DC\uC791" })) }), open ? (_jsx("div", { role: "dialog", "aria-modal": "true", style: { position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.6)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 80 }, onClick: () => !busy && setOpen(false), children: _jsxs("form", { className: "card", style: { minWidth: 320 }, onClick: (e) => e.stopPropagation(), onSubmit: (e) => { void onSubmit(e); }, children: [_jsx("h4", { style: { marginTop: 0 }, children: "\uB2C9\uB124\uC784 \uBCC0\uACBD" }), _jsx("input", { value: draft, onChange: (e) => setDraft(e.target.value), maxLength: 24, autoFocus: true, style: { width: '100%', padding: '0.5rem', background: '#0b0e14', color: 'inherit', border: '1px solid #1f2330' } }), error ? _jsx("p", { style: { color: 'var(--color-fail)' }, children: error }) : null, _jsxs("div", { style: { display: 'flex', gap: '0.5rem', justifyContent: 'space-between', marginTop: '1rem' }, children: [_jsx("button", { type: "button", onClick: () => { void logout(); setOpen(false); }, style: { background: 'transparent', color: 'var(--color-muted)' }, children: "\uB85C\uADF8\uC544\uC6C3 (\uCFE0\uD0A4 \uC0AD\uC81C)" }), _jsxs("div", { style: { display: 'flex', gap: '0.5rem' }, children: [_jsx("button", { type: "button", onClick: () => setOpen(false), disabled: busy, style: { background: '#1f2330' }, children: "\uCDE8\uC18C" }), _jsx("button", { type: "submit", disabled: busy, children: busy ? '저장 중…' : '저장' })] })] })] }) })) : null] }));
}
