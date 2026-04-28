import { Link, useParams } from 'react-router-dom';

import CommentThread from '../components/CommentThread';
import ReportButton from '../components/ReportButton';
import { useBoardTopic, useReportTopic } from '../lib/communityQueries';

export default function BoardTopicDetail() {
  const { id } = useParams();
  const topic = useBoardTopic(id ?? null);
  const report = useReportTopic();

  return (
    <section>
      <p>
        <Link to="/board" className="muted">← 게시판</Link>
      </p>

      {topic.isLoading ? <p>로딩 중…</p> : null}
      {topic.isError ? <p style={{ color: 'var(--color-fail)' }}>{(topic.error as Error).message}</p> : null}

      {topic.isSuccess ? (
        <article className="card">
          <header style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <h2 style={{ margin: 0, flex: 1 }}>{topic.data.title}</h2>
            <ReportButton
              onReport={(reason) => report.mutateAsync({ topic_id: topic.data.topic_id, reason })}
              label="이 토픽 신고"
            />
          </header>
          <div className="muted" style={{ fontSize: '0.85rem', marginTop: '0.5rem' }}>
            {topic.data.display_name} · {new Date(topic.data.created_at).toLocaleString('ko-KR')}
            {topic.data.region_id ? <> · <code>{topic.data.region_id}</code></> : null}
            {topic.data.is_hidden ? <> · <span className="badge badge-warn">숨김</span></> : null}
          </div>
          <p style={{ whiteSpace: 'pre-wrap', marginTop: '1rem', lineHeight: 1.6 }}>{topic.data.body}</p>
        </article>
      ) : null}

      {topic.isSuccess ? (
        <CommentThread scope_type="board_topic" scope_id={topic.data.topic_id} />
      ) : null}
    </section>
  );
}
