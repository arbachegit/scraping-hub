import { Page, expect } from '@playwright/test';

export async function safeClick(
  page: Page,
  selector: string
): Promise<boolean> {
  try {
    const element = page.locator(selector).first();
    await expect(element).toBeVisible({ timeout: 5000 });
    await expect(element).toBeEnabled({ timeout: 5000 });
    await element.click({ timeout: 10000 });
    return true;
  } catch {
    return false;
  }
}

export async function safeFill(
  page: Page,
  selector: string,
  value: string
): Promise<boolean> {
  try {
    const element = page.locator(selector).first();
    await expect(element).toBeVisible({ timeout: 5000 });
    await expect(element).toBeEnabled({ timeout: 5000 });
    await element.fill(value, { timeout: 10000 });
    return true;
  } catch {
    return false;
  }
}

export async function waitForNavigation(
  page: Page,
  action: () => Promise<void>
) {
  const currentURL = page.url();
  await action();
  await page.waitForLoadState('networkidle', { timeout: 15000 }).catch(() => {});

  const newURL = page.url();
  return newURL !== currentURL;
}

export function generateSyntheticData(type: string): string {
  const data: Record<string, string> = {
    text: 'Test Input',
    email: 'test@example.com',
    password: 'TestPassword123!',
    tel: '+5511999999999',
    number: '42',
    url: 'https://example.com',
    search: 'test search',
  };
  return data[type] || 'test';
}
