import { FormEvent, useState } from 'react';
import { Link } from 'react-router-dom';

import { useAnonUser } from '../contexts/AnonUserContext';
import { useRegionState } from '../lib/regionState';
import { useBoardTopics, useCreateBoardTopic } from '../lib/communityQueries';

export default function BoardPage() {
  const { region } = useRegionState();
  const { ensureConsented } = useAnonUser();
  const [sort, setSort] = useState<'recent' | 'popular'>('recent');
  const [page, setPage] = useState(1);
  const [composing, setComposing] = useState(false);
  const [title, setTitle] = useState('');
  const [body, setBody] = useState('');
  const [filterByRegion, setFilterByRegion] = useState<boolean>(!!region);

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

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (!title.trim() || !body.trim()) return;
    await create.mutateAsync({
      title: title.trim(),
      body: body.trim(),
      region_id: filterByRegion && region ? region : null,
    });
    setTitle('');
    setBody('');
    setComposing(false);
  }

  return (
    <section>
      <header style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1rem' }}>
        <h2 style={{ margin: 0 }}>Board</h2>
        <select
          value={sort}
          onChange={(e) => { setSort(e.target.value as 'recent' | 'popular'); setPage(1); }}
          style={{ padding: '0.3rem 0.5rem', background: '#11151f', color: 'inherit', border: '1px solid #1f2330' }}
        >
          <option value="recent">최신</option>
          <option value="popular">인기</option>
        </select>
        {region ? (
          <label style={{ fontSize: '0.85rem' }}>
            <input
              type="checkbox"
              checked={filterByRegion}
              onChange={(e) => { setFilterByRegion(e.target.checked); setPage(1); }}
            />{' '}
            {region} 만 보기
          </label>
        ) : null}
        <button onClick={compose} style={{ marginLeft: 'auto' }}>
          새 토픽 작성
        </button>
      </header>

      {composing ? (
        <form onSubmit={submit} className="card" style={{ marginBottom: '1rem' }}>
          <input
            placeholder="제목"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            maxLength={120}
            style={{ width: '100%', padding: '0.5rem', background: '#0b0e14', color: 'inherit', border: '1px solid #1f2330', marginBottom: '0.5rem' }}
          />
          <textarea
            placeholder="본문"
            value={body}
            onChange={(e) => setBody(e.target.value)}
            rows={5}
            style={{ width: '100%', padding: '0.5rem', background: '#0b0e14', color: 'inherit', border: '1px solid #1f2330' }}
          />
          {create.isError ? (
            <p style={{ color: 'var(--color-fail)' }}>{(create.error as Error).message}</p>
          ) : null}
          <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'flex-end', marginTop: '0.5rem' }}>
            <button type="button" onClick={() => setComposing(false)} style={{ background: '#1f2330' }}>
              취소
            </button>
            <button type="submit" disabled={create.isPending || !title.trim() || !body.trim()}>
              {create.isPending ? '등록 중…' : '등록'}
            </button>
          </div>
        </form>
      ) : null}

      {list.isLoading ? <p>로딩 중…</p> : null}
      {list.isError ? <p style={{ color: 'var(--color-fail)' }}>{(list.error as Error).message}</p> : null}

      {list.isSuccess ? (
        <>
          <ul style={{ listStyle: 'none', padding: 0 }}>
            {list.data.items.map((t) => (
              <li key={t.topic_id} className="card" style={{ marginBottom: '0.5rem', opacity: t.is_hidden ? 0.5 : 1 }}>
                <Link to={`/board/topics/${t.topic_id}`} style={{ display: 'block' }}>
                  <strong>{t.title}</strong>
                </Link>
                <div className="muted" style={{ fontSize: '0.85rem', marginTop: '0.25rem' }}>
                  {t.display_name} · {new Date(t.created_at).toLocaleString('ko-KR')}
                  {t.region_id ? <> · <code>{t.region_id}</code></> : null}
                  · 댓글 {t.comment_count}
                  {t.is_hidden ? <> · <span className="badge badge-warn">숨김</span></> : null}
                </div>
              </li>
            ))}
          </ul>
          <Pagination
            page={page}
            total={list.data.total}
            pageSize={20}
            onChange={setPage}
          />
        </>
      ) : null}
    </section>
  );
}

interface PaginationProps {
  page: number;
  total: number;
  pageSize: number;
  onChange: (page: number) => void;
}

function Pagination({ page, total, pageSize, onChange }: PaginationProps) {
  const last = Math.max(1, Math.ceil(total / pageSize));
  return (
    <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'center', marginTop: '1rem' }}>
      <button onClick={() => onChange(Math.max(1, page - 1))} disabled={page <= 1}>이전</button>
      <span className="muted">
        {page} / {last}
      </span>
      <button onClick={() => onChange(Math.min(last, page + 1))} disabled={page >= last}>다음</button>
    </div>
  );
}
