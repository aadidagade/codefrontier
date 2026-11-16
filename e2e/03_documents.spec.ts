import { test, expect } from '@playwright/test';

test.describe('5-6. Document Upload, List & Preview', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
    await page.getByRole('button', { name: /Auto Fill/i }).click();
    await page.locator('button[type="submit"]').click();
    await expect(page).toHaveURL(/.*dashboard/);
  });

  test('Documents page displays document list and search works', async ({ page }) => {
    await page.goto('/knowledge-sources');
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible();

    // Verify document table exists
    const docRow = page.locator('tbody tr').first();
    await expect(docRow).toBeVisible();

    // Test search filter
    const searchInput = page.locator('input[placeholder*="Search" i]').first();
    await searchInput.fill('Architecture');
    await expect(page.locator('tbody tr').first()).toBeVisible();
  });

  test('Clicking a document opens preview drawer with details and chunks', async ({ page }) => {
    await page.goto('/knowledge-sources');
    
    // Click on the first document row
    const firstRow = page.locator('tbody tr').first();
    await firstRow.click();

    // Verify DocumentDetailsDrawer opened
    const drawerTitle = page.locator('h2, h3').filter({ hasText: /\.(pdf|md|docx|txt)/i }).first();
    await expect(drawerTitle).toBeVisible();
    
    // Verify AST chunks or preview content is displayed
    await expect(page.getByText(/AST|Chunk|Extraction|Metadata/i).first()).toBeVisible();
  });

  test('File upload input is available in the dropzone', async ({ page }) => {
    await page.goto('/knowledge-sources');
    
    // Check hidden file input
    const fileInput = page.locator('input[type="file"]');
    await expect(fileInput).toBeAttached();
  });
});
