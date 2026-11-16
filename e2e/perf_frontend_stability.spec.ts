import { test, expect } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';

interface FrontendPerfMetrics {
  initialLoad: {
    ttfbMs: number;
    domContentLoadedMs: number;
    loadEventMs: number;
    firstContentfulPaintMs: number;
  };
  dashboardLoad: {
    loginToDashboardMs: number;
    dashboardRenderMs: number;
    widgetCount: number;
  };
  projectLoad: {
    navToProjectMs: number;
    status: string;
  };
  versionComparisonView: {
    navToHandoversMs: number;
    status: string;
  };
  navigationStress: {
    cyclesCompleted: number;
    latenciesMs: number[];
    avgLatencyMs: number;
    minLatencyMs: number;
    maxLatencyMs: number;
    p95LatencyMs: number;
  };
  memoryStability: {
    heapStartBytes?: number;
    heapEndBytes?: number;
    heapDeltaBytes?: number;
    heapDeltaMB?: number;
  };
}

test.describe('Frontend Performance & Stability Benchmark', () => {
  const metrics: Partial<FrontendPerfMetrics> = {};

  test('Measure Initial Page Load and Paint Performance', async ({ page }) => {
    // Cold load
    await page.goto('/login', { waitUntil: 'load' });

    // Measure warm load on reload
    await page.reload({ waitUntil: 'load' });

    // Query Performance API for precise W3C Navigation Timing
    const perfTiming = await page.evaluate(() => {
      const navEntries = performance.getEntriesByType('navigation') as PerformanceNavigationTiming[];
      const paintEntries = performance.getEntriesByType('paint');
      const fcp = paintEntries.find((e) => e.name === 'first-contentful-paint');

      if (navEntries.length > 0) {
        const nav = navEntries[0];
        return {
          ttfb: nav.responseStart - nav.requestStart,
          domContentLoaded: nav.domContentLoadedEventEnd - nav.startTime,
          loadEvent: nav.loadEventEnd - nav.startTime,
          fcp: fcp ? fcp.startTime : nav.responseEnd - nav.startTime,
        };
      }
      return {
        ttfb: 0,
        domContentLoaded: 0,
        loadEvent: 0,
        fcp: 0,
      };
    });

    metrics.initialLoad = {
      ttfbMs: Math.round(perfTiming.ttfb * 100) / 100,
      domContentLoadedMs: Math.round(perfTiming.domContentLoaded * 100) / 100,
      loadEventMs: Math.round(perfTiming.loadEvent * 100) / 100,
      firstContentfulPaintMs: Math.round(perfTiming.fcp * 100) / 100,
    };

    console.log(`[PERF] Initial Page Load (Warm): TTFB=${metrics.initialLoad.ttfbMs}ms, DCL=${metrics.initialLoad.domContentLoadedMs}ms, Load=${metrics.initialLoad.loadEventMs}ms, FCP=${metrics.initialLoad.firstContentfulPaintMs}ms`);

    expect(metrics.initialLoad.loadEventMs).toBeGreaterThan(0);
    expect(metrics.initialLoad.loadEventMs).toBeLessThan(3000); // Strict threshold < 3.0s on warm load
  });

  test('Measure Dashboard Loading Time & Component Hydration', async ({ page }) => {
    await page.goto('/login');
    const autoFillBtn = page.getByRole('button', { name: /Auto Fill/i });
    await expect(autoFillBtn).toBeVisible();
    await autoFillBtn.click();

    const tStart = Date.now();
    await page.locator('button[type="submit"]').click();
    await expect(page).toHaveURL(/.*dashboard/);
    const tUrl = Date.now();

    // Wait until key dashboard metrics / widgets are fully visible
    const h1 = page.getByRole('heading', { level: 1 });
    await expect(h1).toBeVisible();
    const searchInput = page.locator('input[placeholder*="Search"]').first();
    await expect(searchInput).toBeVisible();
    const tRender = Date.now();

    const widgets = await page.locator('.metric-card, .dashboard-widget, [class*="card"]').count();

    metrics.dashboardLoad = {
      loginToDashboardMs: tUrl - tStart,
      dashboardRenderMs: tRender - tStart,
      widgetCount: widgets,
    };

    console.log(`[PERF] Dashboard Load: Transition=${metrics.dashboardLoad.loginToDashboardMs}ms, Full Render=${metrics.dashboardLoad.dashboardRenderMs}ms, Widgets=${widgets}`);

    expect(metrics.dashboardLoad.dashboardRenderMs).toBeLessThan(3000); // Strict threshold < 3.0s
  });

  test('Measure Project Workspace Loading Time & Viewport Rendering', async ({ page }) => {
    await page.goto('/login');
    await page.getByRole('button', { name: /Auto Fill/i }).click();
    await page.locator('button[type="submit"]').click();
    await expect(page).toHaveURL(/.*dashboard/);

    const tStart = Date.now();
    await page.goto('/projects');
    await expect(page).toHaveURL(/.*projects/);
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
    const tRender = Date.now();

    metrics.projectLoad = {
      navToProjectMs: tRender - tStart,
      status: 'PASSED',
    };
    console.log(`[PERF] Project Workspace Load: Full Render=${metrics.projectLoad.navToProjectMs}ms`);
    expect(metrics.projectLoad.navToProjectMs).toBeLessThan(3000);
  });

  test('Measure Handover & Version Comparison View Loading', async ({ page }) => {
    await page.goto('/login');
    await page.getByRole('button', { name: /Auto Fill/i }).click();
    await page.locator('button[type="submit"]').click();
    await expect(page).toHaveURL(/.*dashboard/);

    const tStart = Date.now();
    await page.goto('/handovers');
    await expect(page).toHaveURL(/.*handovers/);
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
    const tRender = Date.now();

    metrics.versionComparisonView = {
      navToHandoversMs: tRender - tStart,
      status: 'PASSED',
    };
    console.log(`[PERF] Handover & Version View Load: Render=${metrics.versionComparisonView.navToHandoversMs}ms`);
    expect(metrics.versionComparisonView.navToHandoversMs).toBeLessThan(3000);
  });

  test('Stress Test: Repeated Route Transitions & Memory Stability', async ({ page }) => {
    // Authenticate
    await page.goto('/login');
    await page.getByRole('button', { name: /Auto Fill/i }).click();
    await page.locator('button[type="submit"]').click();
    await expect(page).toHaveURL(/.*dashboard/);

    // Initial heap measurement
    const initialHeap = await page.evaluate(() => {
      // @ts-ignore
      return (window.performance && window.performance.memory) ? window.performance.memory.usedJSHeapSize : null;
    });

    const routes = ['/dashboard', '/projects', '/documents', '/handovers', '/incoming'];
    const latencies: number[] = [];
    const numCycles = 3; // 3 cycles across 5 routes = 15 rapid transitions

    const pageErrors: string[] = [];
    page.on('pageerror', (err) => pageErrors.push(err.message));

    for (let c = 0; c < numCycles; c++) {
      for (const route of routes) {
        const t0 = Date.now();
        await page.goto(route, { waitUntil: 'domcontentloaded' });
        await page.waitForLoadState('networkidle');
        const elapsed = Date.now() - t0;
        latencies.push(elapsed);
      }
    }

    // Final heap measurement
    const finalHeap = await page.evaluate(() => {
      // @ts-ignore
      return (window.performance && window.performance.memory) ? window.performance.memory.usedJSHeapSize : null;
    });

    latencies.sort((a, b) => a - b);
    const sum = latencies.reduce((acc, v) => acc + v, 0);
    const avg = Math.round(sum / latencies.length);
    const min = latencies[0];
    const max = latencies[latencies.length - 1];
    const p95 = latencies[Math.floor(latencies.length * 0.95)];

    const heapDelta = (finalHeap && initialHeap) ? finalHeap - initialHeap : undefined;
    const heapDeltaMB = heapDelta ? Math.round((heapDelta / (1024 * 1024)) * 100) / 100 : undefined;

    metrics.navigationStress = {
      cyclesCompleted: numCycles * routes.length,
      latenciesMs: latencies,
      avgLatencyMs: avg,
      minLatencyMs: min,
      maxLatencyMs: max,
      p95LatencyMs: p95,
    };

    metrics.memoryStability = {
      heapStartBytes: initialHeap || undefined,
      heapEndBytes: finalHeap || undefined,
      heapDeltaBytes: heapDelta,
      heapDeltaMB: heapDeltaMB,
    };

    console.log(`[PERF] Navigation Stress (15 transitions): Avg=${avg}ms, Min=${min}ms, Max=${max}ms, p95=${p95}ms, HeapDelta=${heapDeltaMB ?? 'N/A'}MB`);

    // Ensure no unhandled exceptions occurred
    expect(pageErrors.length).toBe(0);

    // Save metrics JSON to disk
    const outDir = path.resolve('test-results');
    if (!fs.existsSync(outDir)) {
      fs.mkdirSync(outDir, { recursive: true });
    }
    fs.writeFileSync(
      path.join(outDir, 'frontend_perf_metrics.json'),
      JSON.stringify(metrics, null, 2),
      'utf-8'
    );
  });
});
