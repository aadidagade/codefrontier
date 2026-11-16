import { test, expect } from '@playwright/test';

test.describe('2-4. Dashboard, Projects & Project Workspace', () => {
  test.beforeEach(async ({ page }) => {
    // Log in via demo account first
    await page.goto('/login');
    await page.getByRole('button', { name: /Auto Fill/i }).click();
    await page.locator('button[type="submit"]').click();
    await expect(page).toHaveURL(/.*dashboard/);
  });

  test('Dashboard loads metrics, greeting, and project list', async ({ page }) => {
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
    // Search input exists and filters projects
    const searchInput = page.locator('input[placeholder*="Search"]').first();
    await expect(searchInput).toBeVisible();
    await searchInput.fill('Global');
    await expect(page.getByText(/Payment|Orchestration/i).first()).toBeVisible();
  });

  test('Projects page opens and creates a new project via wizard', async ({ page }) => {
    await page.goto('/projects');
    await expect(page.getByRole('heading', { name: /Projects/i })).toBeVisible();

    // Click "Create Project" button
    const createBtn = page.getByRole('button', { name: /Create Project/i });
    await expect(createBtn).toBeVisible();
    await createBtn.click();

    // Verify Wizard Modal opens
    await expect(page.getByText('Create New Project Workspace')).toBeVisible();

    // Step 1: Fill in project details (name, key, and description)
    await page.getByLabel('Project Name *').fill('Quantum Ledger Engine');
    await page.getByLabel('Project Key *').fill('QLE-CORE');
    await page.getByLabel('Description *').fill('High-throughput distributed ledger service for multi-region settlements.');

    // Step 1 -> Step 2
    await page.getByRole('button', { name: 'Continue to Handover Config' }).click();

    // Step 2 -> Step 3
    await page.getByRole('button', { name: 'Continue to Permissions' }).click();

    // Step 3 -> Step 4
    await page.getByRole('button', { name: 'Continue to Review & Create' }).click();

    // Step 4: Create Workspace
    await page.getByRole('button', { name: 'Create Workspace' }).click();

    // Should redirect to project workspace
    await expect(page).toHaveURL(/.*projects\/.+/);
  });

  test('Project workspace loads tabs and project details', async ({ page }) => {
    await page.goto('/projects/proj-1');
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible();

    // Check workspace tabs (e.g. Overview, Members, Documents, Handovers, Audit)
    const membersLink = page.getByRole('link', { name: /Members/i }).first();
    if (await membersLink.isVisible()) {
      await membersLink.click();
      await expect(page).toHaveURL(/.*members/);
    }
  });
});
