import { FormEvent, useState } from 'react';

import { useAnonUser } from '../contexts/AnonUserContext';

/**
 * 헤더 우상단에 노출. 클릭 시 dialog 로 닉네임 변경.
 * 동의 전이라면 banner 를 먼저 띄운다.
 */
export default function NicknameEditor() {
  const { displayName, hasConsented, ensureConsented, updateNickname, openBanner, logout } = useAnonUser();
  const [open, setOpen] = useState(false);
  const [draft, setDraft] = useState(displayName ?? '');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function trigger() {
    if (!hasConsented) {
      openBanner();
      return;
    }
    setDraft(displayName ?? '');
    setOpen(true);
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!draft.trim()) {
      setError('닉네임을 입력해 주세요.');
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await updateNickname(draft.trim());
      setOpen(false);
    } catch (err) {
      setError((err as Error).message ?? '닉네임 변경에 실패했습니다.');
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <button
        type="button"
        onClick={trigger}
        title="닉네임 변경"
        style={{ background: 'transparent', color: 'inherit', padding: '0.25rem 0.5rem' }}
      >
        {hasConsented ? (
          <>👤 {displayName ?? '닉네임 받기'}</>
        ) : (
          <>👤 익명으로 시작</>
        )}
      </button>
      {open ? (
        <div
          role="dialog"
          aria-modal="true"
          style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.6)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 80 }}
          onClick={() => !busy && setOpen(false)}
        >
          <form
            className="card"
            style={{ minWidth: 320 }}
            onClick={(e) => e.stopPropagation()}
            onSubmit={(e) => { void onSubmit(e); }}
          >
            <h4 style={{ marginTop: 0 }}>닉네임 변경</h4>
            <input
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              maxLength={24}
              autoFocus
              style={{ width: '100%', padding: '0.5rem', background: '#0b0e14', color: 'inherit', border: '1px solid #1f2330' }}
            />
            {error ? <p style={{ color: 'var(--color-fail)' }}>{error}</p> : null}
            <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'space-between', marginTop: '1rem' }}>
              <button
                type="button"
                onClick={() => { void logout(); setOpen(false); }}
                style={{ background: 'transparent', color: 'var(--color-muted)' }}
              >
                로그아웃 (쿠키 삭제)
              </button>
              <div style={{ display: 'flex', gap: '0.5rem' }}>
                <button type="button" onClick={() => setOpen(false)} disabled={busy} style={{ background: '#1f2330' }}>
                  취소
                </button>
                <button type="submit" disabled={busy}>
                  {busy ? '저장 중…' : '저장'}
                </button>
              </div>
            </div>
          </form>
        </div>
      ) : null}
    </>
  );
}
