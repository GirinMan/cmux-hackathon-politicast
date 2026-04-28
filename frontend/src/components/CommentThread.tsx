import { FormEvent, useMemo, useState } from 'react';

import { useAnonUser } from '../contexts/AnonUserContext';
import { CommentDTO } from '../lib/anonApi';
import {
  useComments,
  useCreateComment,
  useDeleteComment,
  useReportComment,
  useUpdateComment,
} from '../lib/communityQueries';

import ReportButton from './ReportButton';

interface Props {
  scope_type: 'region' | 'scenario' | 'board_topic' | 'scenario_tree';
  scope_id: string;
  /** 블랙아웃 기간이면 작성 폼 비활성화. 댓글 읽기는 그대로. */
  blackout?: boolean;
}

interface Node {
  comment: CommentDTO;
  children: Node[];
}

function buildTree(items: CommentDTO[]): Node[] {
  const byId = new Map<string, Node>();
  items.forEach((c) => byId.set(c.comment_id, { comment: c, children: [] }));
  const roots: Node[] = [];
  byId.forEach((node) => {
    const pid = node.comment.parent_id;
    if (pid && byId.has(pid)) {
      byId.get(pid)!.children.push(node);
    } else {
      roots.push(node);
    }
  });
  // 시간순 정렬
  const sortFn = (a: Node, b: Node) =>
    a.comment.created_at.localeCompare(b.comment.created_at);
  function recurse(arr: Node[]) {
    arr.sort(sortFn);
    arr.forEach((n) => recurse(n.children));
  }
  recurse(roots);
  return roots;
}

export default function CommentThread({ scope_type, scope_id, blackout }: Props) {
  const { userId, hasConsented, ensureConsented } = useAnonUser();
  const list = useComments(scope_type, scope_id);
  const create = useCreateComment(scope_type, scope_id);
  const update = useUpdateComment(scope_type, scope_id);
  const remove = useDeleteComment(scope_type, scope_id);
  const report = useReportComment();

  const [body, setBody] = useState('');
  const [replyTo, setReplyTo] = useState<string | null>(null);
  const [editing, setEditing] = useState<string | null>(null);
  const [editBody, setEditBody] = useState('');

  const tree = useMemo(() => (list.isSuccess ? buildTree(list.data) : []), [list.isSuccess, list.data]);

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (!body.trim()) return;
    await ensureConsented(async () => {
      await create.mutateAsync({ body: body.trim(), parent_id: replyTo });
      setBody('');
      setReplyTo(null);
    });
  }

  async function saveEdit(comment_id: string) {
    if (!editBody.trim()) return;
    await update.mutateAsync({ comment_id, body: editBody.trim() });
    setEditing(null);
    setEditBody('');
  }

  return (
    <section aria-label="comments" style={{ marginTop: '2rem' }}>
      <h3>💬 댓글 ({list.isSuccess ? list.data.length : '…'})</h3>

      {blackout ? (
        <p className="muted" style={{ fontStyle: 'italic' }}>
          블랙아웃 기간 동안 새 댓글 작성은 제한됩니다. 기존 대화는 계속 읽으실 수 있습니다.
        </p>
      ) : (
        <form onSubmit={submit} style={{ marginBottom: '1rem' }}>
          <textarea
            value={body}
            onChange={(e) => setBody(e.target.value)}
            rows={3}
            placeholder={hasConsented ? '의견을 남겨 주세요' : '닉네임을 받고 첫 의견을 남겨보세요'}
            disabled={create.isPending}
            style={{ width: '100%', background: '#0b0e14', color: 'inherit', padding: '0.5rem', border: '1px solid #1f2330', borderRadius: 4 }}
          />
          <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', marginTop: '0.5rem' }}>
            {replyTo ? (
              <span className="muted" style={{ fontSize: '0.85rem' }}>
                ↳ 답글: <code>{replyTo.slice(0, 8)}</code>{' '}
                <button type="button" onClick={() => setReplyTo(null)} style={{ background: 'transparent', color: 'var(--color-muted)' }}>
                  ✕
                </button>
              </span>
            ) : null}
            <button type="submit" disabled={create.isPending || !body.trim()} style={{ marginLeft: 'auto' }}>
              {create.isPending ? '등록 중…' : '등록'}
            </button>
          </div>
        </form>
      )}

      {list.isLoading ? <p>댓글 로딩 중…</p> : null}
      {list.isError ? (
        <p style={{ color: 'var(--color-fail)' }}>{(list.error as Error).message}</p>
      ) : null}

      <ul style={{ listStyle: 'none', padding: 0 }}>
        {tree.map((n) => (
          <CommentItem
            key={n.comment.comment_id}
            node={n}
            depth={0}
            currentUserId={userId}
            onReply={(id) => setReplyTo(id)}
            onStartEdit={(c) => {
              setEditing(c.comment_id);
              setEditBody(c.body);
            }}
            editing={editing}
            editBody={editBody}
            setEditBody={setEditBody}
            onSaveEdit={saveEdit}
            onCancelEdit={() => {
              setEditing(null);
              setEditBody('');
            }}
            onDelete={(id) => remove.mutate(id)}
            onReport={(id, reason) => report.mutateAsync({ comment_id: id, reason })}
            blackout={blackout}
          />
        ))}
      </ul>
    </section>
  );
}

