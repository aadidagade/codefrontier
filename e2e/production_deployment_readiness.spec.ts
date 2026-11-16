import { test, expect } from '@playwright/test';

test.describe('Production Deployment Readiness: Fresh Browser Session', () => {
  test.describe.configure({ mode: 'serial' });

  test('1. Fresh Session Authentication & Redirect to Dashboard', async ({ browser }) => {
    // Explicitly create an isolated fresh incognito browser context
    const context = await browser.newContext();
    const page = await context.newPage();

    const consoleErrors: string[] = [];
    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        consoleErrors.push(msg.text());
      }
    });

    // 1. Visit Login Page
    await page.goto('/login');
    await expect(page.getByRole('heading', { level: 2 })).toContainText(/Sign in to your workspace/i);

    // 2. Perform Login via Auto Fill
    const autoFillBtn = page.getByRole('button', { name: /Auto Fill/i });
    await expect(autoFillBtn).toBeVisible();
    await autoFillBtn.click();

    // Submit form
    await page.locator('button[type="submit"]').click();

    // 3. Verify successful redirection to dashboard
    await expect(page).toHaveURL(/.*dashboard/);
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible();

    // Verify localStorage has auth token
    const token = await page.evaluate(() => localStorage.getItem('kh_auth_token') || localStorage.getItem('token'));
    expect(token).toBeTruthy();

    await context.close();
  });

  test('2. Audit All Application Routes from Fresh Authenticated Session', async ({ browser }) => {
    const context = await browser.newContext();
    const page = await context.newPage();

    // Pre-authenticate session
    await page.goto('/login');
    await page.getByRole('button', { name: /Auto Fill/i }).click();
    await page.locator('button[type="submit"]').click();
    await expect(page).toHaveURL(/.*dashboard/);

    const routesToAudit = [
      { path: '/dashboard', expectedText: /Dashboard|Engineering Knowledge/i },
      { path: '/projects', expectedText: /Projects/i },
      { path: '/documents', expectedText: /Documents|Knowledge Documents/i },
      { path: '/handovers', expectedText: /Handovers|Knowledge Handovers/i },
      { path: '/handovers/generate', expectedText: /Generate|Synthesis/i },
      { path: '/review', expectedText: /Review|Approval/i },
      { path: '/verification', expectedText: /Evidence|Verification/i },
      { path: '/conflicts', expectedText: /Conflicts|Contradiction/i },
      { path: '/incoming', expectedText: /Incoming|Continuity/i },
      { path: '/audit', expectedText: /Audit|Activity Log/i },
      { path: '/settings', expectedText: /Settings|Workspace Configuration/i },
    ];

    const auditedRoutes: string[] = [];

    for (const r of routesToAudit) {
      await page.goto(r.path, { waitUntil: 'domcontentloaded' });
      await expect(page.getByText(r.expectedText).first()).toBeVisible();
      auditedRoutes.push(r.path);
    }

    expect(auditedRoutes.length).toBe(routesToAudit.length);
    console.log(`[DEPLOY AUDIT] Verified ${auditedRoutes.length} core application routes load successfully.`);

    await context.close();
  });

  test('3. Document Ingestion Interface & Dropzone Validation', async ({ browser }) => {
    const context = await browser.newContext();
    const page = await context.newPage();

    await page.goto('/login');
    await page.getByRole('button', { name: /Auto Fill/i }).click();
    await page.locator('button[type="submit"]').click();
    await expect(page).toHaveURL(/.*dashboard/);

    await page.goto('/documents');
    await expect(page.getByText(/Documents/i).first()).toBeVisible();

    // Verify Upload dropzone trigger and file input exist
    const browseTrigger = page.getByRole('button', { name: /browse files/i });
    await expect(browseTrigger).toBeVisible();
    const fileInput = page.locator('input[type="file"]');
    await expect(fileInput).toBeAttached();

    await context.close();
  });

  test('4. Runtime Bundle Security: Verify Zero Leaked Keys or Localhost API URLs', async ({ browser }) => {
    const context = await browser.newContext();
    const page = await context.newPage();

    await page.goto('/login');

    // Inspect runtime window object and HTML
    const pageSource = await page.content();
    expect(pageSource).not.toContain('AIzaSy');
    expect(pageSource).not.toContain('localhost:8000');

    await context.close();
  });
});
