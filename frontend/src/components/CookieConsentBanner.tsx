import { useState } from 'react';

import { useAnonUser } from '../contexts/AnonUserContext';

/**
 * 작성 액션(댓글/토픽/신고) 시 hasConsented=false 면 자동 노출되는 modal.
 * 동의 → POST /api/v1/users/anonymous → backend 가 HttpOnly cookie 발급.
 */
export default function CookieConsentBanner() {
  const { bannerOpen, closeBanner, consent, hasConsented } = useAnonUser();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!bannerOpen || hasConsented) return null;

  async function onAccept() {
    setBusy(true);
    setError(null);
    try {
      await consent();
      closeBanner();
    } catch (err) {
      setError((err as Error).message ?? '동의 처리에 실패했습니다.');
    } finally {
      setBusy(false);
    }
  }

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="consent-title"
      style={{
        position: 'fixed',
        inset: 0,
        background: 'rgba(0,0,0,0.6)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 100,
      }}
      onClick={closeBanner}
    >
      <div
        className="card"
        style={{ maxWidth: 480, padding: '1.5rem' }}
        onClick={(e) => e.stopPropagation()}
      >
        <h3 id="consent-title" style={{ marginTop: 0 }}>익명 닉네임으로 함께 이야기하기</h3>
        <p style={{ lineHeight: 1.6 }}>
          댓글·게시판을 이용하시려면 <strong>임의 닉네임</strong> 이 자동으로
          만들어집니다. 닉네임은 언제든 바꾸실 수 있고, 따로 회원가입은 필요하지
          않습니다.
        </p>
        <ul style={{ fontSize: '0.9rem', lineHeight: 1.6 }}>
          <li>저장되는 항목: 익명 식별 쿠키 (HttpOnly), 표시 닉네임, 작성한 글.</li>
          <li>저장되지 않는 항목: 이메일, 전화번호, IP 영구기록.</li>
          <li>언제든 헤더의 "로그아웃" 으로 쿠키를 폐기할 수 있습니다.</li>
        </ul>
        {error ? (
          <p style={{ color: 'var(--color-fail)', marginTop: '0.5rem' }}>{error}</p>
        ) : null}
        <div style={{ display: 'flex', gap: '0.75rem', justifyContent: 'flex-end', marginTop: '1rem' }}>
          <button
            onClick={closeBanner}
            disabled={busy}
            style={{ background: '#1f2330' }}
          >
            나중에
          </button>
          <button onClick={onAccept} disabled={busy}>
            {busy ? '동의 중…' : '동의하고 닉네임 받기'}
          </button>
        </div>
      </div>
    </div>
  );
}
