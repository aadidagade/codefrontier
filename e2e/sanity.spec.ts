import { test, expect } from '@playwright/test';

test.describe('Sanity Check', () => {
  test('loads landing page', async ({ page }) => {
    await page.goto('/');
    await expect(page).toHaveTitle(/Knowledge/i);
  });
});
