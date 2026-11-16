import { test, expect } from '@playwright/test';

test.describe('1. Authentication & Registration', () => {
  test('Form validation and error messages on empty login', async ({ page }) => {
    await page.goto('/login');
    await expect(page.locator('h2')).toContainText('Sign in to your workspace');

    // Attempt submitting empty form
    await page.locator('button[type="submit"]').click();
    await expect(page.getByText('Email is required')).toBeVisible();
    await expect(page.getByText('Password is required')).toBeVisible();
  });

  test('Demo Auto Fill and successful login to dashboard', async ({ page }) => {
    await page.goto('/login');
    // Click demo fill button
    const autoFillBtn = page.getByRole('button', { name: /Auto Fill/i });
    await expect(autoFillBtn).toBeVisible();
    await autoFillBtn.click();

    // Verify inputs populated
    await expect(page.locator('input[type="email"]')).toHaveValue('elena.rostova@techfrontier.io');

    // Submit form
    await page.locator('button[type="submit"]').click();

    // Verify redirection to dashboard
    await expect(page).toHaveURL(/.*dashboard/);
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
  });

  test('Registration page loads with form validation', async ({ page }) => {
    await page.goto('/register');
    await expect(page.locator('h2')).toContainText('Create your account');

    // Submit without input
    await page.locator('button[type="submit"]').click();
    await expect(page.getByText(/Full name is required|Name is required/i)).toBeVisible();
  });
});
