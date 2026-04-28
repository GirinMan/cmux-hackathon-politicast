import { useState } from 'react';

import { useAnonUser } from '../contexts/AnonUserContext';

const REPORT_REASONS = [
  { value: 'spam', label: '스팸/광고' },
  { value: 'abuse', label: '욕설/혐오 표현' },
  { value: 'misinformation', label: '허위 정보' },
  { value: 'doxxing', label: '신상 공개' },
  { value: 'other', label: '기타' },
];

interface Props {
  onReport: (reason: string) => Promise<void>;
  label?: string;
  disabled?: boolean;
}

export default function ReportButton({ onReport, label = '신고', disabled }: Props) {
  const { ensureConsented } = useAnonUser();
  const [open, setOpen] = useState(false);
  const [reason, setReason] = useState('spam');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);

  async function trigger() {
    await ensureConsented(() => setOpen(true));
  }

  async function submit() {
    setBusy(true);
    setError(null);
    try {
      await onReport(reason);
      setDone(true);
      setTimeout(() => {
        setDone(false);
        setOpen(false);
      }, 1200);
    } catch (err) {
      setError((err as Error).message ?? '신고 처리에 실패했습니다.');
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <button
        type="button"
        onClick={trigger}
        disabled={disabled}
        style={{ background: 'transparent', color: 'var(--color-muted)', padding: '0.25rem 0.5rem', fontSize: '0.85rem' }}
        aria-label={label}
      >
        {label}
      </button>
      {open ? (
        <div
          role="dialog"
          aria-modal="true"
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(0,0,0,0.6)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 80,
          }}
          onClick={() => !busy && setOpen(false)}
        >
          <div className="card" style={{ minWidth: 320 }} onClick={(e) => e.stopPropagation()}>
            <h4 style={{ marginTop: 0 }}>신고 사유</h4>
            <select
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              disabled={busy || done}
              style={{ width: '100%', padding: '0.4rem', background: '#0b0e14', color: 'inherit', border: '1px solid #1f2330' }}
            >
              {REPORT_REASONS.map((r) => (
                <option key={r.value} value={r.value}>
                  {r.label}
                </option>
              ))}
            </select>
            {error ? <p style={{ color: 'var(--color-fail)' }}>{error}</p> : null}
            {done ? <p style={{ color: 'var(--color-pass)' }}>신고가 접수되었습니다.</p> : null}
            <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'flex-end', marginTop: '1rem' }}>
              <button onClick={() => setOpen(false)} disabled={busy} style={{ background: '#1f2330' }}>
                취소
              </button>
              <button onClick={submit} disabled={busy || done}>
                {busy ? '전송 중…' : '신고하기'}
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </>
  );
}
