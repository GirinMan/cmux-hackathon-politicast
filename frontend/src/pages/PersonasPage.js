import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useState } from 'react';
import BlackoutBanner from '../components/BlackoutBanner';
import CommentThread from '../components/CommentThread';
import PersonaCard from '../components/PersonaCard';
import RequireRegion from '../components/RequireRegion';
import { usePersonas } from '../lib/queries';
import { useBlackout } from '../lib/useBlackout';
export default function PersonasPage() {
    return (_jsx(RequireRegion, { children: (region) => _jsx(PersonasInner, { region: region }) }));
}
function PersonasInner({ region }) {
    const [seed, setSeed] = useState(0);
    const personas = usePersonas(region, 20, seed);
    const blackout = useBlackout(region);
    return (_jsxs("section", { children: [_jsxs("header", { style: { display: 'flex', alignItems: 'center', gap: '1rem', marginBottom: '1rem' }, children: [_jsxs("h2", { style: { margin: 0 }, children: ["Personas \u2014 ", region] }), _jsx("button", { onClick: () => setSeed(Math.floor(Math.random() * 1_000_000)), children: "\uC0C8\uB85C\uACE0\uCE68 (seed)" }), _jsxs("span", { className: "muted", children: ["seed: ", seed] })] }), personas.isLoading ? _jsx("p", { children: "Loading personas\u2026" }) : null, personas.isError ? (_jsxs("p", { style: { color: 'var(--color-fail)' }, children: ["Personas \uB85C\uB4DC \uC2E4\uD328: ", personas.error.message] })) : null, personas.isSuccess ? (_jsx("div", { style: {
                    display: 'grid',
                    gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
                    gap: '1rem',
                }, children: personas.data.map((p) => (_jsx(PersonaCard, { persona: p }, p.persona_id))) })) : null, _jsx(BlackoutBanner, { active: blackout.active, endDate: blackout.endDate }), _jsx(CommentThread, { scope_type: "region", scope_id: region, blackout: blackout.active })] }));
}
