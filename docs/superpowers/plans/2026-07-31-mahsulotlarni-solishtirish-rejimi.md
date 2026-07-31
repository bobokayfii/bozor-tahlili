# Mahsulotlarni solishtirish rejimi ("Compare mode") Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let a user select up to 3 products in the rate board, then open a full-screen modal that compares them side by side with the cheapest/best value highlighted per attribute.

**Architecture:** Pure frontend feature (no backend/API changes). Selection state (`Set<string>` of `bank::product_name` keys) lives in `App.tsx` and flows down to `ProductTable` (checkboxes), `CompareBar` (floating summary + open/clear), and `CompareModal` (transposed comparison). A new `compareLogic.ts` module holds the pure, unit-tested "which value is best" logic so it never touches the DOM.

**Tech Stack:** React 19 + TypeScript + Vite. Vitest + React Testing Library for tests (existing project setup, see `frontend/package.json`).

## Global Constraints

- Spec: `docs/superpowers/specs/2026-07-31-mahsulotlarni-solishtirish-rejimi-design.md` — every requirement in it must be covered by a task below.
- **Do not run `git commit` after individual tasks.** The user explicitly asked for a single commit at the very end of the whole plan (last task only). Still run `git add`-equivalent staging is not needed mid-plan — just leave changes uncommitted until the final task.
- All new UI strings go through the existing `frontend/src/lib/i18n.ts` UZ/RU dictionary — never hardcode user-facing text in a component.
- Max 3 products comparable at once (`MAX_COMPARE = 3`), enforced in `App.tsx` and passed down as a prop — never hardcoded inside `ProductTable`.
- Reuse `getCompareKey` (bank + product name) as the single identity for a selectable product everywhere (checkbox, chip, modal column) — never re-derive it differently in two places.
- Follow existing per-file local-formatter convention (see `MarketPulse.tsx`'s local `formatRateRange`/`formatTermRange`) rather than introducing a new shared formatting module — this codebase already duplicates these small formatters per component intentionally.

---

### Task 1: `compareLogic.ts` — pure best-value logic

**Files:**
- Create: `frontend/src/lib/compareLogic.ts`
- Test: `frontend/src/lib/compareLogic.test.ts`

**Interfaces:**
- Produces: `getCompareKey(product: Product): string`, `bestIndexesByNumber(values: (number | null)[], direction: 'lower' | 'higher'): Set<number>`, `bestIndexesByGracePeriod(values: (number | null)[]): Set<number>` — all three are consumed by `ProductTable.tsx`, `CompareBar.tsx`, and `CompareModal.tsx` in later tasks.

- [ ] **Step 1: Write the failing tests**

Create `frontend/src/lib/compareLogic.test.ts`:

```ts
import { describe, it, expect } from 'vitest'
import type { Product } from './types'
import { getCompareKey, bestIndexesByNumber, bestIndexesByGracePeriod } from './compareLogic'

const base: Product = {
  bank: 'SQB',
  category: 'avtokredit',
  product_name: 'SQB Avtokredit',
  rate_min: 24.9,
  rate_max: 27.9,
  term_min_months: 12,
  term_max_months: 60,
  amount_max_som: 800_000_000,
  requires_collateral: true,
  down_payment_pct: 30,
  grace_period_months: 3,
  payment_method: 'Annuitet',
  special_terms: null,
  scraped_at: '2026-07-08T10:00:00Z',
}

describe('getCompareKey', () => {
  it('combines bank and product name with a double-colon separator', () => {
    expect(getCompareKey(base)).toBe('SQB::SQB Avtokredit')
  })

  it('produces different keys for the same bank with two different products', () => {
    const other: Product = { ...base, product_name: 'SQB Avtokredit Plus' }
    expect(getCompareKey(base)).not.toBe(getCompareKey(other))
  })
})

describe('bestIndexesByNumber', () => {
  it('marks the single lowest value as best when direction is lower', () => {
    expect(bestIndexesByNumber([24.9, 20.9, 27.9], 'lower')).toEqual(new Set([1]))
  })

  it('marks the single highest value as best when direction is higher', () => {
    expect(bestIndexesByNumber([800, 900, 500], 'higher')).toEqual(new Set([1]))
  })

  it('marks all tied values as best', () => {
    expect(bestIndexesByNumber([20, 20, 30], 'lower')).toEqual(new Set([0, 1]))
  })

  it('ignores null values when picking the best', () => {
    expect(bestIndexesByNumber([null, 20, 30], 'lower')).toEqual(new Set([1]))
  })

  it('returns an empty set when every value is null', () => {
    expect(bestIndexesByNumber([null, null], 'lower')).toEqual(new Set())
  })
})

describe('bestIndexesByGracePeriod', () => {
  it('marks entries with a positive grace period as best', () => {
    expect(bestIndexesByGracePeriod([3, 0, null])).toEqual(new Set([0]))
  })

  it('marks all entries with a positive grace period when more than one qualifies', () => {
    expect(bestIndexesByGracePeriod([3, 6, 0])).toEqual(new Set([0, 1]))
  })

  it('returns an empty set when nobody has a grace period', () => {
    expect(bestIndexesByGracePeriod([0, null, 0])).toEqual(new Set())
  })
})
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd frontend && npx vitest run src/lib/compareLogic.test.ts`
Expected: FAIL — `Cannot find module './compareLogic'` (file doesn't exist yet)

- [ ] **Step 3: Write the implementation**

Create `frontend/src/lib/compareLogic.ts`:

```ts
import type { Product } from './types'

export function getCompareKey(product: Product): string {
  return `${product.bank}::${product.product_name}`
}

export function bestIndexesByNumber(values: (number | null)[], direction: 'lower' | 'higher'): Set<number> {
  const defined = values
    .map((value, index) => ({ value, index }))
    .filter((entry): entry is { value: number; index: number } => entry.value !== null)

  if (defined.length === 0) return new Set()

  const best =
    direction === 'lower'
      ? Math.min(...defined.map((entry) => entry.value))
      : Math.max(...defined.map((entry) => entry.value))

  return new Set(defined.filter((entry) => entry.value === best).map((entry) => entry.index))
}

export function bestIndexesByGracePeriod(values: (number | null)[]): Set<number> {
  return new Set(
    values.reduce<number[]>((acc, value, index) => {
      if (value !== null && value > 0) acc.push(index)
      return acc
    }, []),
  )
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd frontend && npx vitest run src/lib/compareLogic.test.ts`
Expected: PASS — all 9 tests green

---

### Task 2: i18n — add compare-mode translation keys

**Files:**
- Modify: `frontend/src/lib/i18n.ts`

**Interfaces:**
- Produces: five new `TranslationKey` members (`compareCheckboxLabel`, `compareBarLabel`, `compareBarClear`, `compareButton`, `compareModalTitle`) consumed by `ProductTable.tsx`, `CompareBar.tsx`, `CompareModal.tsx` in later tasks.

- [ ] **Step 1: Add the UZ keys**

In `frontend/src/lib/i18n.ts`, insert before the closing `closeLabel: 'Yopish',` line's trailing comma inside the `uz` object (i.e. right after line 53 `closeLabel: 'Yopish',`):

```ts
    closeLabel: 'Yopish',
    compareCheckboxLabel: 'Solishtirish uchun tanlash',
    compareBarLabel: 'Tanlangan mahsulotlar',
    compareBarClear: 'Bekor qilish',
    compareButton: 'Solishtirish',
    compareModalTitle: 'Mahsulotlarni solishtirish',
```

- [ ] **Step 2: Add the RU keys**

Insert right after the matching `closeLabel: 'Закрыть',` line inside the `ru` object:

```ts
    closeLabel: 'Закрыть',
    compareCheckboxLabel: 'Выбрать для сравнения',
    compareBarLabel: 'Выбранные продукты',
    compareBarClear: 'Отмена',
    compareButton: 'Сравнить',
    compareModalTitle: 'Сравнение продуктов',
```

- [ ] **Step 3: Verify the project still type-checks**

Run: `cd frontend && npx tsc -b --noEmit`
Expected: no errors (the `as const satisfies Record<Lang, Record<string, string>>` check confirms both `uz` and `ru` now have matching keys)

---

### Task 3: `ProductTable.tsx` — selection checkboxes

**Files:**
- Modify: `frontend/src/components/ProductTable.tsx`
- Modify: `frontend/src/components/ProductTable.test.tsx`

**Interfaces:**
- Consumes: `getCompareKey` from `frontend/src/lib/compareLogic.ts` (Task 1)
- Produces: new optional props on `ProductTable` — `compareKeys?: Set<string>` (default `new Set()`), `onToggleCompare?: (key: string) => void` (default no-op), `maxCompare?: number` (default `3`). These are consumed by `App.tsx` in Task 7.

- [ ] **Step 1: Write the failing tests**

In `frontend/src/components/ProductTable.test.tsx`, add these imports at the top (alongside the existing ones) and these tests at the end of the `describe('ProductTable', ...)` block, right before the final closing `})`:

```ts
import userEvent from '@testing-library/user-event'
```

```tsx
  it('calls onToggleCompare with the compare key when a row checkbox is clicked', async () => {
    const user = userEvent.setup()
    const onToggleCompare = vi.fn()
    renderWithLanguage(
      <ProductTable products={[sampleProduct]} onToggleCompare={onToggleCompare} compareKeys={new Set()} />,
    )
    await user.click(screen.getByRole('checkbox'))
    expect(onToggleCompare).toHaveBeenCalledWith('SQB::SQB Avtokredit')
  })

  it('checks the checkbox for a product whose key is already in compareKeys', () => {
    renderWithLanguage(
      <ProductTable products={[sampleProduct]} compareKeys={new Set(['SQB::SQB Avtokredit'])} />,
    )
    expect(screen.getByRole('checkbox')).toBeChecked()
  })

  it('disables unchecked checkboxes once maxCompare is reached, but keeps the checked one enabled', () => {
    renderWithLanguage(
      <ProductTable
        products={[sampleProduct, cheaperProduct]}
        compareKeys={new Set(['SQB::SQB Avtokredit'])}
        maxCompare={1}
      />,
    )
    const checkboxes = screen.getAllByRole('checkbox')
    const checked = checkboxes.find((box) => (box as HTMLInputElement).checked)
    const unchecked = checkboxes.find((box) => !(box as HTMLInputElement).checked)
    expect(checked).toBeEnabled()
    expect(unchecked).toBeDisabled()
  })

  it('does not render a checkbox for unavailable bank rows', () => {
    const unavailableBanks: UnavailableBank[] = [{ bank: 'TBC Bank', reason: 'Mahsulot mavjud emas' }]
    renderWithLanguage(<ProductTable products={[sampleProduct]} unavailableBanks={unavailableBanks} />)
    expect(screen.getAllByRole('checkbox')).toHaveLength(1)
  })
```

Also add `vi` to the vitest import at the top of the file (currently `import { describe, it, expect } from 'vitest'` — change to `import { describe, it, expect, vi } from 'vitest'`).

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd frontend && npx vitest run src/components/ProductTable.test.tsx`
Expected: FAIL — `Unable to find role="checkbox"` (no checkbox rendered yet)

- [ ] **Step 3: Implement the checkbox column**

In `frontend/src/components/ProductTable.tsx`:

Replace the imports block (lines 1-6) with:

```tsx
import type { Product, UnavailableBank } from '../lib/types'
import { isHouseBank } from '../lib/bank'
import { getBankLogo } from '../lib/bankLogos'
import { getProductColumns } from '../lib/productColumns'
import { getCompareKey } from '../lib/compareLogic'
import { useLanguage } from '../lib/LanguageContext'
import { translate, type Lang } from '../lib/i18n'
```

Replace the `ProductTableProps` interface (lines 8-14) with:

```tsx
interface ProductTableProps {
  products: Product[]
  isLoading?: boolean
  schema?: string
  category?: string
  unavailableBanks?: UnavailableBank[]
  compareKeys?: Set<string>
  onToggleCompare?: (key: string) => void
  maxCompare?: number
}
```

Replace `gridTemplateColumns` (lines 45-48) with a version that reserves a leading checkbox column:

```tsx
function gridTemplateColumns(extraColumnCount: number): string {
  const extraTracks = Array(extraColumnCount).fill('minmax(0, 1fr)').join(' ')
  return `24px 32px minmax(0, 1.1fr) minmax(0, 1.3fr) minmax(0, 0.85fr) minmax(0, 0.6fr) ${extraTracks}`.trim()
}
```

In `SkeletonRows` (lines 50-83), add a leading empty cell to both the head row and each skeleton row. The head row (lines 57-68) becomes:

```tsx
      <div className="rate-board-head" style={gridStyle}>
        <span aria-hidden="true" />
        <span>{t('tableRank')}</span>
        <span>{t('tableBank')}</span>
        <span className="rate-head-product">{t('tableProduct')}</span>
        <span>{t('tableRate')}</span>
        <span className="rate-head-term">{t('tableTerm')}</span>
        {columns.map((column) => (
          <span className="rate-head-extra" key={column.key}>
            {column.label}
          </span>
        ))}
      </div>
```

And each skeleton row (lines 70-79) becomes:

```tsx
        <div className="rate-row rate-row-skeleton" key={row} style={gridStyle}>
          <span aria-hidden="true" />
          <span className="skeleton skeleton-rank" />
          <span className="skeleton skeleton-bank" />
          <span className="skeleton skeleton-product" />
          <span className="skeleton skeleton-figure" />
          <span className="skeleton skeleton-term" />
          {columns.map((column) => (
            <span className="skeleton skeleton-term" key={column.key} />
          ))}
        </div>
```

In the main `ProductTable` function signature (lines 85-91), add the new props with defaults:

```tsx
export function ProductTable({
  products,
  isLoading = false,
  schema,
  category,
  unavailableBanks = [],
  compareKeys = new Set(),
  onToggleCompare = () => {},
  maxCompare = 3,
}: ProductTableProps) {
```

Update the main head row (lines 110-121) to match the skeleton's leading empty cell:

```tsx
      <div className="rate-board-head" style={gridStyle}>
        <span aria-hidden="true" />
        <span>{t('tableRank')}</span>
        <span>{t('tableBank')}</span>
        <span className="rate-head-product">{t('tableProduct')}</span>
        <span>{t('tableRate')}</span>
        <span className="rate-head-term">{t('tableTerm')}</span>
        {columns.map((column) => (
          <span className="rate-head-extra" key={column.key}>
            {column.label}
          </span>
        ))}
      </div>
```

In the row-rendering `map` (lines 122-163), add the checkbox as the first child of each row. Replace the `return (...)` block (lines 131-162) with:

```tsx
        const key = getCompareKey(product)
        const isSelected = compareKeys.has(key)
        const isCheckboxDisabled = !isSelected && compareKeys.size >= maxCompare

        return (
          <div className={rowClass} key={`${product.bank}-${product.product_name}-${index}`} style={gridStyle}>
            <input
              type="checkbox"
              className="compare-checkbox"
              checked={isSelected}
              disabled={isCheckboxDisabled}
              aria-label={t('compareCheckboxLabel')}
              onChange={() => onToggleCompare(key)}
            />
            <span className="rate-rank">{String(index + 1).padStart(2, '0')}</span>
            <span className="rate-bank">
              {getBankLogo(product.bank) && (
                <img src={getBankLogo(product.bank)} alt="" className="rate-bank-logo" />
              )}
              <span className="rate-bank-name">{product.bank}</span>
              {house && <span className="house-flag">{t('houseFlag')}</span>}
            </span>
            <span className="rate-product">{product.product_name}</span>
            <span className="rate-figure">
              <span className="rate-figure-value">
                {product.rate_min === product.rate_max
                  ? `${product.rate_min}%`
                  : `${product.rate_min}% – ${product.rate_max}%`}
              </span>
              <span className="rate-bar-track">
                <span className="rate-bar-fill" style={{ width: `${fillPct}%` }} />
              </span>
            </span>
            <span className="rate-term">{formatTerm(product, lang)}</span>
            {columns.map((column) => {
              const value = column.render(product)
              return (
                <span className="rate-extra" key={column.key} title={value}>
                  {value}
                </span>
              )
            })}
          </div>
        )
```

Finally, update the unavailable-banks row (lines 164-177) to add the leading empty cell and shift the reason's grid span from column 3 to column 4:

```tsx
      {unavailableBanks.map((item) => (
        <div className="rate-row rate-row-unavailable" key={item.bank} style={gridStyle}>
          <span aria-hidden="true" />
          <span className="rate-rank" aria-hidden="true">
            —
          </span>
          <span className="rate-bank">
            {getBankLogo(item.bank) && <img src={getBankLogo(item.bank)} alt="" className="rate-bank-logo" />}
            <span className="rate-bank-name">{item.bank}</span>
          </span>
          <span className="rate-unavailable-reason" style={{ gridColumn: '4 / -1' }}>
            {translateReason(item.reason, lang)}
          </span>
        </div>
      ))}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd frontend && npx vitest run src/components/ProductTable.test.tsx`
Expected: PASS — all tests green (17 previous + 4 new)

---

### Task 4: `CompareBar.tsx` — floating selection summary

**Files:**
- Create: `frontend/src/components/CompareBar.tsx`
- Create: `frontend/src/components/CompareBar.test.tsx`

**Interfaces:**
- Consumes: `getCompareKey` from `frontend/src/lib/compareLogic.ts` (Task 1), `getBankLogo` from `frontend/src/lib/bankLogos.ts`, `useLanguage` from `frontend/src/lib/LanguageContext.tsx`
- Produces: `CompareBar` component with props `{ products: Product[]; onRemove: (key: string) => void; onOpen: () => void; onClear: () => void }`, consumed by `App.tsx` in Task 7.

- [ ] **Step 1: Write the failing tests**

Create `frontend/src/components/CompareBar.test.tsx`:

```tsx
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi } from 'vitest'
import type { ReactElement } from 'react'
import { CompareBar } from './CompareBar'
import { LanguageProvider } from '../lib/LanguageContext'
import type { Product } from '../lib/types'

function renderWithLanguage(ui: ReactElement) {
  return render(<LanguageProvider>{ui}</LanguageProvider>)
}

const sqb: Product = {
  bank: 'SQB',
  category: 'avtokredit',
  product_name: 'SQB Avtokredit',
  rate_min: 24.9,
  rate_max: 27.9,
  term_min_months: 12,
  term_max_months: 60,
  amount_max_som: 800_000_000,
  requires_collateral: true,
  down_payment_pct: 30,
  grace_period_months: 3,
  payment_method: 'Annuitet',
  special_terms: null,
  scraped_at: '2026-07-08T10:00:00Z',
}

const nbu: Product = { ...sqb, bank: 'NBU', product_name: 'NBU Avtokredit' }

describe('CompareBar', () => {
  it('renders nothing when there are no selected products', () => {
    const { container } = renderWithLanguage(
      <CompareBar products={[]} onRemove={vi.fn()} onOpen={vi.fn()} onClear={vi.fn()} />,
    )
    expect(container).toBeEmptyDOMElement()
  })

  it('renders one chip per selected product', () => {
    renderWithLanguage(<CompareBar products={[sqb, nbu]} onRemove={vi.fn()} onOpen={vi.fn()} onClear={vi.fn()} />)
    expect(screen.getByText('SQB')).toBeInTheDocument()
    expect(screen.getByText('NBU')).toBeInTheDocument()
  })

  it('calls onRemove with the compare key when a chip is removed', async () => {
    const user = userEvent.setup()
    const onRemove = vi.fn()
    renderWithLanguage(<CompareBar products={[sqb]} onRemove={onRemove} onOpen={vi.fn()} onClear={vi.fn()} />)
    await user.click(screen.getByRole('button', { name: 'Yopish' }))
    expect(onRemove).toHaveBeenCalledWith('SQB::SQB Avtokredit')
  })

  it('calls onOpen when the compare button is clicked', async () => {
    const user = userEvent.setup()
    const onOpen = vi.fn()
    renderWithLanguage(<CompareBar products={[sqb, nbu]} onRemove={vi.fn()} onOpen={onOpen} onClear={vi.fn()} />)
    await user.click(screen.getByRole('button', { name: /Solishtirish/ }))
    expect(onOpen).toHaveBeenCalled()
  })

  it('calls onClear when the clear button is clicked', async () => {
    const user = userEvent.setup()
    const onClear = vi.fn()
    renderWithLanguage(<CompareBar products={[sqb, nbu]} onRemove={vi.fn()} onOpen={vi.fn()} onClear={onClear} />)
    await user.click(screen.getByRole('button', { name: 'Bekor qilish' }))
    expect(onClear).toHaveBeenCalled()
  })

  it('disables the compare button when only one product is selected', () => {
    renderWithLanguage(<CompareBar products={[sqb]} onRemove={vi.fn()} onOpen={vi.fn()} onClear={vi.fn()} />)
    expect(screen.getByRole('button', { name: /Solishtirish/ })).toBeDisabled()
  })
})
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd frontend && npx vitest run src/components/CompareBar.test.tsx`
Expected: FAIL — `Cannot find module './CompareBar'`

- [ ] **Step 3: Write the implementation**

Create `frontend/src/components/CompareBar.tsx`:

```tsx
import type { Product } from '../lib/types'
import { getBankLogo } from '../lib/bankLogos'
import { getCompareKey } from '../lib/compareLogic'
import { useLanguage } from '../lib/LanguageContext'

interface CompareBarProps {
  products: Product[]
  onRemove: (key: string) => void
  onOpen: () => void
  onClear: () => void
}

export function CompareBar({ products, onRemove, onOpen, onClear }: CompareBarProps) {
  const { t } = useLanguage()

  if (products.length === 0) return null

  return (
    <div className="compare-bar" role="region" aria-live="polite" aria-label={t('compareBarLabel')}>
      <ul className="compare-bar-chips">
        {products.map((product) => {
          const key = getCompareKey(product)
          const logo = getBankLogo(product.bank)
          return (
            <li className="compare-chip" key={key}>
              {logo && <img src={logo} alt="" className="compare-chip-logo" />}
              <span className="compare-chip-name">{product.bank}</span>
              <button
                type="button"
                className="compare-chip-remove"
                aria-label={t('closeLabel')}
                onClick={() => onRemove(key)}
              >
                ×
              </button>
            </li>
          )
        })}
      </ul>
      <div className="compare-bar-actions">
        <button type="button" className="compare-bar-clear" onClick={onClear}>
          {t('compareBarClear')}
        </button>
        <button
          type="button"
          className="modal-btn modal-btn-primary compare-bar-open"
          onClick={onOpen}
          disabled={products.length < 2}
        >
          {t('compareButton')} ({products.length})
        </button>
      </div>
    </div>
  )
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd frontend && npx vitest run src/components/CompareBar.test.tsx`
Expected: PASS — all 6 tests green

---

### Task 5: `CompareModal.tsx` — transposed comparison table

**Files:**
- Create: `frontend/src/components/CompareModal.tsx`
- Create: `frontend/src/components/CompareModal.test.tsx`

**Interfaces:**
- Consumes: `getCompareKey`, `bestIndexesByNumber`, `bestIndexesByGracePeriod` from `frontend/src/lib/compareLogic.ts` (Task 1); `getProductColumns` from `frontend/src/lib/productColumns.ts`; `isHouseBank` from `frontend/src/lib/bank.ts`; `getBankLogo` from `frontend/src/lib/bankLogos.ts`
- Produces: `CompareModal` component with props `{ products: Product[]; schema?: string; category?: string; onClose: () => void; onRemove: (key: string) => void }`, consumed by `App.tsx` in Task 7. Caller is responsible for only rendering it when `products.length >= 2`.

- [ ] **Step 1: Write the failing tests**

Create `frontend/src/components/CompareModal.test.tsx`:

```tsx
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi } from 'vitest'
import type { ReactElement } from 'react'
import { CompareModal } from './CompareModal'
import { LanguageProvider } from '../lib/LanguageContext'
import type { Product } from '../lib/types'

function renderWithLanguage(ui: ReactElement) {
  return render(<LanguageProvider>{ui}</LanguageProvider>)
}

const sqb: Product = {
  bank: 'SQB',
  category: 'avtokredit',
  product_name: 'SQB Avtokredit',
  rate_min: 24.9,
  rate_max: 27.9,
  term_min_months: 12,
  term_max_months: 60,
  amount_max_som: 800_000_000,
  requires_collateral: true,
  down_payment_pct: 30,
  grace_period_months: 3,
  payment_method: 'Annuitet',
  special_terms: null,
  scraped_at: '2026-07-08T10:00:00Z',
}

const nbu: Product = {
  ...sqb,
  bank: 'NBU',
  product_name: 'NBU Avtokredit',
  rate_min: 20.9,
  rate_max: 23.9,
  amount_max_som: 900_000_000,
  grace_period_months: 0,
}

describe('CompareModal', () => {
  it('renders one column per selected product with bank and product name', () => {
    renderWithLanguage(<CompareModal products={[sqb, nbu]} onClose={vi.fn()} onRemove={vi.fn()} />)
    expect(screen.getByText('SQB')).toBeInTheDocument()
    expect(screen.getByText('NBU')).toBeInTheDocument()
    expect(screen.getByText('SQB Avtokredit')).toBeInTheDocument()
    expect(screen.getByText('NBU Avtokredit')).toBeInTheDocument()
  })

  it('highlights the cheapest rate cell as best', () => {
    renderWithLanguage(<CompareModal products={[sqb, nbu]} onClose={vi.fn()} onRemove={vi.fn()} />)
    const nbuRateCell = screen.getByText('20.9% – 23.9%')
    const sqbRateCell = screen.getByText('24.9% – 27.9%')
    expect(nbuRateCell).toHaveClass('compare-cell-best')
    expect(sqbRateCell).not.toHaveClass('compare-cell-best')
  })

  it('highlights the highest amount cell as best', () => {
    renderWithLanguage(<CompareModal products={[sqb, nbu]} onClose={vi.fn()} onRemove={vi.fn()} />)
    expect(screen.getByText("900 mln so'm")).toHaveClass('compare-cell-best')
    expect(screen.getByText("800 mln so'm")).not.toHaveClass('compare-cell-best')
  })

  it('does not highlight the term row since it is a neutral attribute', () => {
    renderWithLanguage(<CompareModal products={[sqb, nbu]} onClose={vi.fn()} onRemove={vi.fn()} />)
    expect(screen.getByText('12–60 oy')).not.toHaveClass('compare-cell-best')
  })

  it('calls onRemove with the compare key when a column remove button is clicked', async () => {
    const user = userEvent.setup()
    const onRemove = vi.fn()
    renderWithLanguage(<CompareModal products={[sqb, nbu]} onClose={vi.fn()} onRemove={onRemove} />)
    const removeButtons = screen.getAllByRole('button', { name: 'Yopish' })
    await user.click(removeButtons[0])
    expect(onRemove).toHaveBeenCalledWith('SQB::SQB Avtokredit')
  })

  it('calls onClose when Escape is pressed', async () => {
    const user = userEvent.setup()
    const onClose = vi.fn()
    renderWithLanguage(<CompareModal products={[sqb, nbu]} onClose={onClose} onRemove={vi.fn()} />)
    await user.keyboard('{Escape}')
    expect(onClose).toHaveBeenCalled()
  })

  it('calls onClose when the overlay is clicked', async () => {
    const user = userEvent.setup()
    const onClose = vi.fn()
    renderWithLanguage(<CompareModal products={[sqb, nbu]} onClose={onClose} onRemove={vi.fn()} />)
    await user.click(screen.getByRole('presentation'))
    expect(onClose).toHaveBeenCalled()
  })
})
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd frontend && npx vitest run src/components/CompareModal.test.tsx`
Expected: FAIL — `Cannot find module './CompareModal'`

- [ ] **Step 3: Write the implementation**

Create `frontend/src/components/CompareModal.tsx`:

```tsx
import { useEffect, useRef } from 'react'
import type { Product } from '../lib/types'
import { isHouseBank } from '../lib/bank'
import { getBankLogo } from '../lib/bankLogos'
import { getProductColumns } from '../lib/productColumns'
import { getCompareKey, bestIndexesByNumber, bestIndexesByGracePeriod } from '../lib/compareLogic'
import { useLanguage } from '../lib/LanguageContext'
import { translate, type Lang } from '../lib/i18n'

interface CompareModalProps {
  products: Product[]
  schema?: string
  category?: string
  onClose: () => void
  onRemove: (key: string) => void
}

function formatRateRange(product: Product): string {
  return product.rate_min === product.rate_max
    ? `${product.rate_min}%`
    : `${product.rate_min}% – ${product.rate_max}%`
}

function formatTermRange(product: Product, lang: Lang): string {
  const unit = translate(lang, 'monthUnit')
  return product.term_min_months === product.term_max_months
    ? `${product.term_min_months} ${unit}`
    : `${product.term_min_months}–${product.term_max_months} ${unit}`
}

const NUMERIC_EXTRACTORS: Record<string, (product: Product) => number | null> = {
  down_payment: (product) => product.down_payment_pct,
  amount: (product) => product.amount_max_som,
}

const NUMERIC_DIRECTIONS: Record<string, 'lower' | 'higher'> = {
  down_payment: 'lower',
  amount: 'higher',
}

function cellClass(isBest: boolean): string {
  return isBest ? 'compare-cell compare-cell-best' : 'compare-cell'
}

export function CompareModal({ products, schema, category, onClose, onRemove }: CompareModalProps) {
  const { lang, t } = useLanguage()
  const cardRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', handleKeyDown)
    cardRef.current?.focus()
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [onClose])

  const columns = getProductColumns(schema, category, lang)
  const gridStyle = { gridTemplateColumns: `160px repeat(${products.length}, minmax(0, 1fr))` }
  const rateBestIndexes = bestIndexesByNumber(
    products.map((product) => product.rate_min),
    'lower',
  )

  return (
    <div className="modal-overlay" role="presentation" onClick={onClose}>
      <div
        className="modal-card compare-modal-card"
        role="dialog"
        aria-modal="true"
        aria-labelledby="compare-modal-title"
        tabIndex={-1}
        ref={cardRef}
        onClick={(event) => event.stopPropagation()}
      >
        <div className="compare-modal-head">
          <h2 id="compare-modal-title" className="modal-title">
            {t('compareModalTitle')}
          </h2>
          <button type="button" className="compare-modal-close" aria-label={t('closeLabel')} onClick={onClose}>
            ×
          </button>
        </div>

        <div className="compare-table-wrap">
          <div className="compare-row compare-row-head" style={gridStyle}>
            <span className="compare-attr-label" />
            {products.map((product) => {
              const key = getCompareKey(product)
              const logo = getBankLogo(product.bank)
              const house = isHouseBank(product.bank)
              return (
                <div className="compare-col-head" key={key}>
                  <button
                    type="button"
                    className="compare-col-remove"
                    aria-label={t('closeLabel')}
                    onClick={() => onRemove(key)}
                  >
                    ×
                  </button>
                  {logo && <img src={logo} alt="" className="compare-col-logo" />}
                  <span className="compare-col-bank">
                    {product.bank}
                    {house && <span className="house-flag">{t('houseFlag')}</span>}
                  </span>
                  <span className="compare-col-product">{product.product_name}</span>
                </div>
              )
            })}
          </div>

          <div className="compare-row" style={gridStyle}>
            <span className="compare-attr-label">{t('tableRate')}</span>
            {products.map((product, index) => (
              <span className={cellClass(rateBestIndexes.has(index))} key={getCompareKey(product)}>
                {formatRateRange(product)}
              </span>
            ))}
          </div>

          <div className="compare-row" style={gridStyle}>
            <span className="compare-attr-label">{t('tableTerm')}</span>
            {products.map((product) => (
              <span className="compare-cell" key={getCompareKey(product)}>
                {formatTermRange(product, lang)}
              </span>
            ))}
          </div>

          {columns.map((column) => {
            const isNumeric = column.key in NUMERIC_EXTRACTORS
            const bestIndexes = isNumeric
              ? bestIndexesByNumber(products.map(NUMERIC_EXTRACTORS[column.key]), NUMERIC_DIRECTIONS[column.key])
              : column.key === 'grace_period'
                ? bestIndexesByGracePeriod(products.map((product) => product.grace_period_months))
                : new Set<number>()

            return (
              <div className="compare-row" style={gridStyle} key={column.key}>
                <span className="compare-attr-label">{column.label}</span>
                {products.map((product, index) => (
                  <span className={cellClass(bestIndexes.has(index))} key={getCompareKey(product)}>
                    {column.render(product)}
                  </span>
                ))}
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd frontend && npx vitest run src/components/CompareModal.test.tsx`
Expected: PASS — all 7 tests green

---

### Task 6: `tokens.css` — visual styling for compare mode

**Files:**
- Modify: `frontend/src/styles/tokens.css`

- [ ] **Step 1: Add the compare-mode CSS block**

Insert the following new section into `frontend/src/styles/tokens.css` immediately before the `@media (max-width: 760px) {` line (currently line 1006):

```css
/* ---------- Compare mode ---------- */

.compare-checkbox {
  width: 15px;
  height: 15px;
  accent-color: var(--house);
  cursor: pointer;
}

.compare-checkbox:disabled {
  cursor: not-allowed;
  opacity: 0.4;
}

.compare-bar {
  position: fixed;
  bottom: 24px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 90;
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 10px 14px 10px 16px;
  border-radius: 999px;
  background: var(--paper);
  border: 1px solid var(--line-strong);
  box-shadow: 0 12px 32px rgba(20, 22, 31, 0.18);
  animation: content-in 220ms cubic-bezier(0.16, 1, 0.3, 1) backwards;
}

.compare-bar-chips {
  display: flex;
  align-items: center;
  gap: 8px;
  list-style: none;
  margin: 0;
  padding: 0;
}

.compare-chip {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 5px 6px 5px 10px;
  border-radius: 999px;
  background: var(--paper-sunk);
  font-size: 12.5px;
  font-weight: 600;
  color: var(--ink);
}

.compare-chip-logo {
  width: 16px;
  height: 16px;
  object-fit: contain;
}

.compare-chip-remove {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
  border: none;
  background: transparent;
  color: var(--ink-faint);
  font-size: 14px;
  line-height: 1;
  cursor: pointer;
  padding: 0;
}

.compare-chip-remove:hover {
  color: var(--negative);
}

.compare-bar-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  padding-left: 6px;
  border-left: 1px solid var(--line);
}

.compare-bar-clear {
  border: none;
  background: transparent;
  color: var(--ink-soft);
  font-size: 12.5px;
  font-weight: 600;
  cursor: pointer;
  padding: 6px 4px;
}

.compare-bar-clear:hover {
  color: var(--ink);
}

.compare-bar-open {
  white-space: nowrap;
}

.compare-bar-open:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.compare-modal-card {
  max-width: 960px;
}

.compare-modal-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.compare-modal-close {
  border: none;
  background: transparent;
  color: var(--ink-faint);
  font-size: 20px;
  line-height: 1;
  cursor: pointer;
  padding: 0 2px;
}

.compare-modal-close:hover {
  color: var(--ink);
}

.compare-table-wrap {
  margin-top: 8px;
  overflow-x: auto;
  border: 1px solid var(--line);
  border-radius: var(--radius);
}

.compare-row {
  display: grid;
  gap: 12px;
  align-items: center;
  padding: 12px 16px;
  border-top: 1px solid var(--line);
}

.compare-row:first-child {
  border-top: none;
}

.compare-row-head {
  align-items: flex-start;
  background: var(--paper-sunk);
  padding: 16px;
}

.compare-attr-label {
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--ink-faint);
}

.compare-col-head {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  text-align: center;
}

.compare-col-remove {
  position: absolute;
  top: -6px;
  right: 0;
  border: none;
  background: transparent;
  color: var(--ink-faint);
  font-size: 15px;
  line-height: 1;
  cursor: pointer;
  padding: 2px;
}

.compare-col-remove:hover {
  color: var(--negative);
}

.compare-col-logo {
  width: 32px;
  height: 32px;
  object-fit: contain;
}

.compare-col-bank {
  display: flex;
  align-items: center;
  gap: 6px;
  font-weight: 800;
  font-size: 14.5px;
  color: var(--ink);
}

.compare-col-product {
  font-size: 12px;
  color: var(--ink-soft);
}

.compare-cell {
  text-align: center;
  font-size: 13.5px;
  font-weight: 600;
  color: var(--ink);
  font-variant-numeric: tabular-nums;
}

.compare-cell-best {
  color: var(--good);
  position: relative;
}

.compare-cell-best::before {
  content: '';
  position: absolute;
  inset: -6px -8px;
  border-radius: 6px;
  background: var(--good-soft);
  z-index: -1;
}
```

- [ ] **Step 2: Add mobile and reduced-motion adjustments**

Inside the existing `@media (max-width: 760px) { ... }` block (starts at what is now further down the file after the insertion above), add this rule alongside the other mobile overrides:

```css
  .compare-bar {
    left: 16px;
    right: 16px;
    bottom: 16px;
    transform: none;
    flex-wrap: wrap;
  }
```

Inside the existing `@media (prefers-reduced-motion: reduce) { ... }` block, add `.compare-bar` to the list of selectors that get `animation: none`:

```css
  .main-content,
  .sidebar-submenu,
  .market-pulse,
  .compare-bar,
  .skeleton {
    animation: none;
  }
```

- [ ] **Step 3: Manually verify no visual regressions**

Run: `cd frontend && npm run dev`
Open the app in a browser, confirm the existing rate board, sidebar, and topbar still look correct (checkbox column doesn't break alignment) before moving on. This step has no automated assertion — it's a visual sanity check per project convention for CSS-only changes.

---

### Task 7: Wire selection state into `App.tsx`

**Files:**
- Modify: `frontend/src/App.tsx`

**Interfaces:**
- Consumes: `getCompareKey` from `frontend/src/lib/compareLogic.ts` (Task 1); `CompareBar` (Task 4); `CompareModal` (Task 5); the new `ProductTable` props from Task 3.

- [ ] **Step 1: Update imports**

Replace the import block at the top of `frontend/src/App.tsx` (lines 1-12) with:

```tsx
import { useEffect, useState } from 'react'
import { Sidebar } from './components/Sidebar'
import { ProductTable } from './components/ProductTable'
import { MarketPulse } from './components/MarketPulse'
import { ExportMenu } from './components/ExportMenu'
import { RefreshDataButton } from './components/RefreshDataButton'
import { CompareBar } from './components/CompareBar'
import { CompareModal } from './components/CompareModal'
import { fetchCategories, fetchProducts, fetchUnavailableBanks } from './lib/api'
import { getCategoryHeading } from './lib/categoryGroups'
import { getCompareKey } from './lib/compareLogic'
import { useLanguage } from './lib/LanguageContext'
import type { Lang } from './lib/i18n'
import type { Category, Product, UnavailableBank } from './lib/types'
import logoIcon from './assets/logo-icon.png'

const MAX_COMPARE = 3
```

- [ ] **Step 2: Add compare state and handlers**

In the `App` function, right after the existing state declarations (lines 49-54: `categories` through `error`), add:

```tsx
  const [compareKeys, setCompareKeys] = useState<Set<string>>(new Set())
  const [isCompareModalOpen, setIsCompareModalOpen] = useState(false)
```

Right after the `activeCategoryData`/`activeLabel`/`lastUpdated` derivations (after line 104, before the `return`), add:

```tsx
  const compareProducts = products.filter((product) => compareKeys.has(getCompareKey(product)))

  function handleSelectCategory(categoryKey: string) {
    setActiveCategory(categoryKey)
    setCompareKeys(new Set())
    setIsCompareModalOpen(false)
  }

  function handleToggleCompare(key: string) {
    const willRemove = compareKeys.has(key)
    const nextSize = willRemove ? compareKeys.size - 1 : Math.min(compareKeys.size + 1, MAX_COMPARE)
    if (willRemove && nextSize < 2) {
      setIsCompareModalOpen(false)
    }
    setCompareKeys((prev) => {
      const next = new Set(prev)
      if (next.has(key)) {
        next.delete(key)
      } else if (next.size < MAX_COMPARE) {
        next.add(key)
      }
      return next
    })
  }

  function handleClearCompare() {
    setCompareKeys(new Set())
    setIsCompareModalOpen(false)
  }
```

- [ ] **Step 3: Pass the new props to `Sidebar` and `ProductTable`, and render `CompareBar`/`CompareModal`**

Replace the `<Sidebar ... />` line (line 120) with:

```tsx
        <Sidebar categories={categories} activeCategory={activeCategory} onSelect={handleSelectCategory} />
```

Replace the `<ProductTable ... />` block (lines 136-142) with:

```tsx
          <ProductTable
            products={products}
            isLoading={isLoading}
            schema={activeCategoryData?.schema}
            category={activeCategory ?? undefined}
            unavailableBanks={unavailableBanks}
            compareKeys={compareKeys}
            onToggleCompare={handleToggleCompare}
            maxCompare={MAX_COMPARE}
          />
```

Replace the closing of the component (lines 143-147, i.e. the final `</main>`, `</div>`, `</div>`, `)`, `}`) with:

```tsx
        </main>
      </div>
      <CompareBar
        products={compareProducts}
        onRemove={handleToggleCompare}
        onOpen={() => setIsCompareModalOpen(true)}
        onClear={handleClearCompare}
      />
      {isCompareModalOpen && compareProducts.length >= 2 && (
        <CompareModal
          products={compareProducts}
          schema={activeCategoryData?.schema}
          category={activeCategory ?? undefined}
          onClose={() => setIsCompareModalOpen(false)}
          onRemove={handleToggleCompare}
        />
      )}
    </div>
  )
}
```

- [ ] **Step 4: Type-check and run the full test suite**

Run: `cd frontend && npx tsc -b --noEmit && npx vitest run`
Expected: no type errors, all test files pass (existing suites unaffected, new ones from Tasks 1, 3, 4, 5 green)

- [ ] **Step 5: Manual verification in the browser**

Run: `cd frontend && npm run dev`

In the browser:
1. Open any category with 2+ banks, check 2 checkboxes → confirm the compare bar appears at the bottom with two chips.
2. Check a 3rd → bar shows 3 chips; confirm remaining unchecked checkboxes in the table are visually disabled.
3. Click "Solishtirish (3)" → modal opens with 3 columns, cheapest rate highlighted green.
4. Remove a column inside the modal down to 1 → modal auto-closes.
5. Switch to a different category in the sidebar → confirm the compare bar disappears (selection was cleared).
6. Toggle UZ/RU with the language switch → confirm all new compare-mode text translates.

---

### Task 8: Final commit

**Files:** none (staging only)

- [ ] **Step 1: Review everything staged**

Run: `git status` and `git diff` to confirm only the intended files changed:
`frontend/src/lib/compareLogic.ts`, `frontend/src/lib/compareLogic.test.ts`, `frontend/src/lib/i18n.ts`, `frontend/src/components/ProductTable.tsx`, `frontend/src/components/ProductTable.test.tsx`, `frontend/src/components/CompareBar.tsx`, `frontend/src/components/CompareBar.test.tsx`, `frontend/src/components/CompareModal.tsx`, `frontend/src/components/CompareModal.test.tsx`, `frontend/src/components/App.tsx`, `frontend/src/styles/tokens.css`, plus this plan/spec doc pair under `docs/superpowers/`.

- [ ] **Step 2: Stage and commit everything in one commit**

```bash
git add frontend/src/lib/compareLogic.ts frontend/src/lib/compareLogic.test.ts frontend/src/lib/i18n.ts frontend/src/components/ProductTable.tsx frontend/src/components/ProductTable.test.tsx frontend/src/components/CompareBar.tsx frontend/src/components/CompareBar.test.tsx frontend/src/components/CompareModal.tsx frontend/src/components/CompareModal.test.tsx frontend/src/App.tsx frontend/src/styles/tokens.css docs/superpowers/plans/2026-07-31-mahsulotlarni-solishtirish-rejimi.md
git commit -m "$(cat <<'EOF'
feat: add product comparison mode to the rate board

Select up to 3 products via checkboxes, then compare them side by
side in a modal with the best value per attribute highlighted.
EOF
)"
```

- [ ] **Step 3: Verify the commit**

Run: `git status` and `git log -1 --stat`
Expected: working tree clean (aside from any genuinely unrelated pre-existing untracked files), commit shows all listed files.
