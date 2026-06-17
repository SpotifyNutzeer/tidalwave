import { test, expect } from '@playwright/test';

test('landing shows connect CTA when anonymous', async ({ page }) => {
  // /auth/me has no backend in preview → intercept it as 401 (anonymous).
  await page.route('**/auth/me', (route) => route.fulfill({ status: 401, body: '{"detail":"no"}' }));
  await page.goto('/');
  await expect(page.getByRole('link', { name: /connect with last\.fm/i })).toBeVisible();
});
