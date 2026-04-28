import { useState } from 'react';

import {
  useHideComment,
  useHideTopic,
  useReports,
  useResolveReport,
} from '../../lib/communityQueries';

type Tab = 'open' | 'resolved';

export default function ModerationPage() {
  const [tab, setTab] = useState<Tab>('open');
  const reports = useReports(tab);
  const resolve = useResolveReport();
  const hideComment = useHideComment();
  const hideTopic = useHideTopic();

  return (
    <section>
      <header style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
        <h2 style={{ margin: 0 }}>Moderation</h2>
        <nav style={{ display: 'flex', gap: '0.5rem', marginLeft: '1rem' }}>
          {(['open', 'resolved'] as Tab[]).map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              style={{
                background: tab === t ? 'var(--color-accent)' : '#1f2330',
                color: 'white',
              }}
            >
              {t === 'open' ? '신고 큐' : '처리됨'}
            </button>
          ))}
        </nav>
      </header>

      {reports.isLoading ? <p>로딩 중…</p> : null}
      {reports.isError ? (
        <p style={{ color: 'var(--color-fail)' }}>{(reports.error as Error).message}</p>
      ) : null}

      {reports.isSuccess ? (
        <table style={{ width: '100%', borderCollapse: 'collapse', marginTop: '1rem' }}>
          <thead>
            <tr style={{ textAlign: 'left', borderBottom: '1px solid #1f2330' }}>
              <th>report_id</th>
              <th>대상</th>
              <th>사유</th>
              <th>제보자</th>
              <th>상태</th>
              <th>접수 시각</th>
              <th>액션</th>
            </tr>
          </thead>
          <tbody>
            {reports.data.map((r) => (
              <tr key={r.report_id} style={{ borderBottom: '1px solid #1f2330' }}>
                <td><code>{r.report_id.slice(0, 8)}</code></td>
                <td>
                  <span className="badge">{r.target_type}</span>
                  <code style={{ marginLeft: '0.5rem' }}>{r.target_id.slice(0, 12)}</code>
                </td>
                <td>{r.reason}</td>
                <td><code>{r.reporter_user_id.slice(0, 8)}</code></td>
                <td>
                  <span className={`badge ${r.status === 'open' ? 'badge-warn' : 'badge-pass'}`}>
                    {r.status}
                  </span>
                </td>
                <td>{new Date(r.created_at).toLocaleString('ko-KR')}</td>
                <td>
                  {r.status === 'open' ? (
                    <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                      <button
                        onClick={() =>
                          resolve.mutate({ report_id: r.report_id, action: 'hide_target' })
                        }
                        disabled={resolve.isPending}
                        style={{ background: 'var(--color-fail)' }}
                      >
                        대상 숨김
                      </button>
                      <button
                        onClick={() =>
                          resolve.mutate({ report_id: r.report_id, action: 'dismiss' })
                        }
                        disabled={resolve.isPending}
                        style={{ background: '#1f2330' }}
                      >
                        기각
                      </button>
                      {r.target_type === 'comment' ? (
                        <button
                          onClick={() => hideComment.mutate(r.target_id)}
                          disabled={hideComment.isPending}
                          style={{ background: '#1f2330' }}
                        >
                          댓글 즉시 숨김
                        </button>
                      ) : null}
                      {r.target_type === 'board_topic' ? (
                        <button
                          onClick={() => hideTopic.mutate(r.target_id)}
                          disabled={hideTopic.isPending}
                          style={{ background: '#1f2330' }}
                        >
                          토픽 즉시 숨김
                        </button>
                      ) : null}
                    </div>
                  ) : (
                    <span className="muted">처리 완료</span>
                  )}
                </td>
              </tr>
            ))}
            {reports.data.length === 0 ? (
              <tr>
                <td colSpan={7} style={{ padding: '2rem', textAlign: 'center' }} className="muted">
                  큐가 비어있습니다.
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      ) : null}
    </section>
  );
}
