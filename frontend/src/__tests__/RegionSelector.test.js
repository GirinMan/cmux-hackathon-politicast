import { jsx as _jsx } from "react/jsx-runtime";
import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import RegionSelector from '../components/RegionSelector';
const REGIONS = [
    {
        region_id: 'seoul_mayor',
        name: '서울시장',
        election_id: 'seoul_mayor_2026',
        election_date: '2026-06-03',
        position_type: 'mayor',
        timezone: 'Asia/Seoul',
    },
    {
        region_id: 'daegu_mayor',
        name: '대구시장',
        election_id: 'daegu_mayor_2026',
        election_date: '2026-06-03',
        position_type: 'mayor',
        timezone: 'Asia/Seoul',
    },
];
describe('<RegionSelector>', () => {
    it('renders all regions and reports active', () => {
        const onChange = vi.fn();
        render(_jsx(RegionSelector, { regions: REGIONS, value: "seoul_mayor", onChange: onChange }));
        expect(screen.getByText('서울시장')).toBeInTheDocument();
        expect(screen.getByText('대구시장')).toBeInTheDocument();
        const seoul = screen.getByRole('radio', { name: /서울시장/ });
        expect(seoul).toHaveAttribute('aria-checked', 'true');
    });
    it('fires onChange with regionId + electionId', () => {
        const onChange = vi.fn();
        render(_jsx(RegionSelector, { regions: REGIONS, value: null, onChange: onChange }));
        fireEvent.click(screen.getByRole('radio', { name: /대구시장/ }));
        expect(onChange).toHaveBeenCalledWith('daegu_mayor', 'daegu_mayor_2026');
    });
});
