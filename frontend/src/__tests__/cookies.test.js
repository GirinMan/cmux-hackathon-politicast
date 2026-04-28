import { afterEach, describe, expect, it } from 'vitest';
import { clearAllAnonState, readConsent, readUserCache, writeConsent, writeUserCache, } from '../lib/cookies';
afterEach(() => {
    clearAllAnonState();
});
describe('cookies / consent', () => {
    it('writeConsent + readConsent round-trip', () => {
        expect(readConsent()).toBe(false);
        writeConsent(true);
        expect(readConsent()).toBe(true);
        writeConsent(false);
        expect(readConsent()).toBe(false);
    });
    it('writeUserCache + readUserCache round-trip', () => {
        expect(readUserCache()).toBeNull();
        writeUserCache({ user_id: 'u_1', display_name: '익명1', fetched_at: '2026-04-28' });
        expect(readUserCache()).toEqual({
            user_id: 'u_1',
            display_name: '익명1',
            fetched_at: '2026-04-28',
        });
    });
    it('clearAllAnonState wipes both', () => {
        writeConsent(true);
        writeUserCache({ user_id: 'u_1', display_name: 'x', fetched_at: '' });
        clearAllAnonState();
        expect(readConsent()).toBe(false);
        expect(readUserCache()).toBeNull();
    });
});
