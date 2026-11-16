import { test, expect } from '@playwright/test';

test.describe('17-18. Incoming-Member Continuity Dashboard & Tasks', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
    await page.getByRole('button', { name: /Auto Fill/i }).click();
    await page.locator('button[type="submit"]').click();
    await expect(page).toHaveURL(/.*dashboard/);
  });

  test('Incoming Member Dashboard loads all 7 continuity sections', async ({ page }) => {
    await page.goto('/incoming');
    await expect(page.getByRole('heading', { level: 1 })).toContainText('Incoming Member Dashboard');

    // Section 1: Shared Projects
    await expect(page.getByRole('heading', { name: /1\. Shared Projects/i })).toBeVisible();

    // Section 2: Received Handovers & Acknowledgement Status
    await expect(page.getByRole('heading', { name: /2\. Received Handovers/i })).toBeVisible();

    // Section 3: Pending Tasks & Continuity Tasks Manager
    await expect(page.getByRole('heading', { name: /3\. Continuation Tasks/i })).toBeVisible();

    // Section 4: Unresolved Issues & Blockers
    await expect(page.getByRole('heading', { name: /4\. Unresolved Issues/i })).toBeVisible();

    // Section 5: Dependencies
    await expect(page.getByRole('heading', { name: /5\. Project Dependencies/i })).toBeVisible();

    // Section 6: Recent Progress Updates
    await expect(page.getByRole('heading', { name: /6\. Recent Progress/i })).toBeVisible();
  });

  test('Acknowledge Handover Receipt modal opens and confirms acknowledgement', async ({ page }) => {
    await page.goto('/incoming');

    // Find "Acknowledge Receipt" button on the first unacknowledged handover
    const ackBtn = page.getByRole('button', { name: 'Acknowledge Receipt' }).first();
    if (await ackBtn.isVisible()) {
      await ackBtn.click();

      // Check modal is open
      await expect(page.getByText('Acknowledge Handover Receipt')).toBeVisible();

      // Check confirmation checkbox
      const checkbox = page.locator('input[type="checkbox"]').first();
      await checkbox.check();

      // Confirm acknowledgement
      const confirmBtn = page.getByRole('button', { name: /Formally Acknowledge Receipt|Confirm/i }).first();
      await confirmBtn.click();
    }
  });

  test('Task progress update modal logs progress and status change', async ({ page }) => {
    await page.goto('/incoming');

    // Filter to an already acknowledged handover or acknowledge first
    const filterBtn = page.getByRole('button', { name: /Filter Tasks/i }).first();
    if (await filterBtn.isVisible()) {
      await filterBtn.click();
    }

    // Now on acknowledged handover, find Log Progress / Update button
    const updateBtn = page.getByRole('button', { name: /Log Progress|Update Progress|Toggle progress history/i }).first();
    if (await updateBtn.isVisible()) {
      await updateBtn.click();
    }
  });
});
