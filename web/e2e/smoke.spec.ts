import { test, expect } from "@playwright/test";

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
    await page.goto("/");
    await page.getByTestId("work-mode-tab-resolve").click();
    await expect(page.getByTestId("resolve-review-grid")).toBeVisible({ timeout: 15_000 });
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
    await page.addInitScript(() => {
      (window as unknown as { __NOVELGUARD_TEST_BRIDGE_FAIL__?: string }).__NOVELGUARD_TEST_BRIDGE_FAIL__ =
        "getMovePreview";
    });
    await page.goto("/");
    await page.getByTestId("work-mode-tab-resolve").click();
    await page.getByTestId("batch-preview-open").click();
    await page.getByTestId("apply-preview-run").click();
    await expect(page.getByTestId("apply-preview-error")).toBeVisible();
    await expect(page.getByTestId("apply-confirm-run")).toHaveCount(0);
  });

  test("review column chooser toggles encoding column", async ({ page }) => {
    await page.goto("/");
    await page.getByTestId("work-mode-tab-resolve").click();
    await expect(page.getByTestId("resolve-review-grid")).toBeVisible({ timeout: 15_000 });
    await page.getByTestId("grid-column-chooser").locator("summary").click();
    await page.getByTestId("column-toggle-encoding").check();
    await expect(page.getByTestId("resolve-grid-header-encoding")).toBeVisible();
  });

  test("review grid header sort triggers sorted fetch", async ({ page }) => {
    await page.goto("/");
    await page.getByTestId("work-mode-tab-resolve").click();
    await expect(page.getByTestId("resolve-review-grid")).toBeVisible({ timeout: 15_000 });
    const statusHeader = page.getByTestId("resolve-grid-header-status");
    await statusHeader.scrollIntoViewIfNeeded();
    await statusHeader.click();
    await expect(statusHeader).toContainText(/[▲▼]/);
  });

  test("closing apply dialog discards pending preview", async ({ page }) => {
    await page.goto("/");
    await page.getByTestId("work-mode-tab-resolve").click();
    await page.getByTestId("batch-preview-open").click();
    await page.getByTestId("apply-preview-run").click();
    await expect(page.getByTestId("apply-confirm-run")).toBeVisible();
    await page.getByRole("button", { name: "취소" }).click();
    await expect(page.getByTestId("apply-confirm-run")).toHaveCount(0);
  });

  test("library revision bump shows stale banner", async ({ page }) => {
    await page.goto("/");
    await page.getByTestId("work-mode-tab-resolve").click();
    await page.getByTestId("batch-preview-open").click();
    await page.getByTestId("apply-preview-run").click();
    await expect(page.getByTestId("apply-confirm-run")).toBeVisible();
    await page.evaluate(() => {
      (window as unknown as { __NOVELGUARD_TEST_BUMP_REVISION__?: () => void }).__NOVELGUARD_TEST_BUMP_REVISION__?.();
    });
    await expect(page.getByTestId("apply-stale-banner")).toBeVisible({ timeout: 5_000 });
    await expect(page.getByTestId("apply-confirm-run")).toHaveCount(0);
  });

  test("pywebview host without api shows unavailable", async ({ page }) => {
    await page.addInitScript(() => {
      (window as unknown as { pywebview?: { api?: unknown } }).pywebview = {};
    });
    await page.goto("/");
    await expect(page.getByTestId("bridge-unavailable")).toBeVisible();
  });
});
