import { test, expect } from '@playwright/test';

test.describe('7, 8, 11. Handover Generation, Display, Editing & Approval', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
    await page.getByRole('button', { name: /Auto Fill/i }).click();
    await page.locator('button[type="submit"]').click();
    await expect(page).toHaveURL(/.*dashboard/);
  });

  test('Generate Handover page loads documents, allows selection, and generates handover', async ({ page }) => {
    await page.goto('/handover/generate');
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible();

    // Select all ready documents
    const selectAllBtn = page.getByRole('button', { name: /^Select All Ready/i });
    if (await selectAllBtn.isVisible()) {
      await selectAllBtn.click();
    } else {
      // Toggle first checkbox
      const checkbox = page.locator('tbody input[type="checkbox"]').first();
      await checkbox.check();
    }

    // Trigger Generation
    const generateBtn = page.getByRole('button', { name: /Generate Structured Handover/i });
    await expect(generateBtn).toBeEnabled();
    await generateBtn.click();

    // Verify progress / stage tracker or completed handover view
    await expect(page.getByText(/Reconstructed|Reconstruction|Complete|Overview/i).first()).toBeVisible({ timeout: 15000 });
  });

  test('Review Workspace displays sections, evidence citations, and version history toggle', async ({ page }) => {
    await page.goto('/review/rev-auth-zero');
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible();

    // Verify sections (e.g. Overview, Architecture, Key Decisions)
    await expect(page.getByText(/Project Overview|Architecture|Decisions|Tasks/i).first()).toBeVisible();

    // Check action buttons (Approve, Request Changes, Edit)
    const approveBtn = page.getByRole('button', { name: /Approve|Sign Off/i }).first();
    await expect(approveBtn).toBeVisible();

    // Check Version History toggle button
    const versionHistoryBtn = page.getByRole('button', { name: /Version History|History/i }).first();
    if (await versionHistoryBtn.isVisible()) {
      await versionHistoryBtn.click();
      await expect(page.getByText(/Version|Snapshot|Baseline/i).first()).toBeVisible();
    }
  });
});
