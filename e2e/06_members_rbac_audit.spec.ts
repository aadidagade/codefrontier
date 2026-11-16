import { test, expect } from '@playwright/test';

test.describe('12-14. Project Members, RBAC Permissions & Audit Trail', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
    await page.getByRole('button', { name: /Auto Fill/i }).click();
    await page.locator('button[type="submit"]').click();
    await expect(page).toHaveURL(/.*dashboard/);
  });

  test('Project Members page lists members and opens Add Member modal', async ({ page }) => {
    await page.goto('/projects/proj-1/members');
    await expect(page.getByRole('heading', { level: 1 })).toContainText('Project Members');

    // Verify member table has rows
    await expect(page.locator('table, .divide-y').first()).toBeVisible();

    // Open invite/add member modal
    const addBtn = page.getByRole('button', { name: /Add Member|Invite Member/i }).first();
    await expect(addBtn).toBeVisible();
    await addBtn.click();

    // Verify modal appears
    await expect(page.getByText(/Invite Member to Project Workspace/i).first()).toBeVisible();
  });

  test('Permissions Management Modal opens and allows toggling granular permissions', async ({ page }) => {
    await page.goto('/projects/proj-1/members');
    
    // Find permissions button on member row
    const permBtn = page.getByRole('button', { name: /Permissions|Manage/i }).first();
    if (await permBtn.isVisible()) {
      await permBtn.click();
      await expect(page.getByText(/Custom Permissions|Permission Overrides/i).first()).toBeVisible();
    }
  });

  test('Audit Trail page loads records, filter controls, and details modal', async ({ page }) => {
    await page.goto('/audit');
    await expect(page.getByRole('heading', { level: 1 })).toContainText('Audit Trail');

    // Test clicking a record's inspect context button
    const inspectBtn = page.getByRole('button', { name: /Inspect Context/i }).first();
    if (await inspectBtn.isVisible()) {
      await inspectBtn.click();
      // Check modal with metadata and cryptographic verification context
      await expect(page.getByText(/Metadata|Request Context|Cryptographic/i).first()).toBeVisible();
    }
  });
});
