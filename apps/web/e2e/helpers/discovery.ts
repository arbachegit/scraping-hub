import { Page } from '@playwright/test';

export interface DiscoveredPage {
  url: string;
  title: string;
  links: string[];
}

export async function discoverLinks(
  page: Page,
  baseURL: string
): Promise<string[]> {
  const links = await page.$$eval(
    'a[href]',
    (anchors, base) => {
      return anchors
        .map((a) => a.getAttribute('href'))
        .filter((href): href is string => href !== null)
        .filter((href) => {
          try {
            const url = new URL(href, base);
            return url.origin === new URL(base).origin && !href.startsWith('#');
          } catch {
            return false;
          }
        })
        .map((href) => new URL(href, base).pathname);
    },
    baseURL
  );

  return [...new Set(links)];
}

export async function getInteractiveElements(page: Page) {
  return page.$$eval(
    'button, a, [role="button"], input, select, textarea, [onclick]',
    (elements) =>
      elements
        .filter((el) => {
          const style = window.getComputedStyle(el);
          return (
            style.display !== 'none' &&
            style.visibility !== 'hidden' &&
            (el as HTMLElement).offsetParent !== null
          );
        })
        .map((el, idx) => ({
          tag: el.tagName.toLowerCase(),
          text: (el.textContent || '').trim().slice(0, 50),
          selector: el.id
            ? `#${el.id}`
            : el.className && typeof el.className === 'string'
              ? `.${el.className.split(' ')[0]}`
              : `${el.tagName.toLowerCase()}:nth-of-type(${idx + 1})`,
          type: (el as HTMLInputElement).type || null,
          isDestructive: /delete|remover|excluir|apagar|drop|destroy/i.test(
            el.textContent || ''
          ),
        }))
  );
}
