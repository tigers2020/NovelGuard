import { test, expect } from "@playwright/test";

async function expandResolveFacet(page: import("@playwright/test").Page) {
  const panel = page.getByTestId("resolve-facet-panel");
  if ((await panel.getAttribute("data-state")) === "collapsed") {
    await panel.getByRole("button", { name: /검토 보기|▸/ }).click();
    await expect(panel).toHaveAttribute("data-state", "expanded");
  }
}

async function openResolveWorkspace(page: import("@playwright/test").Page) {
  await page.goto("/");
  await page.evaluate(() => {
    localStorage.removeItem("novelguard.reviewGrid.sizing.v1");
  });
  await page.reload();
  await page.getByTestId("work-mode-tab-resolve").click();
  await expect(page.getByTestId("shell-file-dock")).toHaveAttribute("data-state", "collapsed");
  await expect(page.getByTestId("resolve-facet-panel")).toHaveAttribute("data-state", "collapsed");
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

/** Open move facet + Exact filter so current_query preview is enabled. */
async function prepareExecutableMoveFilter(page: import("@playwright/test").Page) {
  await page.getByTestId("resolve-type-filter-exact").click();
  await expandResolveFacet(page);
  await page.getByTestId("resolve-facet-move").click();
  await expect(page.getByTestId("batch-preview-open")).toBeEnabled({ timeout: 15_000 });
}

async function runApplyPreview(page: import("@playwright/test").Page) {
  await prepareExecutableMoveFilter(page);
  await openApplyDialog(page);
  await clickApplyPreviewRun(page);
}

async function clickApplyConfirmRun(page: import("@playwright/test").Page) {
  await page
    .getByTestId("apply-subflow-dialog")
    .getByTestId("apply-confirm-run")
    .evaluate((el) => (el as HTMLButtonElement).click());
}

async function runScanToSuccess(page: import("@playwright/test").Page) {
  await page.getByTestId("work-mode-tab-scan").click();
  await page.getByTestId("scan-start").click();
  await expect(page.getByTestId("scan-section")).toHaveAttribute("data-state", "success", {
    timeout: 20_000,
  });
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
    await expect(page.getByTestId("shell-file-dock")).toHaveAttribute("data-state", "collapsed");
    await page.getByTestId("work-mode-tab-quality").click();
    await expect(page.getByTestId("work-mode-tab-quality")).toHaveClass(/bg-primary/);
    await expect(page.getByTestId("shell-file-dock")).toHaveAttribute("data-state", "collapsed");
  });

  test("029 dock policy: collapse on Resolve, restore Scan preference when files exist", async ({
    page,
  }) => {
    await page.goto("/");
    await page.getByTestId("work-mode-tab-scan").click();
    await expect(page.getByTestId("shell-file-dock")).toHaveAttribute("data-state", "collapsed");
    await page.getByTestId("scan-open-file-dock").evaluate((el) => (el as HTMLButtonElement).click());
    await expect(page.getByTestId("shell-file-dock")).toHaveAttribute("data-state", "expanded");
    await page.getByTestId("work-mode-tab-resolve").click();
    await expect(page.getByTestId("shell-file-dock")).toHaveAttribute("data-state", "collapsed");
    await page.getByTestId("work-mode-tab-scan").click();
    await expect(page.getByTestId("shell-file-dock")).toHaveAttribute("data-state", "expanded");
  });

  test("PR-32 scan folder picker updates mock selected path", async ({ page }) => {
    await page.goto("/");
    await page.getByTestId("work-mode-tab-scan").click();
    await expect(page.getByTestId("scan-section")).toBeVisible();
    await page.getByTestId("scan-select-folder").click();
    await expect(page.getByTestId("scan-folder-error")).toHaveCount(0);
    await expect(page.getByTitle("D:/Novels/Library/selected")).toBeVisible();
    await expect(page.getByTestId("scan-section")).toHaveAttribute("data-state", /success|ready/);
    await expect(page.getByTestId("scan-summary")).toBeVisible();
  });

  test("PR-38 work mode tab switches to scan from resolve default", async ({ page }) => {
    await page.goto("/");
    await page.getByTestId("work-mode-tab-scan").click();
    await expect(page.getByTestId("work-mode-tab-scan")).toHaveClass(/bg-primary/);
    await expect(page.getByTestId("scan-section")).toBeVisible();
  });

  test("PR-38 scan reveals expanded file dock", async ({ page }) => {
    await page.goto("/");
    await page.getByTestId("work-mode-tab-scan").click();
    await expect(page.getByTestId("shell-file-dock")).toHaveAttribute("data-state", "collapsed");
    await page.getByTestId("scan-open-file-dock").evaluate((el) => (el as HTMLButtonElement).click());
    await expect(page.getByTestId("shell-file-dock")).toHaveAttribute("data-state", "expanded");
    await page.getByTestId("shell-file-dock").getByRole("button", { name: /파일 목록/ }).click();
    await expect(page.getByTestId("shell-file-dock")).toHaveAttribute("data-state", "collapsed");
    await page.getByTestId("scan-open-file-dock").evaluate((el) => (el as HTMLButtonElement).click());
    await expect(page.getByTestId("shell-file-dock")).toHaveAttribute("data-state", "expanded");
    await expect(page.getByTestId("shell-file-dock-table")).toBeVisible({ timeout: 15_000 });
  });

  test("PR-35 scan settings link opens settings route", async ({ page }) => {
    await page.goto("/");
    await page.getByTestId("work-mode-tab-scan").click();
    await page.getByTestId("scan-open-settings").click();
    await expect(page.getByTestId("settings-route")).toBeVisible();
  });

  test("PR-40 settings section nav shows app info", async ({ page }) => {
    await page.goto("/");
    await page.getByTestId("nav-settings").click();
    await page.getByTestId("settings-nav-app").click();
    await expect(page.getByTestId("settings-section-app")).toBeVisible();
  });

  test("PR-40 logs search filters entries", async ({ page }) => {
    await page.goto("/");
    await page.getByTestId("nav-logs").click();
    await page.getByTestId("logs-search").fill("mock log seed info");
    await expect(page.getByTestId("logs-live-list")).toContainText("mock log seed info");
    await page.getByTestId("logs-search").fill("__no_such_log_message__");
    await expect(page.getByTestId("logs-live-list")).toContainText("표시할 로그가 없습니다");
  });

  test("PR-31 rapid work mode tabs keep highlight and panel in sync", async ({ page }) => {
    await page.goto("/");
    const modes = ["scan", "resolve", "quality"] as const;
    const panelByMode = {
      scan: page.getByTestId("scan-section"),
      resolve: page.getByTestId("resolve-workspace"),
      quality: page.getByTestId("quality-workspace"),
    };

    for (let i = 0; i < 10; i += 1) {
      const mode = modes[i % modes.length];
      await page.getByTestId(`work-mode-tab-${mode}`).click();
      await expect(page.getByTestId(`work-mode-tab-${mode}`)).toHaveClass(/bg-primary/);
      for (const other of modes) {
        const panel = panelByMode[other];
        if (other === mode) {
          await expect(panel).toBeVisible();
        } else {
          await expect(panel).not.toBeVisible();
        }
      }
    }
  });

  test("PR-31 resolve grid scroll survives quality detour", async ({ page }) => {
    await page.setViewportSize({ width: 1920, height: 900 });
    await openResolveWorkspace(page);
    const resolveGrid = page.getByTestId("resolve-review-grid");
    const scrollBody = resolveGrid.getByTestId("grid-scroll-body");
    await scrollBody.evaluate((el) => {
      el.scrollTop = Math.min(480, el.scrollHeight - el.clientHeight);
    });
    const scrollBefore = await scrollBody.evaluate((el) => el.scrollTop);
    expect(scrollBefore).toBeGreaterThan(0);

    await page.getByTestId("work-mode-tab-quality").click();
    await expect(page.getByTestId("quality-workspace")).toBeVisible();
    await page.getByTestId("work-mode-tab-resolve").click();
    await expect(resolveGrid).toBeVisible();

    const scrollAfter = await scrollBody.evaluate((el) => el.scrollTop);
    expect(scrollAfter).toBe(scrollBefore);
  });

  test("PR-31 setWorkMode failure rolls back and shows error strip", async ({ page }) => {
    await page.addInitScript(() => {
      (window as unknown as { __NOVELGUARD_TEST_BRIDGE_FAIL__?: string }).__NOVELGUARD_TEST_BRIDGE_FAIL__ =
        "setWorkMode";
    });
    await page.goto("/");
    await expect(page.getByTestId("work-mode-tab-resolve")).toHaveClass(/bg-primary/);
    await page.getByTestId("work-mode-tab-quality").click();
    await expect(page.getByTestId("work-mode-error")).toBeVisible();
    await expect(page.getByTestId("work-mode-tab-resolve")).toHaveClass(/bg-primary/);
    await expect(page.getByTestId("quality-workspace")).not.toBeVisible();
  });

  test("resolve grid loads rows from mock bridge", async ({ page }) => {
    await openResolveWorkspace(page);
  });

  test("NOV-19 resolve grid has no batch selection checkbox column", async ({ page }) => {
    await openResolveWorkspace(page);
    const resolveGrid = page.getByTestId("resolve-review-grid");
    await expect(resolveGrid.locator('input[type="checkbox"]')).toHaveCount(0);
    await expect(resolveGrid.getByTestId("grid-header-select-all")).toHaveCount(0);
  });

  test("NOV-19 batch bar keeps exclude and preview only", async ({ page }) => {
    await openResolveWorkspace(page);
    await expect(page.getByTestId("batch-exclude-all-filtered")).toBeVisible();
    await expect(page.getByTestId("batch-preview-open")).toBeVisible();
    await expect(page.getByTestId("batch-approve-selected")).toHaveCount(0);
    await expect(page.getByTestId("batch-exclude-selected")).toHaveCount(0);
    await expect(page.getByTestId("batch-approve-all-filtered")).toHaveCount(0);
    await expect(page.getByRole("button", { name: "보이는 행 전체 선택" })).toHaveCount(0);
  });

  test("NOV-19 bulk exclude confirm shows updated copy", async ({ page }) => {
    await openResolveWorkspace(page);
    await page.getByTestId("resolve-type-filter-exact").click();
    await expect(page.getByTestId("batch-exclude-all-filtered")).toBeEnabled({ timeout: 15_000 });
    await page.getByTestId("batch-exclude-all-filtered").click();
    const dialog = page.getByTestId("bulk-filter-confirm-dialog");
    await expect(dialog).toBeVisible();
    await expect(dialog.getByRole("heading")).toHaveText("현재 필터 결과 제외");
    await expect(dialog).toContainText("현재 필터에 포함된 이동 후보");
    await expect(dialog).toContainText("이 파일들은 미리보기와 적용 대상에서 빠집니다.");
    await page.getByTestId("bulk-filter-confirm-cancel").click();
    await expect(dialog).toHaveCount(0);
  });

  test("NOV-19 preview enables from current filter without checkbox selection", async ({ page }) => {
    await openResolveWorkspace(page);
    await prepareExecutableMoveFilter(page);
    await openApplyDialog(page);
    await expect(page.getByTestId("apply-preview-run")).toBeVisible();
  });

  test("NOV-19 preview disabled when filter has no executable rows", async ({ page }) => {
    await openResolveWorkspace(page);
    await page.getByTestId("resolve-type-filter-near").click();
    const preview = page.getByTestId("batch-preview-open");
    await expect(preview).toBeDisabled();
    await expect(preview).toHaveAttribute(
      "title",
      /검토 전용이며 일괄 적용할 수 없습니다/,
    );
  });

  test("NOV-22 resolve defaults to exact and preview needs no type-filter click", async ({ page }) => {
    await openResolveWorkspace(page);
    await expect(page.getByTestId("resolve-type-filter-exact")).toHaveClass(/bg-primary/);
    await expect(page.getByTestId("batch-preview-open")).toBeEnabled({ timeout: 15_000 });
  });

  test("NOV-22 verify first-entry preview opens apply dialog without checkbox", async ({ page }) => {
    await openResolveWorkspace(page);
    await openApplyDialog(page);
    await expect(page.getByTestId("apply-preview-run")).toBeVisible();
  });

  test("NOV-22 verify all types filter disables preview with tooltip", async ({ page }) => {
    await openResolveWorkspace(page);
    await page.getByTestId("resolve-type-filter-all").click();
    const preview = page.getByTestId("batch-preview-open");
    await expect(preview).toBeDisabled();
    await expect(preview).toHaveAttribute("title", /Exact만 선택하세요/);
  });

  test("NOV-22 verify manual all types switch still works", async ({ page }) => {
    await openResolveWorkspace(page);
    await page.getByTestId("resolve-type-filter-all").click();
    await expect(page.getByTestId("resolve-type-filter-all")).toHaveClass(/bg-primary/);
    await page.getByTestId("resolve-type-filter-exact").click();
    await expect(page.getByTestId("resolve-type-filter-exact")).toHaveClass(/bg-primary/);
    await expect(page.getByTestId("batch-preview-open")).toBeEnabled({ timeout: 15_000 });
  });

  test("NOV-24 facet collapsed by default and expands to five modes", async ({ page }) => {
    await openResolveWorkspace(page);
    const panel = page.getByTestId("resolve-facet-panel");
    await expect(panel).toHaveAttribute("data-state", "collapsed");
    await expandResolveFacet(page);
    for (const mode of ["action", "groups", "move", "all", "conflicts"] as const) {
      await expect(page.getByTestId(`resolve-facet-${mode}`)).toBeVisible();
    }
    await panel.getByRole("button", { name: /검토 보기|▾/ }).click();
    await expect(panel).toHaveAttribute("data-state", "collapsed");
  });

  test("NOV-21 auto-loads all filtered rows without scroll", async ({ page }) => {
    await openResolveWorkspace(page);
    await expandResolveFacet(page);
    await page.getByTestId("resolve-facet-all").click();
    await expect(page.getByTestId("batch-loading-all")).toBeHidden({ timeout: 30_000 });
    const countLine = page
      .getByTestId("batch-exclude-all-filtered")
      .locator("xpath=ancestor::div[contains(@class,'border-t')]")
      .getByText(/필터.*로드/);
    await expect(countLine).toBeVisible();
    const text = await countLine.innerText();
    const filterMatch = text.match(/필터\s+([\d,]+)/);
    const loadMatch = text.match(/로드\s+([\d,]+)/);
    expect(filterMatch && loadMatch).toBeTruthy();
    const filtered = Number(filterMatch![1].replace(/,/g, ""));
    const loaded = Number(loadMatch![1].replace(/,/g, ""));
    expect(loaded).toBe(filtered);
    expect(filtered).toBeGreaterThan(200);
  });

  test("NOV-23 wide detail drawer closed on entry, opens on row select", async ({ page }) => {
    await page.setViewportSize({ width: 1920, height: 900 });
    await openResolveWorkspace(page);
    const drawer = page.getByTestId("resolve-detail-drawer");
    await expect(drawer).toHaveAttribute("data-state", "closed");
    const firstRow = page.getByTestId(/^grid-row-/).first();
    await expect(firstRow).toBeVisible({ timeout: 15_000 });
    await firstRow.click();
    await expect(drawer).toHaveAttribute("data-state", "open");
    await expect(page.getByTestId("detail-panel")).toBeVisible();
    await page.getByTestId("detail-panel-close").click();
    await expect(drawer).toHaveAttribute("data-state", "closed");
  });

  test("NOV-20 scan resolve preview without checkbox selection", async ({ page }) => {
    await page.goto("/");
    await runScanToSuccess(page);
    await page.getByTestId("work-mode-tab-resolve").click();
    await expect(page.getByTestId("shell-file-dock")).toHaveAttribute("data-state", "collapsed");
    const resolveGrid = page.getByTestId("resolve-review-grid");
    await expect(resolveGrid).toBeVisible({ timeout: 15_000 });
    await expect(resolveGrid.locator('input[type="checkbox"]')).toHaveCount(0);
    await prepareExecutableMoveFilter(page);
    await openApplyDialog(page);
    await expect(page.getByTestId("apply-preview-run")).toBeVisible();
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
    await prepareExecutableMoveFilter(page);
    await openApplyDialog(page);
    await clickApplyPreviewRun(page);
    await expect(page.getByTestId("apply-preview-error")).toBeVisible();
    await expect(page.getByTestId("apply-confirm-run")).toHaveCount(0);
  });

  test("review grid horizontal scroll exposes action target conf headers", async ({ page }) => {
    await page.setViewportSize({ width: 1920, height: 900 });
    await openResolveWorkspace(page);
    const resolveGrid = page.getByTestId("resolve-review-grid");
    const scrollBody = resolveGrid.getByTestId("grid-scroll-body");
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
    const resolveGrid = page.getByTestId("resolve-review-grid");
    await expect(resolveGrid.getByTestId("grid-resize-handle-name")).toHaveCount(1);
    await expect(resolveGrid.getByTestId("grid-resize-handle-proposedAction")).toHaveCount(1);
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

  test("quality tab summary and filtered footer update on tab switch", async ({ page }) => {
    await page.goto("/");
    await page.getByTestId("work-mode-tab-quality").click();
    await expect(page.getByTestId("quality-workspace")).toBeVisible({ timeout: 15_000 });
    await expect(page.getByTestId("quality-tab-summary")).toBeVisible();
    await expect(page.getByTestId("quality-grid-row-count")).toBeVisible();
    await page.getByRole("button", { name: "인코딩" }).click();
    await expect(page.getByTestId("quality-tab-active-summary")).toBeVisible();
    await page.getByRole("button", { name: "소형 파일" }).click();
    await expect(page.getByTestId("quality-grid-row-count")).toBeVisible();
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
    await page.getByTestId("settings-nav-app").click();
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

  test("PR-43 full pipeline scan duplicate move finalize", async ({ page }) => {
    await page.addInitScript(() => {
      (
        window as unknown as { __NOVELGUARD_TEST_RELAX_FINALIZE_BLOCKERS__?: boolean }
      ).__NOVELGUARD_TEST_RELAX_FINALIZE_BLOCKERS__ = true;
    });
    await page.setViewportSize({ width: 1920, height: 900 });
    await page.goto("/");
    await page.evaluate(() => {
      localStorage.removeItem("novelguard.reviewGrid.sizing.v1");
    });
    await page.reload();

    await runScanToSuccess(page);

    await openResolveWorkspace(page);
    await expect(page.getByTestId("grid-row-row-2")).toBeVisible({ timeout: 15_000 });

    await runApplyPreview(page);
    await expect(page.getByTestId("apply-confirm-run")).toBeVisible();
    await clickApplyConfirmRun(page);
    await expect(page.getByTestId("apply-open-finalize")).toBeVisible({ timeout: 15_000 });
    await page.evaluate(() => {
      (
        window as unknown as { __NOVELGUARD_TEST_PREPARE_FINALIZE_READY__?: () => void }
      ).__NOVELGUARD_TEST_PREPARE_FINALIZE_READY__?.();
    });
    await page.getByTestId("apply-open-finalize").evaluate((el) => (el as HTMLButtonElement).click());

    const finalizeDialog = page.getByTestId("finalize-subflow-dialog");
    await expect(finalizeDialog).toBeVisible();
    await expect(finalizeDialog.getByTestId("finalize-subflow-content")).toBeVisible();
    await expect(finalizeDialog.getByTestId("finalize-run-button")).toBeEnabled({ timeout: 15_000 });
    await finalizeDialog.getByTestId("finalize-run-button").click();
    await expect(finalizeDialog.getByTestId("finalize-report-button")).toBeEnabled({
      timeout: 15_000,
    });
    await expect(finalizeDialog.getByTestId("finalize-subflow-content")).toHaveAttribute(
      "data-state",
      /success|warning/,
    );
  });
});
