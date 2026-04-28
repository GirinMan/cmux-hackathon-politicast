import { jsx as _jsx, jsxs as _jsxs, Fragment as _Fragment } from "react/jsx-runtime";
import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useAnonUser } from '../contexts/AnonUserContext';
import { useRegionState } from '../lib/regionState';
import { useBoardTopics, useCreateBoardTopic } from '../lib/communityQueries';
export default function BoardPage() {
    const { region } = useRegionState();
    const { ensureConsented } = useAnonUser();
    const [sort, setSort] = useState('recent');
    const [page, setPage] = useState(1);
    const [composing, setComposing] = useState(false);
    const [title, setTitle] = useState('');
    const [body, setBody] = useState('');
    const [filterByRegion, setFilterByRegion] = useState(!!region);
    const list = useBoardTopics({
        region_id: filterByRegion && region ? region : undefined,
        sort,
        page,
        page_size: 20,
    });
    const create = useCreateBoardTopic();
    async function compose() {
        await ensureConsented(() => setComposing(true));
    }
    async function submit(e) {
        e.preventDefault();
        if (!title.trim() || !body.trim())
            return;
        await create.mutateAsync({
            title: title.trim(),
            body: body.trim(),
            region_id: filterByRegion && region ? region : null,
        });
        setTitle('');
        setBody('');
        setComposing(false);
    }
    return (_jsxs("section", { children: [_jsxs("header", { style: { display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1rem' }, children: [_jsx("h2", { style: { margin: 0 }, children: "Board" }), _jsxs("select", { value: sort, onChange: (e) => { setSort(e.target.value); setPage(1); }, style: { padding: '0.3rem 0.5rem', background: '#11151f', color: 'inherit', border: '1px solid #1f2330' }, children: [_jsx("option", { value: "recent", children: "\uCD5C\uC2E0" }), _jsx("option", { value: "popular", children: "\uC778\uAE30" })] }), region ? (_jsxs("label", { style: { fontSize: '0.85rem' }, children: [_jsx("input", { type: "checkbox", checked: filterByRegion, onChange: (e) => { setFilterByRegion(e.target.checked); setPage(1); } }), ' ', region, " \uB9CC \uBCF4\uAE30"] })) : null, _jsx("button", { onClick: compose, style: { marginLeft: 'auto' }, children: "\uC0C8 \uD1A0\uD53D \uC791\uC131" })] }), composing ? (_jsxs("form", { onSubmit: submit, className: "card", style: { marginBottom: '1rem' }, children: [_jsx("input", { placeholder: "\uC81C\uBAA9", value: title, onChange: (e) => setTitle(e.target.value), maxLength: 120, style: { width: '100%', padding: '0.5rem', background: '#0b0e14', color: 'inherit', border: '1px solid #1f2330', marginBottom: '0.5rem' } }), _jsx("textarea", { placeholder: "\uBCF8\uBB38", value: body, onChange: (e) => setBody(e.target.value), rows: 5, style: { width: '100%', padding: '0.5rem', background: '#0b0e14', color: 'inherit', border: '1px solid #1f2330' } }), create.isError ? (_jsx("p", { style: { color: 'var(--color-fail)' }, children: create.error.message })) : null, _jsxs("div", { style: { display: 'flex', gap: '0.5rem', justifyContent: 'flex-end', marginTop: '0.5rem' }, children: [_jsx("button", { type: "button", onClick: () => setComposing(false), style: { background: '#1f2330' }, children: "\uCDE8\uC18C" }), _jsx("button", { type: "submit", disabled: create.isPending || !title.trim() || !body.trim(), children: create.isPending ? '등록 중…' : '등록' })] })] })) : null, list.isLoading ? _jsx("p", { children: "\uB85C\uB529 \uC911\u2026" }) : null, list.isError ? _jsx("p", { style: { color: 'var(--color-fail)' }, children: list.error.message }) : null, list.isSuccess ? (_jsxs(_Fragment, { children: [_jsx("ul", { style: { listStyle: 'none', padding: 0 }, children: list.data.items.map((t) => (_jsxs("li", { className: "card", style: { marginBottom: '0.5rem', opacity: t.is_hidden ? 0.5 : 1 }, children: [_jsx(Link, { to: `/board/topics/${t.topic_id}`, style: { display: 'block' }, children: _jsx("strong", { children: t.title }) }), _jsxs("div", { className: "muted", style: { fontSize: '0.85rem', marginTop: '0.25rem' }, children: [t.display_name, " \u00B7 ", new Date(t.created_at).toLocaleString('ko-KR'), t.region_id ? _jsxs(_Fragment, { children: [" \u00B7 ", _jsx("code", { children: t.region_id })] }) : null, "\u00B7 \uB313\uAE00 ", t.comment_count, t.is_hidden ? _jsxs(_Fragment, { children: [" \u00B7 ", _jsx("span", { className: "badge badge-warn", children: "\uC228\uAE40" })] }) : null] })] }, t.topic_id))) }), _jsx(Pagination, { page: page, total: list.data.total, pageSize: 20, onChange: setPage })] })) : null] }));
}
function Pagination({ page, total, pageSize, onChange }) {
    const last = Math.max(1, Math.ceil(total / pageSize));
    return (_jsxs("div", { style: { display: 'flex', gap: '0.5rem', justifyContent: 'center', marginTop: '1rem' }, children: [_jsx("button", { onClick: () => onChange(Math.max(1, page - 1)), disabled: page <= 1, children: "\uC774\uC804" }), _jsxs("span", { className: "muted", children: [page, " / ", last] }), _jsx("button", { onClick: () => onChange(Math.min(last, page + 1)), disabled: page >= last, children: "\uB2E4\uC74C" })] }));
}
