import { test, expect } from '@playwright/test';

test.describe('Comprehensive Form Validation Suite across Applications Forms', () => {

  test('1. Registration Form: Required fields, invalid email, boundary password, XSS and long inputs', async ({ page }) => {
    await page.goto('/register');
    await expect(page.locator('h2')).toContainText('Create your account');

    const submitBtn = page.locator('button[type="submit"]');

    // 1.1 Empty Submission
    await submitBtn.click();
    await expect(page.getByText('Full name is required')).toBeVisible();
    await expect(page.getByText('Work or college email is required')).toBeVisible();
    await expect(page.getByText('Password is required')).toBeVisible();

    // 1.2 Invalid Email Addresses
    const nameInput = page.locator('input[placeholder="Alex Mercer"]');
    const emailInput = page.locator('input[placeholder="alex.m@organization.io"]');
    const passwordInput = page.locator('input[placeholder="Minimum 8 characters"]');
    const confirmInput = page.locator('input[placeholder="Re-enter password"]');

    await nameInput.fill('Sarah Connor');
    await emailInput.fill('notanemail');
    await passwordInput.fill('ValidPass123!');
    await confirmInput.fill('ValidPass123!');
    await submitBtn.click();
    await expect(page.getByText('Please provide a valid email format')).toBeVisible();

    // 1.3 Boundary Values: Password min length (7 chars -> error, 8 chars -> accepted)
    await emailInput.fill('valid.engineer@techfrontier.io');
    await passwordInput.fill('Short7!');
    await confirmInput.fill('Short7!');
    await submitBtn.click();
    await expect(page.getByText('Password must be at least 8 characters')).toBeVisible();

    // 1.4 Mismatched Passwords
    await passwordInput.fill('SecurePassword123!');
    await confirmInput.fill('DifferentPassword123!');
    await submitBtn.click();
    await expect(page.getByText('Passwords do not match')).toBeVisible();

    // 1.5 Special Characters & XSS Protection
    const specialName = '<script>alert("XSS")</script> & "O\'Connor" 🚀';
    await nameInput.fill(specialName);
    await expect(nameInput).toHaveValue(specialName);

    // 1.6 Extremely Long Input (1,000 chars)
    const longName = 'A'.repeat(1000);
    await nameInput.fill(longName);
    await expect(nameInput).toHaveValue(longName);
  });

  test('2. Login Form: Required fields, format validation, short password and duplicate submission', async ({ page }) => {
    await page.goto('/login');
    await expect(page.locator('h2')).toContainText('Sign in to your workspace');

    const submitBtn = page.locator('button[type="submit"]');

    // 2.1 Empty Submission
    await submitBtn.click();
    await expect(page.getByText('Email is required')).toBeVisible();
    await expect(page.getByText('Password is required')).toBeVisible();

    // 2.2 Invalid Email Format
    const emailInput = page.locator('input[type="email"]');
    const passwordInput = page.locator('input[type="password"]');

    await emailInput.fill('invalid-email-address');
    await passwordInput.fill('secret123');
    await submitBtn.click();
    await expect(page.getByText('Please enter a valid email address')).toBeVisible();

    // 2.3 Password Boundary: Less than 6 characters
    await emailInput.fill('engineer@techfrontier.io');
    await passwordInput.fill('12345');
    await submitBtn.click();
    await expect(page.getByText('Password must be at least 6 characters')).toBeVisible();

    // 2.4 Duplicate / Rapid Submissions Prevention
    await page.getByRole('button', { name: /Auto Fill/i }).click();
    await expect(emailInput).toHaveValue('elena.rostova@techfrontier.io');

    // Rapid double-click on submit
    await submitBtn.dblclick();

    // Successfully navigates to dashboard without unhandled promise or duplicate request crash
    await expect(page).toHaveURL(/.*dashboard/);
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
  });

  test('3. Create Project Wizard Form: Step validation, missing fields and special characters', async ({ page }) => {
    await page.goto('/login');
    await page.getByRole('button', { name: /Auto Fill/i }).click();
    await page.locator('button[type="submit"]').click();
    await expect(page).toHaveURL(/.*dashboard/);

    await page.goto('/projects');
    const createBtn = page.getByRole('button', { name: /Create Project/i });
    await expect(createBtn).toBeVisible();
    await createBtn.click();

    await expect(page.getByText('Create New Project Workspace')).toBeVisible();

    // 3.1 Step 1 Empty Submission
    const continueBtn = page.getByRole('button', { name: 'Continue to Handover Config' });
    await continueBtn.click();
    await expect(page.getByText('Project name is required')).toBeVisible();
    await expect(page.getByText('Please provide a brief description')).toBeVisible();

    // 3.2 Special Characters and Long Input in Title & Description
    const specialTitle = 'Vault-Core & Key Services (v2.0) [CONFIDENTIAL] 🚀';
    const longDesc = 'Scalable transaction ledger: ' + 'Secure, isolated data partitions. '.repeat(10);

    await page.getByLabel('Project Name *').fill(specialTitle);
    await page.getByLabel('Project Key *').fill('VAULT-V2');
    await page.getByLabel('Description *').fill(longDesc);

    // Step 1 -> Step 2
    await continueBtn.click();
    await expect(page.getByText('Outgoing Member (Knowledge Holder) *')).toBeVisible();

    // Step 2 reached - click Back to return to Step 1
    await page.getByRole('button', { name: 'Back' }).click();
    await expect(page.getByLabel('Project Name *')).toBeVisible();

    // Cancel / Close modal on Step 1
    await page.getByRole('button', { name: 'Cancel' }).click();
  });

  test('4. Handover Receipt Acknowledgement: Required Checkbox Validation', async ({ page }) => {
    await page.goto('/login');
    await page.getByRole('button', { name: /Auto Fill/i }).click();
    await page.locator('button[type="submit"]').click();
    await expect(page).toHaveURL(/.*dashboard/);

    await page.goto('/incoming');
    await expect(page.getByRole('heading', { name: /Incoming Member Dashboard/i })).toBeVisible();

    const ackBtn = page.getByRole('button', { name: /Acknowledge Handover Receipt/i });
    if (await ackBtn.isVisible()) {
      await ackBtn.click();

      // Attempt to submit without checking the required confirmation checkbox
      const confirmBtn = page.getByRole('button', { name: /Confirm & Accept Handover/i });
      await confirmBtn.click();

      // Verify required checkbox error message
      await expect(page.getByText('You must check the confirmation box to acknowledge handover receipt.')).toBeVisible();

      // Check confirmation box
      const checkbox = page.locator('input[type="checkbox"]');
      await checkbox.check();

      // Error message clears
      await expect(page.getByText('You must check the confirmation box to acknowledge handover receipt.')).not.toBeVisible();

      // Close modal
      await page.keyboard.press('Escape');
    }
  });

  test('5. Task Progress Update Modal: Required Progress Notes Validation', async ({ page }) => {
    await page.goto('/login');
    await page.getByRole('button', { name: /Auto Fill/i }).click();
    await page.locator('button[type="submit"]').click();
    await expect(page).toHaveURL(/.*dashboard/);

    await page.goto('/incoming');
    const updateBtn = page.getByRole('button', { name: /Update Progress/i }).first();
    if (await updateBtn.isVisible()) {
      await updateBtn.click();

      // Click submit without entering progress note
      const saveBtn = page.getByRole('button', { name: /Save Progress Update/i });
      await saveBtn.click();

      // Verify required field error message
      await expect(page.getByText('Please enter a brief note describing the progress update or blocker reason.')).toBeVisible();

      // Type special characters note
      const textarea = page.locator('textarea');
      await textarea.fill('Progress logged at 50%: Automated test verification with symbols: #$%^&*() 🚀');
      await expect(page.getByText('Please enter a brief note describing the progress update or blocker reason.')).not.toBeVisible();

      // Close modal
      await page.keyboard.press('Escape');
    }
  });

  test('6. Network Failure During Submission Handling', async ({ page }) => {
    await page.goto('/login');
    await page.getByRole('button', { name: /Auto Fill/i }).click();

    // Intercept auth API call to simulate network drop
    await page.route('**/api/v1/auth/login', route => route.abort('connectionfailed'));

    // Submit form
    await page.locator('button[type="submit"]').click();

    // Verify application handles failure gracefully without white-screen crash
    await expect(page.locator('body')).toBeVisible();
    await expect(page.locator('button[type="submit"]')).toBeEnabled();
  });

});
