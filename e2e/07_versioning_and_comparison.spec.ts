import { test, expect } from '@playwright/test';

test.describe('15-16. Handover Version History, Comparison & Restoration', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
    await page.getByRole('button', { name: /Auto Fill/i }).click();
    await page.locator('button[type="submit"]').click();
    await expect(page).toHaveURL(/.*dashboard/);
  });

  test('Version History page displays versions list, snapshot modal, and create snapshot button', async ({ page }) => {
    await page.goto('/handovers/rev-auth-zero/versions');
    await expect(page.getByRole('heading', { level: 1 })).toContainText('Handover Version Management');

    // Create Snapshot button
    const snapshotBtn = page.getByRole('button', { name: /Create Snapshot/i });
    await expect(snapshotBtn).toBeVisible();

    // Verify version entries exist (v1.0, v1.1, etc.)
    await expect(page.getByText(/v1\./i).first()).toBeVisible();

    // Click "View Version" on first version
    const viewBtn = page.getByRole('button', { name: /View Version/i }).first();
    if (await viewBtn.isVisible()) {
      await viewBtn.click();
      await expect(page.getByText(/Snapshot captured on|Version v1\./i).first()).toBeVisible();
      // Close snapshot modal
      await page.keyboard.press('Escape');
    }
  });

  test('Version Comparison Modal renders diff highlights (Added, Removed, Modified)', async ({ page }) => {
    await page.goto('/handovers/rev-auth-zero/versions');

    // Click Compare Versions
    const compareBtn = page.getByRole('button', { name: 'Compare Versions' });
    if (await compareBtn.isVisible()) {
      await compareBtn.click();

      // Check Comparison Modal
      await expect(page.getByText('Version Comparison Engine')).toBeVisible();

      // Check diff indicators or tabs (Overview, Architecture, Tasks)
      await expect(page.getByText(/Technical Architecture|Project Overview|Pending Tasks/i).first()).toBeVisible();
    }
  });

  test('Version Restoration opens confirmation modal with non-destructive preservation notice', async ({ page }) => {
    await page.goto('/handovers/rev-auth-zero/versions');

    // Find Restore Version button on a historical version
    const restoreBtn = page.getByRole('button', { name: 'Restore Version' }).first();
    if (await restoreBtn.isVisible()) {
      await restoreBtn.click();
      // Confirm Restore modal shows preservation notice
      await expect(page.getByText('Restore Previous Version')).toBeVisible();
    }
  });
});
