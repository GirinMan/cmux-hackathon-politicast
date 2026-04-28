import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import BlackoutBanner, { BlackoutPlaceholder } from '../components/BlackoutBanner';

describe('<BlackoutBanner>', () => {
  it('renders nothing when inactive', () => {
    const { container } = render(<BlackoutBanner active={false} />);
    expect(container.firstChild).toBeNull();
  });

  it('shows endDate when active', () => {
    render(<BlackoutBanner active endDate="2026-06-03" />);
    expect(screen.getByRole('alert')).toHaveTextContent('블랙아웃');
    expect(screen.getByRole('alert')).toHaveTextContent('2026-06-03');
  });

  it('falls back to default when endDate missing', () => {
    render(<BlackoutBanner active />);
    expect(screen.getByRole('alert')).toHaveTextContent('선거 종료 시');
  });
});

describe('<BlackoutPlaceholder>', () => {
  it('renders blackout marker', () => {
    render(<BlackoutPlaceholder />);
    expect(screen.getByRole('img', { name: /blackout/i })).toBeInTheDocument();
  });

  it('honors custom message', () => {
    render(<BlackoutPlaceholder message="커스텀 메시지" />);
    expect(screen.getByText('커스텀 메시지')).toBeInTheDocument();
  });
});
