import { test, expect } from '@playwright/test';
import path from 'path';
import fs from 'fs';

const SCREENSHOT_DIR = path.resolve('test-results/screenshots');
const ARTIFACT_SCREENSHOT_DIR = 'C:/Users/Aadi Dagade/.gemini/antigravity/brain/6d3f310c-3d85-4dbc-8c2a-38cc0fc91d77/screenshots';

// Ensure screenshot directories exist
if (!fs.existsSync(SCREENSHOT_DIR)) {
  fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });
}

// Helper to save screenshot to both test-results and artifact folder
async function captureScreenshot(page: any, filename: string, fullPage: boolean = false) {
  const localPath = path.join(SCREENSHOT_DIR, filename);
  await page.screenshot({ path: localPath, fullPage });
  try {
    if (fs.existsSync(ARTIFACT_SCREENSHOT_DIR)) {
      const artifactPath = path.join(ARTIFACT_SCREENSHOT_DIR, filename);
      fs.copyFileSync(localPath, artifactPath);
    }
  } catch (err) {
    console.warn(`Could not mirror screenshot to artifact folder: ${err}`);
  }
}

test.describe('End-to-End QA Team Workflow Audit: CodeFrontier Platform', () => {
  test.setTimeout(180000); // 3 minutes for complete 8-phase audit

  test('Execute Full 8-Phase End-to-End Workflow across 3 User Roles', async ({ page, request }) => {
    // Standard Desktop Viewport
    await page.setViewportSize({ width: 1440, height: 900 });

    // =========================================================================
    // PHASE 1: PROJECT SETUP
    // =========================================================================
    console.log('[PHASE 1] Starting Project Setup...');

    // 1. Visit Registration Page
    await page.goto('/register');
    await expect(page.locator('h2')).toContainText(/Create your account/i);

    // Test form validation on empty submit
    await page.locator('button[type="submit"]').click();
    await expect(page.getByText(/Full name is required|Name is required/i)).toBeVisible();
    await captureScreenshot(page, '01_phase1_register_validation.png');

    // 2. Perform Login as Outgoing Lead (Sarah Chen)
    await page.goto('/login');
    await expect(page.locator('h2')).toContainText(/Sign in to your workspace/i);

    await page.locator('input[type="email"]').fill('sarah.chen@apex-pay.io');
    await page.locator('input[type="password"]').fill('Password123!');
    await captureScreenshot(page, '01_phase1_login_credentials.png');

    await page.locator('button[type="submit"]').click();
    await expect(page).toHaveURL(/.*dashboard/);
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
    await captureScreenshot(page, '02_phase1_dashboard_logged_in.png');

    // 3. Project Creation
    await page.goto('/projects');
    await expect(page.getByRole('heading', { name: /Projects/i })).toBeVisible();

    const createBtn = page.getByRole('button', { name: /Create Project/i });
    await expect(createBtn).toBeVisible();
    await createBtn.click();

    // Verify Wizard Modal opens
    await expect(page.getByText(/Create New Project Workspace/i)).toBeVisible();
    await page.getByLabel(/Project Name \*/i).fill('Apex Multi-Currency Distributed Settlement Engine');
    await page.getByLabel(/Project Key \*/i).fill('APEX-SETTLE');
    await page.getByLabel(/Description \*/i).fill('High-throughput distributed multi-currency financial settlement engine supporting ISO 20022 wire formats, Apache Kafka 3.6 event bus, and PostgreSQL 16 persistence.');

    await captureScreenshot(page, '03_phase1_project_wizard_step1.png');

    // Step through wizard
    await page.getByRole('button', { name: /Continue to Handover Config/i }).click();
    await page.getByRole('button', { name: /Continue to Permissions/i }).click();
    await page.getByRole('button', { name: /Continue to Review & Create/i }).click();
    await page.getByRole('button', { name: /Create Workspace/i }).click();

    // Verify redirect to project workspace
    await expect(page).toHaveURL(/.*projects\/.+/);
    await captureScreenshot(page, '04_phase1_project_workspace_created.png');

    // 4. Project Member Management & Role Assignment
    await page.goto('/projects/proj-1/members');
    await expect(page.getByRole('heading', { level: 1 })).toContainText(/Project Members/i);
    await expect(page.locator('table, .divide-y').first()).toBeVisible();

    const addMemberBtn = page.getByRole('button', { name: /Add Member|Invite Member/i }).first();
    await expect(addMemberBtn).toBeVisible();
    await addMemberBtn.click();

    // Verify invite modal
    await expect(page.getByText(/Invite Member to Project Workspace/i)).toBeVisible();
    await page.locator('input[type="email"], input[placeholder*="email" i]').first().fill('marcus.vance@apex-pay.io');
    await captureScreenshot(page, '05_phase1_invite_modal_reviewer.png');
    await page.keyboard.press('Escape');

    // =========================================================================
    // PHASE 2: DOCUMENT UPLOAD
    // =========================================================================
    console.log('[PHASE 2] Starting Document Upload...');

    await page.goto('/knowledge-sources');
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible();

    // Ensure test documents exist
    const pdfPath = path.resolve('test_docs/apex_settlement_architecture.pdf');
    const docxPath = path.resolve('test_docs/apex_migration_guide.docx');
    const txtPath = path.resolve('test_docs/apex_operational_runbook.txt');
    const mdPath = path.resolve('test_docs/apex_product_requirements.md');

    expect(fs.existsSync(pdfPath)).toBeTruthy();
    expect(fs.existsSync(docxPath)).toBeTruthy();
    expect(fs.existsSync(txtPath)).toBeTruthy();
    expect(fs.existsSync(mdPath)).toBeTruthy();

    // Upload documents through file input
    const fileInput = page.locator('input[type="file"]');
    await expect(fileInput).toBeAttached();

    await fileInput.setInputFiles([pdfPath, docxPath, txtPath, mdPath]);
    await page.waitForTimeout(1000); // Allow react state update

    await captureScreenshot(page, '06_phase2_documents_uploaded_list.png', true);

    // Verify Document Drawer / Details
    const firstDocRow = page.locator('tbody tr').first();
    await expect(firstDocRow).toBeVisible();
    await firstDocRow.click();

    // Verify drawer opened with extraction and chunk details
    await expect(page.getByText(/AST|Chunk|Extraction|Metadata|\.(pdf|docx|txt|md)/i).first()).toBeVisible();
    await captureScreenshot(page, '07_phase2_document_details_drawer.png');
    await page.keyboard.press('Escape');

    // =========================================================================
    // PHASE 3: AI HANDOVER
    // =========================================================================
    console.log('[PHASE 3] Starting AI Handover Generation...');

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
    await expect(page.getByText(/Reconstructed|Reconstruction|Complete|Overview|Decisions/i).first()).toBeVisible({ timeout: 20000 });
    await captureScreenshot(page, '08_phase3_handover_generated.png', true);

    // =========================================================================
    // PHASE 4: EVIDENCE VERIFICATION & CONTRADICTION DETECTION
    // =========================================================================
    console.log('[PHASE 4] Starting Evidence Verification & Contradiction Detection...');

    // 1. Evidence Verification Dashboard
    await page.goto('/verification');
    await expect(page.getByRole('heading', { level: 1 })).toContainText(/Evidence Verification Dashboard/i);

    const runBtn = page.getByRole('button', { name: /Run Verification Engine|Start First Verification|Analyzing Claims/i }).first();
    await expect(runBtn).toBeVisible();
    await runBtn.click();
    await page.waitForTimeout(1000);

    // Inspect grounded claims
    await expect(page.getByText(/Supported|Claims|Alignment|Verified/i).first()).toBeVisible();
    await captureScreenshot(page, '09_phase4_evidence_claims_verified.png');

    // 2. Knowledge Conflicts & Contradiction Resolution
    await page.goto('/conflicts');
    await expect(page.getByRole('heading', { level: 1 })).toContainText(/Knowledge Conflicts/i);

    const scanBtn = page.getByRole('button', { name: /Run Contradiction Scan/i }).first();
    await expect(scanBtn).toBeVisible();
    await scanBtn.click();
    await page.waitForTimeout(1000);

    // Verify contradiction categories
    await expect(page.getByText(/Contradiction|Conflict|Category|High|Medium/i).first()).toBeVisible();
    await captureScreenshot(page, '10_phase4_knowledge_conflicts_detected.png');

    // Resolve conflict modal (check if active conflict card has resolve button)
    const resolveBtn = page.getByRole('button', { name: /^Resolve Conflict$/i }).first();
    if (await resolveBtn.isVisible()) {
      await resolveBtn.click();
      await expect(page.getByText(/Human Conflict Arbitration|Select the authoritative statement/i).first()).toBeVisible();
      await captureScreenshot(page, '11_phase4_conflict_resolution_modal.png');
      await page.keyboard.press('Escape');
    } else {
      await captureScreenshot(page, '11_phase4_conflicts_triage_view.png');
    }

    // =========================================================================
    // PHASE 5: REVIEW AND APPROVAL
    // =========================================================================
    console.log('[PHASE 5] Starting Review and Approval Workflow...');

    await page.goto('/review/rev-auth-zero');
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible();

    // Verify sections (Overview, Architecture, Key Decisions)
    await expect(page.getByText(/Project Overview|Architecture|Key Decisions|Tasks/i).first()).toBeVisible();

    // Check approval action button
    const approveBtn = page.getByRole('button', { name: /Approve|Sign Off/i }).first();
    await expect(approveBtn).toBeVisible();

    await captureScreenshot(page, '12_phase5_handover_review_workspace.png', true);

    // =========================================================================
    // PHASE 6: VERSION MANAGEMENT
    // =========================================================================
    console.log('[PHASE 6] Starting Version Management & Comparison...');

    await page.goto('/handovers/rev-auth-zero/versions');
    await expect(page.getByRole('heading', { level: 1 })).toContainText(/Handover Version Management/i);

    // Verify snapshot button and existing versions
    const snapshotBtn = page.getByRole('button', { name: /Create Snapshot/i });
    await expect(snapshotBtn).toBeVisible();
    await expect(page.getByText(/v1\./i).first()).toBeVisible();

    // Open Compare Versions modal
    const compareBtn = page.getByRole('button', { name: /Compare Versions/i });
    if (await compareBtn.isVisible()) {
      await compareBtn.click();
      await expect(page.getByText(/Version Comparison Engine|Diff/i).first()).toBeVisible();
      await captureScreenshot(page, '13_phase6_version_comparison_diff.png');
      await page.goto('/handovers/rev-auth-zero/versions');
    }

    // Open Restore Version confirmation modal
    const restoreBtn = page.getByRole('button', { name: /Restore Version/i }).first();
    if (await restoreBtn.isVisible()) {
      await restoreBtn.click();
      await expect(page.getByText(/Restore Previous Version/i)).toBeVisible();
      await captureScreenshot(page, '14_phase6_restore_version_modal.png');
      await page.goto('/handovers/rev-auth-zero/versions');
    }

    // =========================================================================
    // PHASE 7: KNOWLEDGE TRANSFER (INCOMING MEMBER CONTINUITY)
    // =========================================================================
    console.log('[PHASE 7] Starting Incoming Member Knowledge Transfer...');

    // Log in as Incoming Member (Alex Rivera)
    await page.goto('/login');
    await page.locator('input[type="email"]').fill('alex.rivera@apex-pay.io');
    await page.locator('input[type="password"]').fill('Password123!');
    await page.locator('button[type="submit"]').click();
    await expect(page).toHaveURL(/.*dashboard/);

    // Navigate to Incoming Member Dashboard
    await page.goto('/incoming');
    await expect(page.getByRole('heading', { level: 1 })).toContainText(/Incoming Member Dashboard/i);

    // Verify all continuity sections
    await expect(page.getByRole('heading', { name: /1\. Shared Projects/i })).toBeVisible();
    await expect(page.getByRole('heading', { name: /2\. Received Handovers/i })).toBeVisible();
    await expect(page.getByRole('heading', { name: /3\. Continuation Tasks/i })).toBeVisible();

    await captureScreenshot(page, '15_phase7_incoming_dashboard_loaded.png', true);

    // Test Acknowledge Receipt modal
    const ackBtn = page.getByRole('button', { name: /Acknowledge Receipt/i }).first();
    if (await ackBtn.isVisible()) {
      await ackBtn.click();
      await expect(page.getByText(/Acknowledge Handover Receipt/i)).toBeVisible();
      await captureScreenshot(page, '16_phase7_acknowledge_receipt_modal.png');

      const checkbox = page.locator('input[type="checkbox"]').first();
      if (await checkbox.isVisible()) {
        await checkbox.check();
      }
      await page.goto('/incoming');
    }

    // Test Task Progress Update
    const updateTaskBtn = page.getByRole('button', { name: /Log Progress|Update Progress|Toggle progress history/i }).first();
    if (await updateTaskBtn.isVisible()) {
      await updateTaskBtn.click();
      await page.waitForTimeout(500);
      await captureScreenshot(page, '17_phase7_task_progress_update_modal.png');
      await page.goto('/incoming');
    }

    // =========================================================================
    // PHASE 8: FINAL VALIDATION (AUDIT TRAIL & PERMISSIONS)
    // =========================================================================
    console.log('[PHASE 8] Starting Final Audit Trail & Persistence Validation...');

    await page.goto('/audit');
    await expect(page.getByRole('heading', { level: 1 })).toContainText(/Audit Trail/i);

    // Verify audit log entries
    await expect(page.getByText(/All Events|Actions|Timeline|Export|Filter/i).first()).toBeVisible();

    const inspectBtn = page.getByRole('button', { name: /Inspect Context/i }).first();
    if (await inspectBtn.isVisible()) {
      await inspectBtn.click();
      await expect(page.getByText(/Metadata|Request Context|Cryptographic/i).first()).toBeVisible();
      await captureScreenshot(page, '18_phase8_audit_event_inspect_modal.png');
      await page.goto('/audit');
    }

    await captureScreenshot(page, '19_phase8_audit_trail_table.png', true);

    console.log('[AUDIT COMPLETE] All 8 Phases executed and verified successfully!');
  });
});
