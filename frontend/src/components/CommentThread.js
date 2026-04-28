import { jsxs as _jsxs, jsx as _jsx, Fragment as _Fragment } from "react/jsx-runtime";
import { useMemo, useState } from 'react';
import { useAnonUser } from '../contexts/AnonUserContext';
import { useComments, useCreateComment, useDeleteComment, useReportComment, useUpdateComment, } from '../lib/communityQueries';
import ReportButton from './ReportButton';
function buildTree(items) {
    const byId = new Map();
    items.forEach((c) => byId.set(c.comment_id, { comment: c, children: [] }));
    const roots = [];
    byId.forEach((node) => {
        const pid = node.comment.parent_id;
        if (pid && byId.has(pid)) {
            byId.get(pid).children.push(node);
        }
        else {
            roots.push(node);
        }
    });
    // 시간순 정렬
    const sortFn = (a, b) => a.comment.created_at.localeCompare(b.comment.created_at);
    function recurse(arr) {
        arr.sort(sortFn);
        arr.forEach((n) => recurse(n.children));
    }
    recurse(roots);
    return roots;
}
export default function CommentThread({ scope_type, scope_id, blackout }) {
    const { userId, hasConsented, ensureConsented } = useAnonUser();
    const list = useComments(scope_type, scope_id);
    const create = useCreateComment(scope_type, scope_id);
    const update = useUpdateComment(scope_type, scope_id);
    const remove = useDeleteComment(scope_type, scope_id);
    const report = useReportComment();
    const [body, setBody] = useState('');
    const [replyTo, setReplyTo] = useState(null);
    const [editing, setEditing] = useState(null);
    const [editBody, setEditBody] = useState('');
    const tree = useMemo(() => (list.isSuccess ? buildTree(list.data) : []), [list.isSuccess, list.data]);
    async function submit(e) {
        e.preventDefault();
        if (!body.trim())
            return;
        await ensureConsented(async () => {
            await create.mutateAsync({ body: body.trim(), parent_id: replyTo });
            setBody('');
            setReplyTo(null);
        });
    }
    async function saveEdit(comment_id) {
        if (!editBody.trim())
            return;
        await update.mutateAsync({ comment_id, body: editBody.trim() });
        setEditing(null);
        setEditBody('');
    }
    return (_jsxs("section", { "aria-label": "comments", style: { marginTop: '2rem' }, children: [_jsxs("h3", { children: ["\uD83D\uDCAC \uB313\uAE00 (", list.isSuccess ? list.data.length : '…', ")"] }), blackout ? (_jsx("p", { className: "muted", style: { fontStyle: 'italic' }, children: "\uBE14\uB799\uC544\uC6C3 \uAE30\uAC04 \uB3D9\uC548 \uC0C8 \uB313\uAE00 \uC791\uC131\uC740 \uC81C\uD55C\uB429\uB2C8\uB2E4. \uAE30\uC874 \uB300\uD654\uB294 \uACC4\uC18D \uC77D\uC73C\uC2E4 \uC218 \uC788\uC2B5\uB2C8\uB2E4." })) : (_jsxs("form", { onSubmit: submit, style: { marginBottom: '1rem' }, children: [_jsx("textarea", { value: body, onChange: (e) => setBody(e.target.value), rows: 3, placeholder: hasConsented ? '의견을 남겨 주세요' : '닉네임을 받고 첫 의견을 남겨보세요', disabled: create.isPending, style: { width: '100%', background: '#0b0e14', color: 'inherit', padding: '0.5rem', border: '1px solid #1f2330', borderRadius: 4 } }), _jsxs("div", { style: { display: 'flex', gap: '0.5rem', alignItems: 'center', marginTop: '0.5rem' }, children: [replyTo ? (_jsxs("span", { className: "muted", style: { fontSize: '0.85rem' }, children: ["\u21B3 \uB2F5\uAE00: ", _jsx("code", { children: replyTo.slice(0, 8) }), ' ', _jsx("button", { type: "button", onClick: () => setReplyTo(null), style: { background: 'transparent', color: 'var(--color-muted)' }, children: "\u2715" })] })) : null, _jsx("button", { type: "submit", disabled: create.isPending || !body.trim(), style: { marginLeft: 'auto' }, children: create.isPending ? '등록 중…' : '등록' })] })] })), list.isLoading ? _jsx("p", { children: "\uB313\uAE00 \uB85C\uB529 \uC911\u2026" }) : null, list.isError ? (_jsx("p", { style: { color: 'var(--color-fail)' }, children: list.error.message })) : null, _jsx("ul", { style: { listStyle: 'none', padding: 0 }, children: tree.map((n) => (_jsx(CommentItem, { node: n, depth: 0, currentUserId: userId, onReply: (id) => setReplyTo(id), onStartEdit: (c) => {
                        setEditing(c.comment_id);
                        setEditBody(c.body);
                    }, editing: editing, editBody: editBody, setEditBody: setEditBody, onSaveEdit: saveEdit, onCancelEdit: () => {
                        setEditing(null);
                        setEditBody('');
                    }, onDelete: (id) => remove.mutate(id), onReport: (id, reason) => report.mutateAsync({ comment_id: id, reason }), blackout: blackout }, n.comment.comment_id))) })] }));
}
function CommentItem({ node, depth, currentUserId, onReply, onStartEdit, editing, editBody, setEditBody, onSaveEdit, onCancelEdit, onDelete, onReport, blackout, }) {
    const c = node.comment;
    const isOwner = currentUserId !== null && currentUserId === c.user_id;
    const hidden = c.is_hidden || c.is_deleted;
    return (_jsxs("li", { className: "card", style: {
            marginLeft: depth * 1.25 + 'rem',
            marginBottom: '0.5rem',
            opacity: hidden ? 0.5 : 1,
        }, children: [_jsxs("header", { style: { display: 'flex', gap: '0.5rem', alignItems: 'center', fontSize: '0.85rem' }, children: [_jsx("strong", { children: c.display_name }), _jsx("span", { className: "muted", children: new Date(c.created_at).toLocaleString('ko-KR') }), c.report_count > 0 ? (_jsxs("span", { className: "badge badge-warn", children: ["\uC2E0\uACE0 ", c.report_count] })) : null] }), hidden ? (_jsx("p", { className: "muted", style: { fontStyle: 'italic' }, children: c.is_deleted ? '삭제된 댓글입니다.' : '신고로 가려진 댓글입니다.' })) : editing === c.comment_id ? (_jsxs(_Fragment, { children: [_jsx("textarea", { value: editBody, onChange: (e) => setEditBody(e.target.value), rows: 3, style: { width: '100%', background: '#0b0e14', color: 'inherit', padding: '0.4rem', border: '1px solid #1f2330' } }), _jsxs("div", { style: { display: 'flex', gap: '0.5rem', justifyContent: 'flex-end' }, children: [_jsx("button", { onClick: onCancelEdit, style: { background: '#1f2330' }, children: "\uCDE8\uC18C" }), _jsx("button", { onClick: () => { void onSaveEdit(c.comment_id); }, children: "\uC800\uC7A5" })] })] })) : (_jsx("p", { style: { whiteSpace: 'pre-wrap', margin: '0.5rem 0' }, children: c.body })), !hidden && editing !== c.comment_id ? (_jsxs("div", { style: { display: 'flex', gap: '0.5rem', fontSize: '0.85rem' }, children: [!blackout ? (_jsx("button", { onClick: () => onReply(c.comment_id), style: { background: 'transparent', color: 'var(--color-muted)' }, children: "\uB2F5\uAE00" })) : null, isOwner ? (_jsxs(_Fragment, { children: [_jsx("button", { onClick: () => onStartEdit(c), style: { background: 'transparent', color: 'var(--color-muted)' }, children: "\uC218\uC815" }), _jsx("button", { onClick: () => onDelete(c.comment_id), style: { background: 'transparent', color: 'var(--color-fail)' }, children: "\uC0AD\uC81C" })] })) : (_jsx(ReportButton, { onReport: (reason) => onReport(c.comment_id, reason) }))] })) : null, node.children.length > 0 ? (_jsx("ul", { style: { listStyle: 'none', padding: 0, marginTop: '0.5rem' }, children: node.children.map((child) => (_jsx(CommentItem, { node: child, depth: depth + 1, currentUserId: currentUserId, onReply: onReply, onStartEdit: onStartEdit, editing: editing, editBody: editBody, setEditBody: setEditBody, onSaveEdit: onSaveEdit, onCancelEdit: onCancelEdit, onDelete: onDelete, onReport: onReport, blackout: blackout }, child.comment.comment_id))) })) : null] }));
}
