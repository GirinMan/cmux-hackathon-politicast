import { jsx as _jsx, jsxs as _jsxs, Fragment as _Fragment } from "react/jsx-runtime";
import { useState } from 'react';
import { useAnonUser } from '../contexts/AnonUserContext';
const REPORT_REASONS = [
    { value: 'spam', label: '스팸/광고' },
    { value: 'abuse', label: '욕설/혐오 표현' },
    { value: 'misinformation', label: '허위 정보' },
    { value: 'doxxing', label: '신상 공개' },
    { value: 'other', label: '기타' },
];
export default function ReportButton({ onReport, label = '신고', disabled }) {
    const { ensureConsented } = useAnonUser();
    const [open, setOpen] = useState(false);
    const [reason, setReason] = useState('spam');
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState(null);
    const [done, setDone] = useState(false);
    async function trigger() {
        await ensureConsented(() => setOpen(true));
    }
    async function submit() {
        setBusy(true);
        setError(null);
        try {
            await onReport(reason);
            setDone(true);
            setTimeout(() => {
                setDone(false);
                setOpen(false);
            }, 1200);
        }
        catch (err) {
            setError(err.message ?? '신고 처리에 실패했습니다.');
        }
        finally {
            setBusy(false);
        }
    }
    return (_jsxs(_Fragment, { children: [_jsx("button", { type: "button", onClick: trigger, disabled: disabled, style: { background: 'transparent', color: 'var(--color-muted)', padding: '0.25rem 0.5rem', fontSize: '0.85rem' }, "aria-label": label, children: label }), open ? (_jsx("div", { role: "dialog", "aria-modal": "true", style: {
                    position: 'fixed',
                    inset: 0,
                    background: 'rgba(0,0,0,0.6)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    zIndex: 80,
                }, onClick: () => !busy && setOpen(false), children: _jsxs("div", { className: "card", style: { minWidth: 320 }, onClick: (e) => e.stopPropagation(), children: [_jsx("h4", { style: { marginTop: 0 }, children: "\uC2E0\uACE0 \uC0AC\uC720" }), _jsx("select", { value: reason, onChange: (e) => setReason(e.target.value), disabled: busy || done, style: { width: '100%', padding: '0.4rem', background: '#0b0e14', color: 'inherit', border: '1px solid #1f2330' }, children: REPORT_REASONS.map((r) => (_jsx("option", { value: r.value, children: r.label }, r.value))) }), error ? _jsx("p", { style: { color: 'var(--color-fail)' }, children: error }) : null, done ? _jsx("p", { style: { color: 'var(--color-pass)' }, children: "\uC2E0\uACE0\uAC00 \uC811\uC218\uB418\uC5C8\uC2B5\uB2C8\uB2E4." }) : null, _jsxs("div", { style: { display: 'flex', gap: '0.5rem', justifyContent: 'flex-end', marginTop: '1rem' }, children: [_jsx("button", { onClick: () => setOpen(false), disabled: busy, style: { background: '#1f2330' }, children: "\uCDE8\uC18C" }), _jsx("button", { onClick: submit, disabled: busy || done, children: busy ? '전송 중…' : '신고하기' })] })] }) })) : null] }));
}
