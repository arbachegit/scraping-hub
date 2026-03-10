'use strict';

import { expect, test } from '@playwright/test';

const BASE = 'http://localhost:3002';

async function openPeopleListing(page: import('@playwright/test').Page) {
  await page.goto(`${BASE}/dashboard`, { waitUntil: 'domcontentloaded' });
  await page.waitForSelector('text=Pessoas', { timeout: 15000 });

  const pessoasModuleCard = page.locator('div.cursor-pointer', {
    hasText: 'Perfis profissionais',
  });
  await pessoasModuleCard.click();

  await expect(page.locator('text=Digite pelo menos 2 letras para buscar pessoas no banco.')).toBeVisible({
    timeout: 10000,
  });
}

test.describe('People Listing Modal', () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => {
      localStorage.setItem('token', 'test-token');
      localStorage.setItem('refresh_token', 'test-refresh-token');
      document.cookie = 'has_session=1; path=/';
    });

    await page.route('**/api/auth/me', (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          email: 'test@example.com',
          name: 'Test User',
          is_admin: true,
          role: 'superadmin',
          permissions: ['empresas', 'pessoas', 'politicos', 'mandatos', 'emendas', 'noticias'],
        }),
      })
    );

    await page.route('**/api/health', (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ version: '1.0.0', status: 'healthy' }),
      })
    );

    await page.route('**/api/stats/current', (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          stats: [],
          data_referencia: new Date().toISOString(),
          online: true,
          proxima_atualizacao_segundos: 60,
          timestamp: new Date().toISOString(),
        }),
      })
    );

    await page.route('**/api/stats/history*', (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          historico: {},
          categorias: [],
          total_registros: 0,
          timestamp: new Date().toISOString(),
        }),
      })
    );

    await page.route('**/api/stats/snapshot', (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ success: true }),
      })
    );
  });

  test('opens DB listing flow instead of the old people modal', async ({ page }) => {
    await page.route('**/api/people/list-enriched*', (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ success: true, count: 0, people: [] }),
      })
    );

    await openPeopleListing(page);

    await expect(page.locator('text=Buscar Pessoa')).toHaveCount(0);
    await expect(page.locator('input[placeholder*="Digite pelo menos 2 letras"]')).toBeVisible();
  });

  test('does not query before the second letter', async ({ page }) => {
    let requestCount = 0;

    await page.route('**/api/people/list-enriched*', async (route) => {
      requestCount += 1;
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ success: true, count: 0, people: [] }),
      });
    });

    await openPeopleListing(page);

    const searchInput = page.locator('input[placeholder*="Digite pelo menos 2 letras"]');
    await searchInput.fill('F');
    await page.waitForTimeout(500);
    expect(requestCount).toBe(0);

    await searchInput.fill('Fe');
    await page.waitForTimeout(500);
    expect(requestCount).toBe(1);
  });

  test('renders DB table columns after a 2-letter search', async ({ page }) => {
    await page.route('**/api/people/list-enriched*', (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          count: 1,
          people: [
            {
              id: '1',
              nome: 'Fernando Arbache',
              empresa: 'IconsAI',
              cidade: 'Sao Paulo',
              estado: 'SP',
              cnae: '6201-5/01',
              descricao: 'Desenvolvimento de software',
              cnae_descricao: 'Desenvolvimento de software',
              email: 'fernando@example.com',
              phone: '(11) 99999-0000',
              telefone: '(11) 99999-0000',
            },
          ],
        }),
      })
    );

    await openPeopleListing(page);

    const searchInput = page.locator('input[placeholder*="Digite pelo menos 2 letras"]');
    await searchInput.fill('Fe');

    await expect(page.locator('th:has-text("Nome")')).toBeVisible();
    await expect(page.locator('th:has-text("Empresa")')).toBeVisible();
    await expect(page.locator('th:has-text("Cidade")')).toBeVisible();
    await expect(page.locator('th:has-text("UF")')).toBeVisible();
    await expect(page.locator('th:has-text("CNAE")')).toBeVisible();
    await expect(page.locator('th:has-text("Descricao")')).toBeVisible();
    await expect(page.locator('th:has-text("Email")')).toBeVisible();
    await expect(page.locator('th:has-text("Phone")')).toBeVisible();

    await expect(page.locator('text=Fernando Arbache')).toBeVisible();
    await expect(page.locator('text=IconsAI')).toBeVisible();
    await expect(page.locator('text=fernando@example.com')).toBeVisible();
  });
});