interface ItemProps {
  node: Node;
  depth: number;
  currentUserId: string | null;
  onReply: (id: string) => void;
  onStartEdit: (c: CommentDTO) => void;
  editing: string | null;
  editBody: string;
  setEditBody: (s: string) => void;
  onSaveEdit: (id: string) => void | Promise<void>;
  onCancelEdit: () => void;
  onDelete: (id: string) => void;
  onReport: (id: string, reason: string) => Promise<void>;
  blackout?: boolean;
}

function CommentItem({
  node, depth, currentUserId, onReply, onStartEdit, editing, editBody, setEditBody,
  onSaveEdit, onCancelEdit, onDelete, onReport, blackout,
}: ItemProps) {
  const c = node.comment;
  const isOwner = currentUserId !== null && currentUserId === c.user_id;
  const hidden = c.is_hidden || c.is_deleted;

  return (
    <li
      className="card"
      style={{
        marginLeft: depth * 1.25 + 'rem',
        marginBottom: '0.5rem',
        opacity: hidden ? 0.5 : 1,
      }}
    >
      <header style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', fontSize: '0.85rem' }}>
        <strong>{c.display_name}</strong>
        <span className="muted">{new Date(c.created_at).toLocaleString('ko-KR')}</span>
        {c.report_count > 0 ? (
          <span className="badge badge-warn">신고 {c.report_count}</span>
        ) : null}
      </header>
      {hidden ? (
        <p className="muted" style={{ fontStyle: 'italic' }}>
          {c.is_deleted ? '삭제된 댓글입니다.' : '신고로 가려진 댓글입니다.'}
        </p>
      ) : editing === c.comment_id ? (
        <>
          <textarea
            value={editBody}
            onChange={(e) => setEditBody(e.target.value)}
            rows={3}
            style={{ width: '100%', background: '#0b0e14', color: 'inherit', padding: '0.4rem', border: '1px solid #1f2330' }}
          />
          <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'flex-end' }}>
            <button onClick={onCancelEdit} style={{ background: '#1f2330' }}>취소</button>
            <button onClick={() => { void onSaveEdit(c.comment_id); }}>저장</button>
          </div>
        </>
      ) : (
        <p style={{ whiteSpace: 'pre-wrap', margin: '0.5rem 0' }}>{c.body}</p>
      )}

      {!hidden && editing !== c.comment_id ? (
        <div style={{ display: 'flex', gap: '0.5rem', fontSize: '0.85rem' }}>
          {!blackout ? (
            <button onClick={() => onReply(c.comment_id)} style={{ background: 'transparent', color: 'var(--color-muted)' }}>
              답글
            </button>
          ) : null}
          {isOwner ? (
            <>
              <button onClick={() => onStartEdit(c)} style={{ background: 'transparent', color: 'var(--color-muted)' }}>
                수정
              </button>
              <button onClick={() => onDelete(c.comment_id)} style={{ background: 'transparent', color: 'var(--color-fail)' }}>
                삭제
              </button>
            </>
          ) : (
            <ReportButton onReport={(reason) => onReport(c.comment_id, reason)} />
          )}
        </div>
      ) : null}

      {node.children.length > 0 ? (
        <ul style={{ listStyle: 'none', padding: 0, marginTop: '0.5rem' }}>
          {node.children.map((child) => (
            <CommentItem
              key={child.comment.comment_id}
              node={child}
              depth={depth + 1}
              currentUserId={currentUserId}
              onReply={onReply}
              onStartEdit={onStartEdit}
              editing={editing}
              editBody={editBody}
              setEditBody={setEditBody}
              onSaveEdit={onSaveEdit}
              onCancelEdit={onCancelEdit}
              onDelete={onDelete}
              onReport={onReport}
              blackout={blackout}
            />
          ))}
        </ul>
      ) : null}
    </li>
  );
}
