/**
 * 공직선거법 §108 블랙아웃 표시. 페이지 상단에 노란 배너.
 * AI 차트(LineChart/BarChart) 가 blackout=true 일 때 placeholder 로 대체.
 */

interface Props {
  /** true 면 배너 + 차트 placeholder 활성화. 보통 backend 응답 meta.blackout. */
  active: boolean;
  /** 종료 일자 (ISO 또는 한국어 표기). null 이면 "선거 종료 시까지". */
  endDate?: string | null;
  /** 추가 메시지 (선택). */
  reason?: string;
}

export default function BlackoutBanner({ active, endDate, reason }: Props) {
  if (!active) return null;
  return (
    <div
      role="alert"
      className="card"
      style={{
        background: '#3a3500',
        border: '1px solid var(--color-warn)',
        color: '#fff7d6',
        padding: '0.75rem 1rem',
        marginBottom: '1rem',
      }}
    >
      <strong>⚠️ 블랙아웃 기간</strong>{' '}
      <span>
        공직선거법 제108조에 따라 <strong>{endDate ?? '선거 종료 시'}</strong>까지 일부
        예측 화면과 새 댓글 작성이 제한됩니다.
      </span>
      {reason ? <p style={{ margin: '0.25rem 0 0', fontSize: '0.85rem' }}>{reason}</p> : null}
    </div>
  );
}

export function BlackoutPlaceholder({ message }: { message?: string }) {
  return (
    <div
      role="img"
      aria-label="blackout placeholder"
      className="card"
      style={{
        height: 360,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        textAlign: 'center',
        background: 'repeating-linear-gradient(45deg, #1a1a1a, #1a1a1a 8px, #11151f 8px, #11151f 16px)',
        color: 'var(--color-warn)',
        border: '1px dashed var(--color-warn)',
      }}
    >
      <div>
        <p style={{ margin: 0, fontSize: '1.2rem' }}>🔒 블랙아웃</p>
        <p style={{ margin: '0.5rem 0 0', fontSize: '0.9rem' }}>
          {message ?? '공직선거법 §108에 따라 비공개 처리되었습니다.'}
        </p>
      </div>
    </div>
  );
}
