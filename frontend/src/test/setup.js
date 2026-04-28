import '@testing-library/jest-dom/vitest';
import { afterEach } from 'vitest';
import { cleanup } from '@testing-library/react';
afterEach(() => {
    cleanup();
});
// Plotly + cytoscape는 jsdom 에서 무거우니 default mock.
// 테스트가 차트 동작을 검증하지 않도록 inert 컴포넌트로 대체.
if (typeof window !== 'undefined') {
    // window.matchMedia poly
    if (!window.matchMedia) {
        window.matchMedia = () => ({ matches: false, addEventListener: () => { }, removeEventListener: () => { } });
    }
}
