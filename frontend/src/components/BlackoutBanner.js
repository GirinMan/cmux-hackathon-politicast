import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
export default function BlackoutBanner({ active, endDate, reason }) {
    if (!active)
        return null;
    return (_jsxs("div", { role: "alert", className: "card", style: {
            background: '#3a3500',
            border: '1px solid var(--color-warn)',
            color: '#fff7d6',
            padding: '0.75rem 1rem',
            marginBottom: '1rem',
        }, children: [_jsx("strong", { children: "\u26A0\uFE0F \uBE14\uB799\uC544\uC6C3 \uAE30\uAC04" }), ' ', _jsxs("span", { children: ["\uACF5\uC9C1\uC120\uAC70\uBC95 \uC81C108\uC870\uC5D0 \uB530\uB77C ", _jsx("strong", { children: endDate ?? '선거 종료 시' }), "\uAE4C\uC9C0 \uC77C\uBD80 \uC608\uCE21 \uD654\uBA74\uACFC \uC0C8 \uB313\uAE00 \uC791\uC131\uC774 \uC81C\uD55C\uB429\uB2C8\uB2E4."] }), reason ? _jsx("p", { style: { margin: '0.25rem 0 0', fontSize: '0.85rem' }, children: reason }) : null] }));
}
export function BlackoutPlaceholder({ message }) {
    return (_jsx("div", { role: "img", "aria-label": "blackout placeholder", className: "card", style: {
            height: 360,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            textAlign: 'center',
            background: 'repeating-linear-gradient(45deg, #1a1a1a, #1a1a1a 8px, #11151f 8px, #11151f 16px)',
            color: 'var(--color-warn)',
            border: '1px dashed var(--color-warn)',
        }, children: _jsxs("div", { children: [_jsx("p", { style: { margin: 0, fontSize: '1.2rem' }, children: "\uD83D\uDD12 \uBE14\uB799\uC544\uC6C3" }), _jsx("p", { style: { margin: '0.5rem 0 0', fontSize: '0.9rem' }, children: message ?? '공직선거법 §108에 따라 비공개 처리되었습니다.' })] }) }));
}
