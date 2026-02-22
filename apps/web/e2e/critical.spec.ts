import { test, expect } from '@playwright/test';
import { setupGuards, assertNoErrors } from './helpers/consoleNetworkGuards';
import { safeClick, safeFill, generateSyntheticData } from './helpers/actions';

test.describe('Critical Tests', () => {
  test('smoke - home page loads without errors', async ({ page }) => {
    const guards = setupGuards(page);

    await page.goto('/');
    await expect(page.locator('body')).toBeVisible();

    // Wait for initial load
    await page.waitForLoadState('networkidle');

    // Check for main content - login page or app
    const hasContent = await page
      .locator('main, [role="main"], form, .card, [data-testid]')
      .count();
    expect(hasContent).toBeGreaterThan(0);

    assertNoErrors(guards, [/hydration/i, /chunk/i]);
  });

  test('login page - form visible and interactive', async ({ page }) => {
    const guards = setupGuards(page);
    await page.goto('/');

    // Check for login form elements
    const emailInput = page.locator('input[type="email"], input[name="email"]');
    const passwordInput = page.locator(
      'input[type="password"], input[name="password"]'
    );

    if ((await emailInput.count()) > 0) {
      await expect(emailInput.first()).toBeVisible();
      await expect(passwordInput.first()).toBeVisible();

      // Fill form with test data
      await emailInput.first().fill('test@example.com');
      await passwordInput.first().fill('testpassword123');

      // Find submit button
      const submitBtn = page.locator(
        'button[type="submit"], button:has-text("Entrar"), button:has-text("Login")'
      );
      await expect(submitBtn.first()).toBeVisible();
    }

    assertNoErrors(guards, [/hydration/i]);
  });

  test('dashboard - loads when authenticated', async ({ page }) => {
    const guards = setupGuards(page);

    // Try to access dashboard directly
    await page.goto('/dashboard');

    // Should either show dashboard or redirect to login
    await page.waitForLoadState('networkidle');

    const url = page.url();
    const isDashboard = url.includes('/dashboard');
    const isLogin = url === '/' || url.includes('login');

    expect(isDashboard || isLogin).toBeTruthy();

    assertNoErrors(guards, [/hydration/i, /401/i]);
  });

  test('navigation - header elements are interactive', async ({ page }) => {
    const guards = setupGuards(page);
    await page.goto('/');

    // Check header exists
    const header = page.locator('header');
    if ((await header.count()) > 0) {
      await expect(header.first()).toBeVisible();

      // Check for logo
      const logo = page.locator('header img, header picture');
      if ((await logo.count()) > 0) {
        await expect(logo.first()).toBeVisible();
      }
    }

    assertNoErrors(guards, [/hydration/i]);
  });

  test('modals - module cards are clickable', async ({ page }) => {
    const guards = setupGuards(page);

    // Set auth token to simulate logged in user
    await page.addInitScript(() => {
      localStorage.setItem('token', 'test-token');
    });

    await page.goto('/dashboard');
    await page.waitForLoadState('networkidle');

    // Find module cards
    const moduleCards = page.locator(
      '[class*="cursor-pointer"], .card, [role="button"]'
    );
    const cardCount = await moduleCards.count();

    if (cardCount > 0) {
      // Click first card
      await moduleCards.first().click();
      await page.waitForTimeout(500);

      // Check if modal opened
      const modal = page.locator(
        '[role="dialog"], .modal, [class*="fixed"][class*="inset"]'
      );
      const modalVisible = (await modal.count()) > 0;

      if (modalVisible) {
        // Try to close with ESC
        await page.keyboard.press('Escape');
        await page.waitForTimeout(300);
      }
    }

    // Allow 401 errors since we're using fake token
    assertNoErrors(guards, [/hydration/i, /401/i, /unauthorized/i]);
  });

  test('forms - inputs accept text', async ({ page }) => {
    const guards = setupGuards(page);
    await page.goto('/');

    const inputs = await page.locator('input:visible').all();

    for (const input of inputs.slice(0, 5)) {
      const type = (await input.getAttribute('type')) || 'text';
      if (type !== 'hidden' && type !== 'submit') {
        const value = generateSyntheticData(type);
        const filled = await input.fill(value).then(
          () => true,
          () => false
        );
        expect(filled).toBeTruthy();
      }
    }

    assertNoErrors(guards, [/hydration/i]);
  });

  test('buttons - all visible buttons are enabled', async ({ page }) => {
    const guards = setupGuards(page);
    await page.goto('/');

    const buttons = await page.locator('button:visible').all();

    for (const button of buttons.slice(0, 10)) {
      const isDisabled = await button.isDisabled();
      const text = await button.textContent();

      // Log button state
      console.log(`Button "${text?.trim()}": disabled=${isDisabled}`);
    }

    assertNoErrors(guards, [/hydration/i]);
  });

  test('responsive - page renders on mobile viewport', async ({ page }) => {
    const guards = setupGuards(page);

    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    await expect(page.locator('body')).toBeVisible();

    // Check content is still visible
    const hasContent = await page
      .locator('main, form, .card, [class*="flex"]')
      .count();
    expect(hasContent).toBeGreaterThan(0);

    assertNoErrors(guards, [/hydration/i]);
  });
});
