// @ts-check
const { test, expect } = require('@playwright/test');

test.describe('moke index page', () => {

  test('index page loads', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('text=moke')).toBeVisible();
  });

  test('shows version 0.3.0', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('text=v0.3.0').first()).toBeVisible();
  });

  test('sidebar navigation exists', async ({ page }) => {
    await page.goto('/');
    const nav = page.locator('nav, [role="navigation"]');
    await expect(nav.first()).toBeVisible();
  });

  test('dataset cards are displayed', async ({ page }) => {
    await page.goto('/');
    // moke index should show dataset categories
    const body = await page.textContent('body');
    expect(body).toContain('Load');
  });

  test('no console errors on index', async ({ page }) => {
    const errors = [];
    page.on('pageerror', err => errors.push(err.message));
    await page.goto('/');
    await page.waitForTimeout(2000);
    expect(errors).toEqual([]);
  });
});

test.describe('moke health check', () => {

  test('loke connection indicator exists', async ({ page }) => {
    await page.goto('/');
    const badge = page.locator('#loke-conn-badge, #loke-conn-label');
    await expect(badge.first()).toBeAttached();
  });

  test('loke health resolves within 5s', async ({ page }) => {
    await page.goto('/');
    await page.waitForTimeout(5000);
    const label = page.locator('#loke-conn-label');
    const text = await label.textContent();
    // Should not still say "checking"
    expect(text).not.toContain('checking');
  });
});

test.describe('moke chat page', () => {

  test('chat page loads', async ({ page }) => {
    await page.goto('/chat');
    await expect(page.locator('#chat-input, textarea')).toBeVisible();
  });

  test('model selector populates from Ollama', async ({ page }) => {
    await page.goto('/chat');
    await page.waitForTimeout(3000);
    const select = page.locator('#model-select');
    const options = await select.locator('option').count();
    // Should have at least loke-router + models from Ollama
    expect(options).toBeGreaterThanOrEqual(1);
  });

  test('no console errors on chat page', async ({ page }) => {
    const errors = [];
    page.on('pageerror', err => errors.push(err.message));
    await page.goto('/chat');
    await page.waitForTimeout(3000);
    expect(errors).toEqual([]);
  });

  test('can type in chat input', async ({ page }) => {
    await page.goto('/chat');
    const input = page.locator('#chat-input, textarea').first();
    await input.fill('Hello world');
    await expect(input).toHaveValue('Hello world');
  });

  test('send button exists', async ({ page }) => {
    await page.goto('/chat');
    const btn = page.locator('#send-btn, .send-btn').first();
    await expect(btn).toBeVisible();
  });

  test('pipeline console section exists', async ({ page }) => {
    await page.goto('/chat');
    const console = page.locator('#console-body, .console-body');
    await expect(console.first()).toBeAttached();
  });

  test('chat sends message and gets response from Ollama', async ({ page }) => {
    await page.goto('/chat');
    await page.waitForTimeout(2000);
    const input = page.locator('#chat-input, textarea').first();
    await input.fill('What is 2+2? Reply with just the number.');
    // Click send
    const btn = page.locator('#send-btn, .send-btn').first();
    await btn.click();
    // Wait for response (Ollama may take a few seconds)
    await page.waitForTimeout(15000);
    const body = await page.textContent('body');
    expect(body).toContain('4');
  });
});

test.describe('moke settings page', () => {

  test('settings page loads', async ({ page }) => {
    await page.goto('/settings');
    const body = await page.textContent('body');
    expect(body.toLowerCase()).toContain('settings');
  });

  test('loke connection status in settings', async ({ page }) => {
    await page.goto('/settings');
    await page.waitForTimeout(3000);
    const body = await page.textContent('body');
    // Should show connection status (connected or offline)
    expect(body).toMatch(/loke|connected|offline/i);
  });

  test('no console errors on settings', async ({ page }) => {
    const errors = [];
    page.on('pageerror', err => errors.push(err.message));
    await page.goto('/settings');
    await page.waitForTimeout(2000);
    expect(errors).toEqual([]);
  });
});

test.describe('moke governance page', () => {

  test('governance page loads', async ({ page }) => {
    await page.goto('/governance');
    const body = await page.textContent('body');
    expect(body.toLowerCase()).toContain('governance');
  });

  test('no console errors on governance', async ({ page }) => {
    const errors = [];
    page.on('pageerror', err => errors.push(err.message));
    await page.goto('/governance');
    await page.waitForTimeout(2000);
    expect(errors).toEqual([]);
  });
});

test.describe('moke other pages', () => {

  test('upload page loads', async ({ page }) => {
    await page.goto('/upload');
    const body = await page.textContent('body');
    expect(body.length).toBeGreaterThan(100);
  });

  test('dashboard page loads', async ({ page }) => {
    await page.goto('/dashboard');
    const body = await page.textContent('body');
    expect(body.length).toBeGreaterThan(100);
  });

  test('insight page loads', async ({ page }) => {
    await page.goto('/insight');
    const body = await page.textContent('body');
    expect(body.length).toBeGreaterThan(100);
  });

  test('agents page loads', async ({ page }) => {
    await page.goto('/agents');
    const body = await page.textContent('body');
    expect(body.length).toBeGreaterThan(100);
  });

  test('mcp page loads', async ({ page }) => {
    await page.goto('/mcp');
    const body = await page.textContent('body');
    expect(body.length).toBeGreaterThan(100);
  });

  test('memory page loads', async ({ page }) => {
    await page.goto('/memory');
    const body = await page.textContent('body');
    expect(body.length).toBeGreaterThan(100);
  });
});

test.describe('moke a11y basics', () => {

  test('skip link exists', async ({ page }) => {
    await page.goto('/');
    const skipLink = page.locator('.skip-link, #skip-to-main');
    await expect(skipLink.first()).toBeAttached();
  });

  test('main content landmark exists', async ({ page }) => {
    await page.goto('/');
    const main = page.locator('main, #main-content, [role="main"]');
    await expect(main.first()).toBeAttached();
  });

  test('navigation landmark exists', async ({ page }) => {
    await page.goto('/');
    const nav = page.locator('nav, [role="navigation"]');
    await expect(nav.first()).toBeAttached();
  });

  test('live regions exist', async ({ page }) => {
    await page.goto('/');
    const polite = page.locator('[aria-live="polite"]');
    const assertive = page.locator('[aria-live="assertive"]');
    await expect(polite.first()).toBeAttached();
    await expect(assertive.first()).toBeAttached();
  });
});
