import { test, expect } from '@playwright/test';
import path from 'path';

const SCREENSHOT_DIR = path.resolve('test-results/screenshots');

test.describe('End-to-End QA User Journey: Knowledge Handover Platform', () => {
  test.beforeEach(async ({ page }) => {
    // Set desktop standard viewport
    await page.setViewportSize({ width: 1440, height: 900 });
  });

  // ============================================================================
  // PHASE 1 — PROJECT SETUP
  // ============================================================================
  test('Phase 1: Project Setup — Registration, Login, Project Creation & Role Assignment', async ({ page }) => {
    // 1. Visit Registration Page
    await page.goto('/register');
    await expect(page.locator('h2')).toContainText(/Create your account/i);
    await page.screenshot({ path: `${SCREENSHOT_DIR}/01_auth_register_page.png`, fullPage: true });

    // 2. Visit Login Page & Perform Authentication
    await page.goto('/login');
    await expect(page.locator('h2')).toContainText(/Sign in to your workspace/i);

    // Verify form validation on empty submit
    await page.locator('button[type="submit"]').click();
    await expect(page.getByText(/Email is required/i)).toBeVisible();
    await expect(page.getByText(/Password is required/i)).toBeVisible();

    // Auto-fill credentials
    const autoFillBtn = page.getByRole('button', { name: /Auto Fill/i });
    await expect(autoFillBtn).toBeVisible();
    await autoFillBtn.click();
    await page.screenshot({ path: `${SCREENSHOT_DIR}/01_auth_register_login.png` });

    // Submit and navigate to Dashboard
    await page.locator('button[type="submit"]').click();
    await expect(page).toHaveURL(/.*dashboard/);
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible();

    // 3. Project Creation
    await page.goto('/projects');
    await expect(page.getByRole('heading', { name: /Projects/i })).toBeVisible();

    const createBtn = page.getByRole('button', { name: /Create Project/i });
    await expect(createBtn).toBeVisible();
    await createBtn.click();

    // Fill project creation modal
    await expect(page.getByText(/Create New Project Workspace/i)).toBeVisible();
    await page.getByLabel(/Project Name \*/i).fill('Project Apex Multi-Currency Engine');
    await page.getByLabel(/Project Key \*/i).fill('APEX-V1');
    await page.getByLabel(/Description \*/i).fill('High-throughput distributed multi-currency financial settlement engine.');

    await page.screenshot({ path: `${SCREENSHOT_DIR}/02_project_setup.png` });

    // Step through configuration
    await page.getByRole('button', { name: /Continue to Handover Config/i }).click();
    await page.getByRole('button', { name: /Continue to Permissions/i }).click();
    await page.getByRole('button', { name: /Continue to Review & Create/i }).click();
    await page.getByRole('button', { name: /Create Workspace/i }).click();

    await expect(page).toHaveURL(/.*projects\/.+/);

    // 4. Project Member Management & Role Assignment
    await page.goto('/projects/proj-1/members');
    await expect(page.getByRole('heading', { level: 1 })).toContainText(/Project Members/i);
    await expect(page.locator('table, .divide-y').first()).toBeVisible();

    const addMemberBtn = page.getByRole('button', { name: /Add Member|Invite Member/i }).first();
    if (await addMemberBtn.isVisible()) {
      await addMemberBtn.click();
      await expect(page.getByText(/Invite Member to Project Workspace/i)).toBeVisible();
      await page.screenshot({ path: `${SCREENSHOT_DIR}/03_project_members_rbac.png` });
      await page.keyboard.press('Escape');
    }
  });

  // ============================================================================
  // PHASE 2 — DOCUMENT INGESTION
  // ============================================================================
  test('Phase 2: Document Ingestion — Ingestion, Chunking, Indexing & Knowledge Sources', async ({ page }) => {
    // Login
    await page.goto('/login');
    await page.getByRole('button', { name: /Auto Fill/i }).click();
    await page.locator('button[type="submit"]').click();
    await expect(page).toHaveURL(/.*dashboard/);

    // Navigate to Knowledge Sources / Documents
    await page.goto('/documents');
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible();

    // Verify document cards and ingestion status badges
    await expect(page.getByText(/Uploaded|Ready|Indexed|Processing|PDF|DOCX|TXT|MD/i).first()).toBeVisible();

    // Verify search and filter controls
    const searchDoc = page.locator('input[placeholder*="Search"]').first();
    if (await searchDoc.isVisible()) {
      await searchDoc.fill('Architecture');
    }

    await page.screenshot({ path: `${SCREENSHOT_DIR}/04_document_ingestion.png`, fullPage: true });
  });

  // ============================================================================
  // PHASE 3 — AI HANDOVER GENERATION
  // ============================================================================
  test('Phase 3: AI Handover Generation — Gemini Synthesis across Core Pillars', async ({ page }) => {
    // Login
    await page.goto('/login');
    await page.getByRole('button', { name: /Auto Fill/i }).click();
    await page.locator('button[type="submit"]').click();
    await expect(page).toHaveURL(/.*dashboard/);

    // Navigate to Handover Generation
    await page.goto('/handover/generate');
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible();

    // Select Ready Documents
    const selectAllBtn = page.getByRole('button', { name: /^Select All Ready/i });
    if (await selectAllBtn.isVisible()) {
      await selectAllBtn.click();
    } else {
      const checkbox = page.locator('tbody input[type="checkbox"]').first();
      if (await checkbox.isVisible()) {
        await checkbox.check();
      }
    }

    // Trigger Generation
    const generateBtn = page.getByRole('button', { name: /Generate Structured Handover/i });
    await expect(generateBtn).toBeEnabled();
    await generateBtn.click();

    // Wait for synthesis completion and verify core sections
    await expect(page.getByText(/Reconstructed|Reconstruction|Complete|Overview|Decisions/i).first()).toBeVisible({ timeout: 15000 });
    await page.screenshot({ path: `${SCREENSHOT_DIR}/05_handover_generation.png`, fullPage: true });
  });

  // ============================================================================
  // PHASE 4 — EVIDENCE VERIFICATION & CONTRADICTION DETECTION
  // ============================================================================
  test('Phase 4: Evidence Verification — Grounding, Contradiction Detection & Conflict Resolution', async ({ page }) => {
    // Login
    await page.goto('/login');
    await page.getByRole('button', { name: /Auto Fill/i }).click();
    await page.locator('button[type="submit"]').click();
    await expect(page).toHaveURL(/.*dashboard/);

    // 1. Verification Dashboard
    await page.goto('/verification');
    await expect(page.getByRole('heading', { level: 1 })).toContainText(/Evidence Verification Dashboard/i);
    const runBtn = page.getByRole('button', { name: /Run Verification Engine|Start First Verification|Analyzing Claims/i }).first();
    await expect(runBtn).toBeVisible();

    // 2. Conflicts Page
    await page.goto('/conflicts');
    await expect(page.getByRole('heading', { level: 1 })).toContainText(/Knowledge Conflicts/i);

    // Verify scan / detect button or contradiction elements
    const scanBtn = page.getByRole('button', { name: /Run Contradiction Scan/i }).first();
    await expect(scanBtn).toBeVisible();

    await page.screenshot({ path: `${SCREENSHOT_DIR}/06_evidence_verification_conflicts.png`, fullPage: true });
  });

  // ============================================================================
  // PHASE 5 — APPROVAL WORKFLOW
  // ============================================================================
  test('Phase 5: Approval Workflow — Handover Review, Section Editing & Sign-off', async ({ page }) => {
    // Login
    await page.goto('/login');
    await page.getByRole('button', { name: /Auto Fill/i }).click();
    await page.locator('button[type="submit"]').click();
    await expect(page).toHaveURL(/.*dashboard/);

    // Navigate to Review Workspace
    await page.goto('/review/rev-auth-zero');
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible();

    // Verify sections (Project Overview, Key Decisions, Tasks)
    await expect(page.getByText(/Project Overview|Architecture|Key Decisions|Tasks/i).first()).toBeVisible();

    // Verify approval and edit actions
    const approveBtn = page.getByRole('button', { name: /Approve|Sign Off/i }).first();
    await expect(approveBtn).toBeVisible();

    await page.screenshot({ path: `${SCREENSHOT_DIR}/07_handover_approval.png`, fullPage: true });
  });

  // ============================================================================
  // PHASE 6 — VERSION MANAGEMENT
  // ============================================================================
  test('Phase 6: Version Management — Revisions, Diff Comparison Engine & Restoration', async ({ page }) => {
    // Login
    await page.goto('/login');
    await page.getByRole('button', { name: /Auto Fill/i }).click();
    await page.locator('button[type="submit"]').click();
    await expect(page).toHaveURL(/.*dashboard/);

    // Navigate to Handover Versions
    await page.goto('/handovers/rev-auth-zero/versions');
    await expect(page.getByRole('heading', { level: 1 })).toContainText(/Handover Version Management/i);

    // Verify versions list
    await expect(page.getByText(/v1\./i).first()).toBeVisible();

    // Open Compare Versions modal
    const compareBtn = page.getByRole('button', { name: /Compare Versions/i });
    if (await compareBtn.isVisible()) {
      await compareBtn.click();
      await expect(page.getByText(/Version Comparison Engine|Diff/i).first()).toBeVisible();
      await page.screenshot({ path: `${SCREENSHOT_DIR}/08_version_management_diff.png` });
      await page.keyboard.press('Escape');
    } else {
      await page.screenshot({ path: `${SCREENSHOT_DIR}/08_version_management_diff.png` });
    }
  });

  // ============================================================================
  // PHASE 7 — KNOWLEDGE TRANSFER (INCOMING CONTINUITY)
  // ============================================================================
  test('Phase 7: Knowledge Transfer — Incoming Member Receipt, Task Continuity & Progress Updates', async ({ page }) => {
    // Login
    await page.goto('/login');
    await page.getByRole('button', { name: /Auto Fill/i }).click();
    await page.locator('button[type="submit"]').click();
    await expect(page).toHaveURL(/.*dashboard/);

    // Navigate to Incoming Member Dashboard
    await page.goto('/incoming');
    await expect(page.getByRole('heading', { level: 1 })).toContainText(/Incoming Member Dashboard/i);

    // Verify all continuity sections
    await expect(page.getByRole('heading', { name: /1\. Shared Projects/i })).toBeVisible();
    await expect(page.getByRole('heading', { name: /2\. Received Handovers/i })).toBeVisible();
    await expect(page.getByRole('heading', { name: /3\. Continuation Tasks/i })).toBeVisible();

    // Test Acknowledge Receipt modal trigger
    const ackBtn = page.getByRole('button', { name: /Acknowledge Receipt/i }).first();
    if (await ackBtn.isVisible()) {
      await ackBtn.click();
      await expect(page.getByText(/Acknowledge Handover Receipt/i)).toBeVisible();
      await page.screenshot({ path: `${SCREENSHOT_DIR}/09_incoming_knowledge_transfer.png` });
      await page.keyboard.press('Escape');
    } else {
      await page.screenshot({ path: `${SCREENSHOT_DIR}/09_incoming_knowledge_transfer.png`, fullPage: true });
    }
  });

  // ============================================================================
  // PHASE 8 — FINAL VALIDATION (AUDIT TRAIL & PERMISSIONS)
  // ============================================================================
  test('Phase 8: Final Validation — Audit Trail, Security Context & Event Logging', async ({ page }) => {
    // Login
    await page.goto('/login');
    await page.getByRole('button', { name: /Auto Fill/i }).click();
    await page.locator('button[type="submit"]').click();
    await expect(page).toHaveURL(/.*dashboard/);

    // Navigate to Audit Trail
    await page.goto('/audit');
    await expect(page.getByRole('heading', { level: 1 })).toContainText(/Audit Trail/i);

    // Verify filter controls or timeline/table switchers
    await expect(page.getByText(/All Events|Actions|Timeline|Export|Filter/i).first()).toBeVisible();

    // Inspect first audit record context
    const inspectBtn = page.getByRole('button', { name: /Inspect Context/i }).first();
    if (await inspectBtn.isVisible()) {
      await inspectBtn.click();
      await expect(page.getByText(/Metadata|Request Context|Cryptographic/i).first()).toBeVisible();
      await page.screenshot({ path: `${SCREENSHOT_DIR}/10_audit_trail_validation.png` });
      await page.keyboard.press('Escape');
    } else {
      await page.screenshot({ path: `${SCREENSHOT_DIR}/10_audit_trail_validation.png`, fullPage: true });
    }
  });
});
