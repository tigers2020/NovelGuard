import { test, expect } from "@playwright/test";

async function openResolveWorkspace(page: import("@playwright/test").Page) {
  await page.goto("/");
  await page.evaluate(() => {
    localStorage.removeItem("novelguard.reviewGrid.sizing.v1");
  });
  await page.reload();
  await page.getByTestId("work-mode-tab-resolve").click();
  await expect(page.getByTestId("resolve-review-grid")).toBeVisible({ timeout: 15_000 });
}

/** Open apply subflow. Bar click uses evaluate (grid can intercept pointer events); in-dialog clicks use the dialog scope. */
async function openApplyDialog(page: import("@playwright/test").Page) {
  await page.getByTestId("batch-preview-open").evaluate((el) => (el as HTMLButtonElement).click());
  const dialog = page.getByTestId("apply-subflow-dialog");
  await expect(dialog).toBeVisible();
  await expect(dialog.getByTestId("apply-preview-run")).toBeVisible();
}

async function clickApplyPreviewRun(page: import("@playwright/test").Page) {
  await page
    .getByTestId("apply-subflow-dialog")
    .getByTestId("apply-preview-run")
    .evaluate((el) => (el as HTMLButtonElement).click());
}

/** Pick a mock row with executable move_duplicate so preview reaches confirm step. */
async function selectExecutableMoveRow(page: import("@playwright/test").Page) {
  await page.getByRole("button", { name: "Move Plan" }).click();
  const row = page.getByTestId("grid-row-row-2");
  await expect(row).toBeVisible({ timeout: 15_000 });
  await row.scrollIntoViewIfNeeded();
  await row.click();
}

async function runApplyPreview(page: import("@playwright/test").Page) {
  await selectExecutableMoveRow(page);
  await openApplyDialog(page);
  await clickApplyPreviewRun(page);
}

