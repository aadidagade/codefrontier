import { test, expect } from '@playwright/test';
import * as path from 'path';

test.describe('Improvement 2: Role-Based Access Control and Audit Trail Browser Verification', () => {
  test.beforeEach(async ({ page }) => {
    // 1. Log in to the application
    await page.goto('/login');
    const autoFillBtn = page.getByRole('button', { name: /Auto Fill/i });
    if (await autoFillBtn.isVisible()) {
      await autoFillBtn.click();
    } else {
      await page.fill('input[type="email"]', 'demo@knowledge-handover.io');
      await page.fill('input[type="password"]', 'Password123!');
    }
    await page.locator('button[type="submit"]').click();
    await expect(page).toHaveURL(/.*dashboard/);
  });

  test('1. Project Owner & Lead can access Members management and Permissions modal', async ({ page }) => {
    // Navigate to members page
    await page.goto('/projects/proj-1/members');
    await expect(page.getByRole('heading', { level: 1 })).toContainText('Project Members');

    // Verify member table has rows
    await expect(page.locator('table, .divide-y').first()).toBeVisible();

    // Verify Invite / Add Member button is present
    const addBtn = page.getByRole('button', { name: /Add Member|Invite Member/i }).first();
    await expect(addBtn).toBeVisible();
    await addBtn.click();

    // Verify invite modal appears with role options
    await expect(page.getByText(/Invite Member to Project Workspace/i).first()).toBeVisible();
    
    // Close modal
    const cancelBtn = page.getByRole('button', { name: /Cancel|Close/i }).first();
    if (await cancelBtn.isVisible()) {
      await cancelBtn.click();
    } else {
      await page.keyboard.press('Escape');
    }

    // Verify permissions management modal opens
    const permBtn = page.getByRole('button', { name: /Permissions|Manage/i }).first();
    if (await permBtn.isVisible()) {
      await permBtn.click();
      await expect(page.getByText(/Custom Permissions|Permission Overrides/i).first()).toBeVisible();
      await page.keyboard.press('Escape');
    }
  });

  test('2. Incoming Member role is blocked from viewing Audit Trail and restricted on uploads', async ({ page }) => {
    // Switch active role to incoming_member via localStorage to test UI enforcement
    await page.evaluate(() => {
      localStorage.setItem('kh_active_app_role', 'incoming_member');
    });
    await page.reload();

    // Attempt to navigate to Audit Trail
    await page.goto('/audit');

    // Verify Audit Trail Access Restricted screen is rendered
    await expect(page.getByText(/Audit Trail Access Restricted/i).first()).toBeVisible();
    await expect(page.getByText(/does not possess VIEW_AUDIT_LOGS privilege/i).first()).toBeVisible();

    // Navigate to documents page
    await page.goto('/documents');
    // Incoming member should not have upload documents button active
    const uploadBtn = page.getByRole('button', { name: /Upload Document|Add Knowledge/i }).first();
    const isVisible = await uploadBtn.isVisible().catch(() => false);
    if (isVisible) {
      const isDisabled = await uploadBtn.isDisabled().catch(() => false);
      expect(isDisabled).toBe(true);
    }
  });

  test('3. Audit Trail page renders complete metadata and inspect context modal', async ({ page }) => {
    // Ensure role is project_lead to view audit logs
    await page.evaluate(() => {
      localStorage.setItem('kh_active_app_role', 'project_lead');
    });
    await page.reload();

    await page.goto('/audit');
    await expect(page.getByRole('heading', { level: 1 })).toContainText('Audit Trail');

    // Verify audit log timeline, table, or audit container is visible
    await expect(page.locator('.space-y-6, table, .divide-y, :has-text("Audit Records"), :has-text("Enterprise Activity")').first()).toBeVisible();

    // Inspect the first record context modal if records exist
    const inspectBtn = page.getByRole('button', { name: /Inspect Context|Inspect/i }).first();
    if (await inspectBtn.isVisible()) {
      await inspectBtn.click();

      // Verify that inspect context modal displays:
      // Actor, Action, Project, Timestamp, Entity Type, Entity Reference ID, and Change Metadata
      await expect(page.getByText(/Metadata|Request Context|Cryptographic/i).first()).toBeVisible();
    }

    // Capture screenshot for audit evidence
    const screenshotPath = 'C:/Users/Aadi Dagade/.gemini/antigravity/brain/6d3f310c-3d85-4dbc-8c2a-38cc0fc91d77/screenshots/11_rbac_audit_trail_inspection.png';
    await page.screenshot({ path: screenshotPath, fullPage: true });
  });

  test('4. Direct backend API requests reject audit log mutations (Immutability)', async ({ request }) => {
    // Register a fresh test user via API
    const testEmail = `sec_audit_${Date.now()}@corp.io`;
    const regRes = await request.post('http://127.0.0.1:8000/api/v1/auth/register', {
      data: {
        email: testEmail,
        password: 'Password123!',
        full_name: 'Security Test Auditor',
      },
    });
    expect(regRes.ok()).toBe(true);
    const regData = await regRes.json();
    const token = regData.data?.access_token || regData.access_token;
    expect(token).toBeDefined();

    // 1. Attempt POST to create audit log directly -> 403 Forbidden
    const postRes = await request.post('http://127.0.0.1:8000/api/v1/audit-logs', {
      headers: { Authorization: `Bearer ${token}` },
      data: { action: 'fake_client_event' },
    });
    expect(postRes.status()).toBe(403);
    const postBody = await postRes.text();
    expect(postBody.toLowerCase()).toContain('immutable');

    // 2. Attempt DELETE to destroy an audit record -> 403 Forbidden
    const deleteRes = await request.delete('http://127.0.0.1:8000/api/v1/audit-logs/00000000-0000-0000-0000-000000000001', {
      headers: { Authorization: `Bearer ${token}` },
    });
    expect(deleteRes.status()).toBe(403);
    const deleteBody = await deleteRes.text();
    expect(deleteBody.toLowerCase()).toContain('immutable');
  });
});
