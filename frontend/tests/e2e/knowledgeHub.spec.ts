import { test, expect } from '@playwright/test';

test('navigate to Knowledge Hub', async ({ page }) => {
  await page.goto('http://localhost:5173/knowledge-hub');

  // Expect a title "to contain" a substring.
  await expect(page).toHaveTitle(/Knowledge Hub/);

  // Optionally, check for a specific element on the page
  await expect(page.locator('h1', { hasText: 'Knowledge Hub' })).toBeVisible();
});
