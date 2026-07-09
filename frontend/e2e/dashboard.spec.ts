import { test, expect } from '@playwright/test'

test('selecting a sidebar category updates the product table heading', async ({ page }) => {
  await page.goto('/')

  await expect(page.getByRole('button', { name: 'Mikroqarz (oflayn)' })).toBeVisible()

  await page.getByRole('button', { name: 'Mikroqarz (oflayn)' }).click()

  await expect(page.getByRole('heading', { name: 'Mikroqarz (oflayn)' })).toBeVisible()
})
