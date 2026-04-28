import { jsx as _jsx, jsxs as _jsxs, Fragment as _Fragment } from "react/jsx-runtime";
import { Link, useParams } from 'react-router-dom';
import CommentThread from '../components/CommentThread';
import ReportButton from '../components/ReportButton';
import { useBoardTopic, useReportTopic } from '../lib/communityQueries';
export default function BoardTopicDetail() {
    const { id } = useParams();
    const topic = useBoardTopic(id ?? null);
    const report = useReportTopic();
    return (_jsxs("section", { children: [_jsx("p", { children: _jsx(Link, { to: "/board", className: "muted", children: "\u2190 \uAC8C\uC2DC\uD310" }) }), topic.isLoading ? _jsx("p", { children: "\uB85C\uB529 \uC911\u2026" }) : null, topic.isError ? _jsx("p", { style: { color: 'var(--color-fail)' }, children: topic.error.message }) : null, topic.isSuccess ? (_jsxs("article", { className: "card", children: [_jsxs("header", { style: { display: 'flex', alignItems: 'center', gap: '0.5rem' }, children: [_jsx("h2", { style: { margin: 0, flex: 1 }, children: topic.data.title }), _jsx(ReportButton, { onReport: (reason) => report.mutateAsync({ topic_id: topic.data.topic_id, reason }), label: "\uC774 \uD1A0\uD53D \uC2E0\uACE0" })] }), _jsxs("div", { className: "muted", style: { fontSize: '0.85rem', marginTop: '0.5rem' }, children: [topic.data.display_name, " \u00B7 ", new Date(topic.data.created_at).toLocaleString('ko-KR'), topic.data.region_id ? _jsxs(_Fragment, { children: [" \u00B7 ", _jsx("code", { children: topic.data.region_id })] }) : null, topic.data.is_hidden ? _jsxs(_Fragment, { children: [" \u00B7 ", _jsx("span", { className: "badge badge-warn", children: "\uC228\uAE40" })] }) : null] }), _jsx("p", { style: { whiteSpace: 'pre-wrap', marginTop: '1rem', lineHeight: 1.6 }, children: topic.data.body })] })) : null, topic.isSuccess ? (_jsx(CommentThread, { scope_type: "board_topic", scope_id: topic.data.topic_id })) : null] }));
}
