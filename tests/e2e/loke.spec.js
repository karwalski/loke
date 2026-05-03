// @ts-check
const { test, expect } = require('@playwright/test');

test.describe('loke browser UI', () => {

  test('index page loads with correct title', async ({ page }) => {
    await page.goto('/');
    await expect(page).toHaveTitle(/loke/);
  });

  test('index page shows pipeline status card', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('text=Pipeline Status')).toBeVisible();
  });

  test('index page shows all pipeline components', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('text=Privacy Pipeline')).toBeVisible();
    await expect(page.locator('text=Governance Gateway')).toBeVisible();
    await expect(page.locator('text=LLM Router')).toBeVisible();
    await expect(page.locator('text=Memory Palace').first()).toBeVisible();
    await expect(page.locator('text=Agent Framework').first()).toBeVisible();
    await expect(page.locator('text=Kill Switch').first()).toBeVisible();
  });

  test('index page shows Ollama status', async ({ page }) => {
    await page.goto('/');
    const ollamaBadge = page.locator('#ollama-badge');
    // Should transition from "checking..." to either "models loaded" or "offline"
    await page.waitForTimeout(3000);
    const text = await ollamaBadge.textContent();
    expect(text).not.toBe('checking...');
  });

  test('index page shows version info', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('text=v0.3.0').first()).toBeVisible();
  });

  test('index page shows backlog stats', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('text=Backlog')).toBeVisible();
    await expect(page.locator('text=Foundation')).toBeVisible();
  });

  test('index page shows source info', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('text=Source')).toBeVisible();
    await expect(page.locator('text=toke v3.0.0')).toBeVisible();
    await expect(page.locator('text=ooke v1.1.0')).toBeVisible();
  });

  test('header shows loke branding', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('h1')).toHaveText('loke');
    await expect(page.locator('text=local intelligence layer')).toBeVisible();
  });

  test('a11y: skip link exists', async ({ page }) => {
    await page.goto('/');
    const skipLink = page.locator('#skip-to-main');
    await expect(skipLink).toBeAttached();
  });

  test('a11y: main content has id and tabindex', async ({ page }) => {
    await page.goto('/');
    const main = page.locator('#main-content');
    await expect(main).toBeAttached();
    await expect(main).toHaveAttribute('tabindex', '-1');
  });

  test('a11y: live regions exist', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('#aria-live-polite')).toBeAttached();
    await expect(page.locator('#aria-live-assertive')).toBeAttached();
  });

  test('no console errors on page load', async ({ page }) => {
    const errors = [];
    page.on('pageerror', err => errors.push(err.message));
    await page.goto('/');
    await page.waitForTimeout(2000);
    expect(errors).toEqual([]);
  });
});
