import { test, expect } from '@playwright/test';

const VIEWPORTS = [
  { name: 'Mobile (375x812)', width: 375, height: 812 },
  { name: 'Mobile (390x844)', width: 390, height: 844 },
  { name: 'Tablet (768x1024)', width: 768, height: 1024 },
  { name: 'Laptop (1366x768)', width: 1366, height: 768 },
  { name: 'Desktop (1920x1080)', width: 1920, height: 1080 },
];

const PAGES_TO_TEST = [
  { name: 'Dashboard', path: '/dashboard' },
  { name: 'Project Workspace', path: '/projects/proj-alpha-001' },
  { name: 'Upload & Documents', path: '/documents' },
  { name: 'Handover Review Details', path: '/review/handover-session-001' },
  { name: 'Evidence Verification', path: '/verification' },
  { name: 'Audit Logs', path: '/audit' },
  { name: 'Version History', path: '/handovers/handover-session-001/versions' },
  { name: 'Incoming Member Dashboard', path: '/incoming' },
];

test.describe('Responsive & Viewport Diagnostics', () => {
  test.beforeEach(async ({ page }) => {
    // Inject auth session directly for instant loading
    await page.addInitScript(() => {
      const session = {
        user: {
          id: 'usr-001',
          name: 'Dr. Elena Rostova',
          email: 'elena.rostova@techfrontier.io',
          role: 'Project Lead',
          avatarUrl: 'https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=150',
          initials: 'ER',
          department: 'AI Systems Engineering',
        },
        token: 'kh_jwt_mock_test_token',
        expiresAt: new Date(Date.now() + 86400 * 1000 * 7).toISOString(),
      };
      localStorage.setItem('kh_auth_session', JSON.stringify(session));
      localStorage.setItem('kh_auth_token', session.token);
    });
  });

  // Test all 8 pages across all 5 viewports (40 combinations)
  for (const vp of VIEWPORTS) {
    test.describe(`Viewport: ${vp.name}`, () => {
      for (const p of PAGES_TO_TEST) {
        test(`Page: ${p.name} - checks overflow, layout, tables & buttons`, async ({ page }) => {
          await page.setViewportSize({ width: vp.width, height: vp.height });
          await page.goto(p.path);
          await page.waitForLoadState('domcontentloaded');
          await page.waitForTimeout(400); // Allow layout recalculation

          // 1. Check for horizontal overflow on document root and main container
          const overflowInfo = await page.evaluate(() => {
            const docWidth = document.documentElement.clientWidth;
            const docScroll = document.documentElement.scrollWidth;
            const main = document.querySelector('main');
            const mainScroll = main ? main.scrollWidth : 0;
            const mainClient = main ? main.clientWidth : 0;

            const overflowingElements: { tag: string; id: string; className: string; right: number; width: number }[] = [];
            document.querySelectorAll('*').forEach((el) => {
              const rect = el.getBoundingClientRect();
              const style = window.getComputedStyle(el);
              if (style.display === 'none' || style.visibility === 'hidden' || style.position === 'fixed') {
                return;
              }
              if (rect.right > docWidth + 3 && rect.width > 0) {
                overflowingElements.push({
                  tag: el.tagName.toLowerCase(),
                  id: el.id,
                  className: el.className ? String(el.className).substring(0, 80) : '',
                  right: Math.round(rect.right),
                  width: Math.round(rect.width),
                });
              }
            });

            return {
              docWidth,
              docScroll,
              docOverflow: docScroll > docWidth + 2,
              mainClient,
              mainScroll,
              mainOverflow: mainScroll > mainClient + 2,
              overflowCount: overflowingElements.length,
              sampleOverflows: overflowingElements.slice(0, 5),
            };
          });

          if (overflowInfo.docOverflow || overflowInfo.mainOverflow) {
            console.log(`[OVERFLOW] ${vp.name} on ${p.name}:`, JSON.stringify(overflowInfo));
          }

          // 2. Navigation check: on mobile/tablet (< 1024), check hamburger menu button
          if (vp.width < 1024) {
            const hamburger = page.locator('button[aria-label="Toggle Navigation"]');
            await expect(hamburger).toBeVisible();
          }

          // 3. Table responsiveness: check all tables are wrapped in an overflow container
          const tableStatus = await page.evaluate((vpWidth) => {
            const tables = Array.from(document.querySelectorAll('table'));
            return tables.map((t) => {
              let parent = t.parentElement;
              let hasScroll = false;
              while (parent && parent !== document.body) {
                const overflowX = window.getComputedStyle(parent).overflowX;
                if (overflowX === 'auto' || overflowX === 'scroll') {
                  hasScroll = true;
                  break;
                }
                parent = parent.parentElement;
              }
              const tableWidth = Math.round(t.getBoundingClientRect().width);
              return {
                tableWidth,
                hasScrollParent: hasScroll,
                isOverflowingUnwrapped: !hasScroll && tableWidth > vpWidth,
              };
            });
          }, vp.width);

          for (const ts of tableStatus) {
            expect(ts.isOverflowingUnwrapped, `Table exceeds viewport width without scroll wrapper on ${p.name} at ${vp.name}`).toBe(false);
          }

          // 4. Assert neither root document nor main container causes page-level horizontal overflow
          expect(overflowInfo.docOverflow, `Root document horizontal overflow on ${p.name} at ${vp.name}`).toBe(false);
          expect(overflowInfo.mainOverflow, `Main container horizontal overflow on ${p.name} at ${vp.name}`).toBe(false);
        });
      }
    });
  }

  // Mobile Navigation Drawer Interaction Test
  test('Mobile Navigation: Hamburger opens sidebar drawer and backdrop closes it', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 812 });
    await page.goto('/dashboard');

    const hamburger = page.locator('button[aria-label="Toggle Navigation"]');
    await expect(hamburger).toBeVisible();

    // Initially sidebar is offscreen on mobile
    const aside = page.locator('aside');
    await expect(aside).toHaveClass(/.*-translate-x-full.*/);

    // Click hamburger to open
    await hamburger.click();
    await page.waitForTimeout(350);

    // Verify sidebar slid in
    await expect(aside).toHaveClass(/.*translate-x-0.*/);

    // Verify backdrop is visible and click it to close
    const backdrop = page.locator('.fixed.inset-0.z-40.bg-black\\/60');
    await expect(backdrop).toBeVisible();
    await backdrop.click({ position: { x: 350, y: 100 } });
    await page.waitForTimeout(350);

    // Verify sidebar is dismissed
    await expect(aside).toHaveClass(/.*-translate-x-full.*/);
  });

  // Modal Responsiveness on Mobile Viewport (375x812)
  test('Modal Responsiveness: Version Comparison Modal fits mobile viewport without cut-off', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 812 });
    await page.goto('/handovers/handover-session-001/versions');

    // Click Compare Versions
    const compareBtn = page.getByRole('button', { name: /Compare Versions/i });
    await expect(compareBtn).toBeVisible();
    await compareBtn.click();

    // Verify modal is visible
    const modalHeading = page.getByText('Version Comparison Engine');
    await expect(modalHeading).toBeVisible();

    // Check modal height does not exceed viewport height
    const modalBox = await page.locator('.fixed.z-50 .relative.w-full.max-w-6xl').boundingBox();
    expect(modalBox).not.toBeNull();
    if (modalBox) {
      expect(modalBox.height).toBeLessThanOrEqual(812);
      expect(modalBox.width).toBeLessThanOrEqual(375);
    }
  });

  test('Modal Responsiveness: Handover Acknowledgement Modal fits mobile viewport', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 812 });
    await page.goto('/incoming');

    // Click Acknowledge Receipt
    const ackBtn = page.getByRole('button', { name: /Acknowledge Receipt/i }).first();
    await expect(ackBtn).toBeVisible();
    await ackBtn.click();

    // Check modal dialog
    const modalHeading = page.getByRole('heading', { name: /Acknowledge Handover Receipt/i });
    await expect(modalHeading).toBeVisible();

    const modalBox = await page.locator('.fixed.z-50 .relative.w-full.max-w-lg').boundingBox();
    expect(modalBox).not.toBeNull();
    if (modalBox) {
      expect(modalBox.height).toBeLessThanOrEqual(812);
      expect(modalBox.width).toBeLessThanOrEqual(375);
    }
  });

  test('Modal Responsiveness: Task Progress Update Modal fits mobile viewport', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 812 });
    await page.goto('/incoming');

    // Click "Filter Tasks" on the acknowledged handover (Real-Time Fraud Prevention) to select it
    const filterBtn = page.getByRole('button', { name: 'Filter Tasks' }).first();
    await expect(filterBtn).toBeVisible();
    await filterBtn.click();
    await page.waitForTimeout(400);

    // Now in Section 3, click "Update"
    const updateBtn = page.getByRole('button', { name: /^Update$/i }).first();
    await expect(updateBtn).toBeVisible();
    await updateBtn.click();

    const modalHeading = page.getByRole('heading', { name: /Log Task Progress & Status Update/i });
    await expect(modalHeading).toBeVisible();

    const modalBox = await page.locator('.fixed.z-50 .relative.w-full.max-w-lg').boundingBox();
    expect(modalBox).not.toBeNull();
    if (modalBox) {
      expect(modalBox.height).toBeLessThanOrEqual(812);
      expect(modalBox.width).toBeLessThanOrEqual(375);
    }
  });
});
