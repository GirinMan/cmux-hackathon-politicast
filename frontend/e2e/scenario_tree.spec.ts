/**
 * Phase 6 — Playwright E2E smoke for the ScenarioTreePage happy path.
 *
 * This file is opt-in: Playwright isn't installed in CI by default. Run
 * locally with:
 *
 *   cd frontend && npm i -D @playwright/test && npx playwright install
 *   POLITIKAST_E2E=1 npx playwright test e2e/scenario_tree.spec.ts
 *
 * The harness skips itself when Playwright isn't present so that
 * `cd frontend && npm test` (vitest) keeps passing in environments without
 * the browser stack.
 */
let test: any;
let expect: any;

try {
  // eslint-disable-next-line @typescript-eslint/no-require-imports, @typescript-eslint/no-var-requires
  ({ test, expect } = require('@playwright/test'));
} catch {
  // Playwright not installed — emit a no-op suite so the file imports cleanly
  // (vitest test runner will not pick this up; only @playwright/test runner).
  // eslint-disable-next-line no-console
  console.warn('[e2e/scenario_tree.spec] @playwright/test missing — skipping');
  test = (..._args: unknown[]) => {};
  test.describe = (_n: string, fn: () => void) => fn();
  expect = () => ({ toBeVisible: () => undefined, toContainText: () => undefined });
}

const BASE = process.env.POLITIKAST_FE_BASE ?? 'http://localhost:5173';
const REGION = process.env.POLITIKAST_E2E_REGION ?? 'seoul_mayor';

test.describe('ScenarioTreePage smoke', () => {
  test('cookie consent → sankey renders → comment happy path', async ({
    page,
  }: any) => {
    await page.goto(`${BASE}/?region=${REGION}`);

    // 1. Cookie consent banner — accept if present.
    const consent = page.getByRole('button', { name: /동의|허용|accept/i });
    if (await consent.count()) {
      await consent.first().click();
    }

    // 2. Navigate to the scenario tree page.
    await page.goto(`${BASE}/scenario-tree?region=${REGION}`);
    await expect(page.getByRole('heading', { name: /시나리오 트리/ })).toBeVisible();

    // 3. The Sankey container or the empty-state must show.
    const sankey = page.getByTestId('sankey-container');
    const emptyState = page.getByRole('status');
    await expect(sankey.or(emptyState).first()).toBeVisible();

    // 4. If the tree rendered, click root and ensure the drilldown side panel
    //    appears. Otherwise this is still a successful smoke (empty state).
    if (await sankey.count()) {
      await page.locator('[data-node-id]').first().click();
      await expect(page.getByRole('dialog', { name: /시나리오 노드 상세/ }))
        .toBeVisible();
    }

    // 5. Comment thread is mounted under the tree (smoke only — backend
    //    interactions covered by tests/api/test_comments.py).
    const threadHeading = page.getByRole('heading', {
      name: /시나리오 트리 토론/,
    });
    if (await sankey.count()) {
      await expect(threadHeading).toBeVisible();
    }
  });
});