test.describe("NovelGuard smoke", () => {
  test("app loads and shows connection badge", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByTestId("connection-badge")).toBeVisible();
    await expect(page.getByTestId("connection-badge")).toContainText(/Mock bridge|Bridge/i);
  });

  test("Work mode tabs switch scan resolve quality", async ({ page }) => {
    await page.goto("/");
    await page.getByTestId("work-mode-tab-scan").click();
    await expect(page.getByTestId("work-mode-tab-scan")).toHaveClass(/bg-primary/);
    await page.getByTestId("work-mode-tab-resolve").click();
    await expect(page.getByTestId("resolve-workspace")).toBeVisible();
    await page.getByTestId("work-mode-tab-quality").click();
    await expect(page.getByTestId("work-mode-tab-quality")).toHaveClass(/bg-primary/);
  });

  test("resolve grid loads rows from mock bridge", async ({ page }) => {
    await openResolveWorkspace(page);
  });

  test("quality query failure shows error and retry", async ({ page }) => {
    await page.addInitScript(() => {
      (window as unknown as { __NOVELGUARD_TEST_BRIDGE_FAIL__?: string }).__NOVELGUARD_TEST_BRIDGE_FAIL__ =
        "queryQualityRows";
    });
    await page.goto("/");
    await page.getByTestId("work-mode-tab-quality").click();
    await expect(page.getByTestId("quality-workspace")).toBeVisible();
    await expect(page.getByTestId("quality-query-error")).toBeVisible();
    await page.getByTestId("quality-query-retry").click();
    await expect(page.getByTestId("quality-query-error")).toBeVisible();
  });

  test("query failure shows error and retry", async ({ page }) => {
    await page.addInitScript(() => {
      (window as unknown as { __NOVELGUARD_TEST_BRIDGE_FAIL__?: string }).__NOVELGUARD_TEST_BRIDGE_FAIL__ =
        "queryReviewRows";
    });
    await page.goto("/");
    await page.getByTestId("work-mode-tab-resolve").click();
    await expect(page.getByTestId("resolve-query-error")).toBeVisible();
    await page.getByTestId("resolve-query-retry").click();
    await expect(page.getByTestId("resolve-query-error")).toBeVisible();
  });

  test("snapshot failure shows unavailable screen", async ({ page }) => {
    await page.addInitScript(() => {
      (window as unknown as { __NOVELGUARD_TEST_BRIDGE_FAIL__?: string }).__NOVELGUARD_TEST_BRIDGE_FAIL__ =
        "snapshot";
    });
    await page.goto("/");
    await expect(page.getByTestId("bridge-unavailable")).toBeVisible();
  });

  test("preview failure blocks apply", async ({ page }) => {
    await page.setViewportSize({ width: 1920, height: 900 });
    await page.addInitScript(() => {
      (window as unknown as { __NOVELGUARD_TEST_BRIDGE_FAIL__?: string }).__NOVELGUARD_TEST_BRIDGE_FAIL__ =
        "getMovePreview";
    });
    await openResolveWorkspace(page);
    await selectExecutableMoveRow(page);
    await openApplyDialog(page);
    await clickApplyPreviewRun(page);
    await expect(page.getByTestId("apply-preview-error")).toBeVisible();
    await expect(page.getByTestId("apply-confirm-run")).toHaveCount(0);
  });

  test("review grid horizontal scroll exposes action target conf headers", async ({ page }) => {
    await page.setViewportSize({ width: 1920, height: 900 });
    await openResolveWorkspace(page);
    const scrollBody = page.getByTestId("grid-scroll-body");
    await scrollBody.evaluate((el) => {
      el.scrollLeft = el.scrollWidth - el.clientWidth;
    });
    await expect(page.getByTestId("resolve-grid-header-proposedAction")).toBeVisible();
    await expect(page.getByTestId("resolve-grid-header-targetFolder")).toBeVisible();
    await expect(page.getByTestId("resolve-grid-header-confidence")).toBeVisible();
  });

  test("review grid exposes column resize handles", async ({ page }) => {
    await page.setViewportSize({ width: 1920, height: 900 });
    await openResolveWorkspace(page);
    await expect(page.getByTestId("grid-resize-handle-name")).toHaveCount(1);
    await expect(page.getByTestId("grid-resize-handle-proposedAction")).toHaveCount(1);
  });

  test("review grid header sort triggers sorted fetch", async ({ page }) => {
    await page.setViewportSize({ width: 1920, height: 900 });
    await openResolveWorkspace(page);
    const nameHeader = page.getByTestId("resolve-grid-header-name");
    await nameHeader.scrollIntoViewIfNeeded();
    await nameHeader.click();
    await expect(nameHeader).toContainText(/[▲▼]/);
  });

  test("closing apply dialog discards pending preview", async ({ page }) => {
    await page.setViewportSize({ width: 1920, height: 900 });
    await openResolveWorkspace(page);
    await runApplyPreview(page);
    await expect(page.getByTestId("apply-confirm-run")).toBeVisible();
    await page
      .getByTestId("apply-subflow-dialog")
      .getByRole("button", { name: "취소" })
      .evaluate((el) => (el as HTMLButtonElement).click());
    await expect(page.getByTestId("apply-confirm-run")).toHaveCount(0);
  });

  test("library revision bump shows stale banner", async ({ page }) => {
    await page.setViewportSize({ width: 1920, height: 900 });
    await openResolveWorkspace(page);
    await runApplyPreview(page);
    await expect(page.getByTestId("apply-confirm-run")).toBeVisible();
    await page.evaluate(() => {
      (window as unknown as { __NOVELGUARD_TEST_BUMP_REVISION__?: () => void }).__NOVELGUARD_TEST_BUMP_REVISION__?.();
    });
    await expect(page.getByTestId("apply-stale-banner")).toBeVisible({ timeout: 5_000 });
    await expect(page.getByTestId("apply-confirm-run")).toHaveCount(0);
  });

  test("pywebview host without api shows unavailable", async ({ page }) => {
    await page.addInitScript(() => {
      const w = window as unknown as {
        pywebview?: { api?: unknown };
        __NOVELGUARD_FORCE_PYWEBVIEW_WAIT__?: boolean;
      };
      w.pywebview = {};
      w.__NOVELGUARD_FORCE_PYWEBVIEW_WAIT__ = true;
    });
    await page.goto("/");
    await expect(page.getByTestId("bridge-unavailable")).toBeVisible({ timeout: 15_000 });
  });

  test("quality grid header sort shows sort indicator", async ({ page }) => {
    await page.goto("/");
    await page.getByTestId("work-mode-tab-quality").click();
    await expect(page.getByTestId("quality-issue-grid")).toBeVisible({ timeout: 15_000 });
    const header = page.getByTestId("quality-grid-header-name");
    await header.click();
    await expect(header).toHaveText(/▲|▼/);
  });

  test("quality column chooser reveals path column", async ({ page }) => {
    await page.goto("/");
    await page.getByTestId("work-mode-tab-quality").click();
    await expect(page.getByTestId("quality-issue-grid")).toBeVisible({ timeout: 15_000 });
    await page.getByTestId("quality-column-chooser").locator("summary").click();
    await page.getByTestId("column-toggle-path").check();
    await expect(page.getByTestId("quality-grid-header-path")).toBeVisible();
  });

  test("Settings route loads diagnostics", async ({ page }) => {
    await page.goto("/");
    await page.getByTestId("nav-settings").click();
    await expect(page.getByTestId("settings-route")).toBeVisible();
    await expect(page.getByTestId("app-info-diagnostics")).toBeVisible();
  });

  test("shell file dock sort and load more", async ({ page }) => {
    await page.goto("/");
    await page.getByTestId("shell-file-dock").getByRole("button", { name: /파일 목록/ }).click();
    await expect(page.getByTestId("shell-file-dock-table")).toBeVisible({ timeout: 15_000 });
    const nameHeader = page.getByTestId("shell-file-dock-sort-name");
    await expect(nameHeader).toBeVisible();
    await nameHeader.click();
    await expect(nameHeader).toHaveText(/▲|▼/);

    const loadMore = page.getByTestId("shell-file-dock-load-more");
    await expect(loadMore).toBeVisible({ timeout: 10_000 });
    const rowCountBefore = await page.locator("[data-testid='shell-file-dock-table'] tbody tr").count();
    await loadMore.click();
    await expect
      .poll(async () => page.locator("[data-testid='shell-file-dock-table'] tbody tr").count())
      .toBeGreaterThan(rowCountBefore);
  });

  test("Logs route loads live and artifacts sections", async ({ page }) => {
    await page.goto("/");
    await page.getByTestId("nav-logs").click();
    await expect(page.getByTestId("logs-route")).toBeVisible();
    await expect(page.getByTestId("logs-live-list")).toBeVisible();
    await expect(page.getByTestId("logs-artifacts-list")).toBeVisible();
  });
});
