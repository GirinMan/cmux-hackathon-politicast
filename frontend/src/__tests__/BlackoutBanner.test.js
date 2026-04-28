import { jsx as _jsx } from "react/jsx-runtime";
import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import BlackoutBanner, { BlackoutPlaceholder } from '../components/BlackoutBanner';
describe('<BlackoutBanner>', () => {
    it('renders nothing when inactive', () => {
        const { container } = render(_jsx(BlackoutBanner, { active: false }));
        expect(container.firstChild).toBeNull();
    });
    it('shows endDate when active', () => {
        render(_jsx(BlackoutBanner, { active: true, endDate: "2026-06-03" }));
        expect(screen.getByRole('alert')).toHaveTextContent('블랙아웃');
        expect(screen.getByRole('alert')).toHaveTextContent('2026-06-03');
    });
    it('falls back to default when endDate missing', () => {
        render(_jsx(BlackoutBanner, { active: true }));
        expect(screen.getByRole('alert')).toHaveTextContent('선거 종료 시');
    });
});
describe('<BlackoutPlaceholder>', () => {
    it('renders blackout marker', () => {
        render(_jsx(BlackoutPlaceholder, {}));
        expect(screen.getByRole('img', { name: /blackout/i })).toBeInTheDocument();
    });
    it('honors custom message', () => {
        render(_jsx(BlackoutPlaceholder, { message: "\uCEE4\uC2A4\uD140 \uBA54\uC2DC\uC9C0" }));
        expect(screen.getByText('커스텀 메시지')).toBeInTheDocument();
    });
});
