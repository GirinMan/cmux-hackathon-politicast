import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
export default function RegionSelector({ regions, value, onChange, disabled }) {
    return (_jsx("div", { role: "radiogroup", "aria-label": "Region selector", className: "region-selector", children: regions.map((r) => {
            const active = value === r.region_id;
            return (_jsxs("button", { type: "button", role: "radio", "aria-checked": active, disabled: disabled, onClick: () => onChange(r.region_id, r.election_id), className: `card region-card${active ? ' active' : ''}`, style: {
                    cursor: 'pointer',
                    border: active ? '2px solid var(--color-accent)' : '1px solid #1f2330',
                    minWidth: 220,
                    textAlign: 'left',
                    background: active ? '#1a2030' : '#11151f',
                    color: 'inherit',
                }, children: [_jsx("div", { style: { fontWeight: 600 }, children: r.name }), _jsxs("div", { className: "muted", style: { fontSize: '0.85rem' }, children: [r.region_id, " \u00B7 ", r.position_type] }), _jsxs("div", { className: "muted", style: { fontSize: '0.85rem' }, children: ["election: ", r.election_date] }), r.in_blackout ? _jsx("span", { className: "badge badge-warn", children: "blackout" }) : null] }, r.region_id));
        }) }));
}
