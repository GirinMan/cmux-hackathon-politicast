import { describe, expect, it } from 'vitest';
import { AdminLoginResponse, PersonaSampleDTO, PollPointDTO, RegionDTO, } from '../lib/types';
describe('zod DTO mirrors', () => {
    it('parses RegionDTO with required fields', () => {
        const out = RegionDTO.parse({
            region_id: 'seoul_mayor',
            name: '서울시장',
            election_id: 'seoul_mayor_2026',
            election_date: '2026-06-03',
            position_type: 'mayor',
        });
        expect(out.timezone).toBe('Asia/Seoul');
    });
    it('parses PersonaSampleDTO with optional fields', () => {
        const out = PersonaSampleDTO.parse({ persona_id: 'p_x' });
        expect(out.summary).toBe('');
    });
    it('parses PollPointDTO with default support map', () => {
        const out = PollPointDTO.parse({ timestep: 0 });
        expect(out.support_by_candidate).toEqual({});
    });
    it('AdminLoginResponse defaults token_type to bearer', () => {
        const out = AdminLoginResponse.parse({
            access_token: 'tok',
            expires_in: 3600,
            username: 'admin',
        });
        expect(out.token_type).toBe('bearer');
    });
});
