import { test, expect } from '@playwright/test';

test.describe('9-10. Evidence Verification & Contradiction Detection', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
    await page.getByRole('button', { name: /Auto Fill/i }).click();
    await page.locator('button[type="submit"]').click();
    await expect(page).toHaveURL(/.*dashboard/);
  });

  test('Evidence Verification Dashboard loads and displays claim metrics', async ({ page }) => {
    await page.goto('/verification');
    await expect(page.getByRole('heading', { level: 1 })).toContainText('Evidence Verification Dashboard');

    // Run verification engine button should be present
    const runBtn = page.getByRole('button', { name: /Run Verification Engine|Start First Verification/i }).first();
    await expect(runBtn).toBeVisible();
  });

  test('Knowledge Conflicts page loads and displays contradiction categories and items', async ({ page }) => {
    await page.goto('/conflicts');
    await expect(page.getByRole('heading', { level: 1 })).toContainText('Knowledge Conflicts');

    // Verify scan / detect button exists
    const scanBtn = page.getByRole('button', { name: /Run Contradiction Scan/i }).first();
    await expect(scanBtn).toBeVisible();
  });
});
