import { Page, ConsoleMessage, Request, Response } from '@playwright/test';

export interface GuardReport {
  consoleErrors: string[];
  pageErrors: string[];
  failedRequests: string[];
  serverErrors: { url: string; status: number }[];
}

export function setupGuards(page: Page): GuardReport {
  const report: GuardReport = {
    consoleErrors: [],
    pageErrors: [],
    failedRequests: [],
    serverErrors: [],
  };

  page.on('console', (msg: ConsoleMessage) => {
    if (msg.type() === 'error') {
      report.consoleErrors.push(msg.text());
    }
  });

  page.on('pageerror', (error: Error) => {
    report.pageErrors.push(error.message);
  });

  page.on('requestfailed', (request: Request) => {
    report.failedRequests.push(`${request.method()} ${request.url()}`);
  });

  page.on('response', (response: Response) => {
    const status = response.status();
    if (status >= 400) {
      report.serverErrors.push({ url: response.url(), status });
    }
  });

  return report;
}

export function assertNoErrors(
  report: GuardReport,
  allowedPatterns: RegExp[] = []
) {
  const filteredErrors = report.consoleErrors.filter(
    (err) => !allowedPatterns.some((p) => p.test(err))
  );

  if (filteredErrors.length > 0) {
    throw new Error(`Console errors detected:\n${filteredErrors.join('\n')}`);
  }

  if (report.pageErrors.length > 0) {
    throw new Error(`Page errors detected:\n${report.pageErrors.join('\n')}`);
  }

  const serverErrors5xx = report.serverErrors.filter((e) => e.status >= 500);
  if (serverErrors5xx.length > 0) {
    throw new Error(
      `Server errors detected:\n${serverErrors5xx.map((e) => `${e.status} ${e.url}`).join('\n')}`
    );
  }
}
