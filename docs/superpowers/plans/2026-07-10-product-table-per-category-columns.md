# Product Table Per-Category Columns Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the platform's product comparison table render the same set of columns, per product category, as the corresponding table in the reference deck `Raqobatchi_banklar_tahlili_ChB_31_03_2026 y].pptx`, instead of one fixed column set for every category.

**Architecture:** Ground truth was extracted directly from the pptx by reading each slide's text-box shapes and their x/y positions (the pptx does not use real PowerPoint tables — each "table" is a grid of individually positioned text boxes). Comparing column headers across all 18 slides shows exactly two column patterns among the platform's 11 registered credit categories:

- **`credit_down_payment`** (Avtokredit ×5 variants, Ipoteka ×2 variants — slides 3–7, 12–13): Mahsulot nomi, Yillik foiz stavkasi, Muddati, **Boshlang'ich badal**, Imtiyozli davri, Kredit miqdori, To'lov usuli, Kredit kafolati.
- **`credit_special_terms`** (Mikroqarz oflayn/onlayn, Kredit kartalari, Iste'mol krediti — slides 8–11): Mahsulot nomi, Yillik foiz stavkasi, Muddati, Kredit miqdori, Imtiyozli davri, **Maxsus shartlari**, To'lov usuli, Kredit kafolati.

The two patterns have the same column count and mostly the same columns — they differ only in one slot (`Boshlang'ich badal` vs `Kredit miqdori` first, and `Kredit miqdori` vs `Maxsus shartlari` in the middle). The backend's existing `Category.schema` field (currently a stub always set to `"credit"`) becomes the discriminator. The frontend gets a new `productColumns.ts` module mapping schema → ordered column definitions, and `ProductTable` renders columns from that list instead of a hardcoded JSX block.

**Tech Stack:** Python 3 / FastAPI / pytest (backend), React 19 / TypeScript / Vitest / React Testing Library (frontend).

## Global Constraints

- Do not touch `docs/superpowers/plans/2026-07-08-mahsulot-taksonomiya-va-frontend.md` — it documents a prior completed plan verbatim; it is history, not living config.
- Column order and presence must match the pptx exactly per category family (see Architecture section) — do not invent additional columns.
- Keep the existing 11 category keys and labels in `categories.py` unchanged — only the `schema` value changes.
- No new dependencies.

---

## File Map

- Modify: `categories.py` — assign `schema="credit_down_payment"` or `schema="credit_special_terms"` per category.
- Modify: `tests/test_categories.py` — replace the single-schema assertion with one per schema family.
- Modify: `tests/api/test_main.py` — fix the hardcoded `"credit"` schema assertion.
- Create: `frontend/src/lib/productColumns.ts` — schema → column list mapping + amount formatter.
- Create: `frontend/src/lib/productColumns.test.ts` — unit tests for the above.
- Modify: `frontend/src/components/ProductTable.tsx` — accept a `schema` prop, render columns from `getProductColumns(schema)`.
- Modify: `frontend/src/components/ProductTable.test.tsx` — add schema-specific column tests.
- Modify: `frontend/src/App.tsx` — pass the active category's `schema` down to `ProductTable`.
- Modify: `frontend/src/styles/tokens.css` — extend `.rate-board-head` / `.rate-row` grid from 9 to 10 tracks.

---

### Task 1: Backend — split `Category.schema` into two real values

**Files:**
- Modify: `categories.py`
- Modify: `tests/test_categories.py`
- Modify: `tests/api/test_main.py:120`

**Interfaces:**
- Produces: `CATEGORIES` entries now have `schema` equal to either `"credit_down_payment"` or `"credit_special_terms"` (was always `"credit"`). No signature changes to `Category`, `category_keys()`, or the `/categories` endpoint — only the data values change.

- [ ] **Step 1: Write the failing tests**

Replace the contents of `tests/test_categories.py` with:

```python
from categories import CATEGORIES, category_keys


def test_categories_contains_eleven_entries():
    assert len(CATEGORIES) == 11


def test_all_category_keys_are_unique():
    keys = category_keys()
    assert len(keys) == len(set(keys))


def test_existing_categories_keep_original_keys():
    keys = category_keys()
    for legacy_key in ["avtokredit", "mikroqarz", "kredit_karta", "istemol_krediti"]:
        assert legacy_key in keys


def test_avtokredit_and_ipoteka_categories_use_down_payment_schema():
    down_payment_keys = {
        "avtokredit",
        "avtokredit_ikkilamchi",
        "avtokredit_brend_birlamchi",
        "avtokredit_brend_ikkilamchi",
        "avtokredit_elektro",
        "ipoteka_tijorat",
        "ipoteka_davlat",
    }
    by_key = {c.key: c for c in CATEGORIES}
    for key in down_payment_keys:
        assert by_key[key].schema == "credit_down_payment", key


def test_mikroqarz_karta_and_istemol_categories_use_special_terms_schema():
    special_terms_keys = {
        "mikroqarz",
        "mikroqarz_onlayn",
        "kredit_karta",
        "istemol_krediti",
    }
    by_key = {c.key: c for c in CATEGORIES}
    for key in special_terms_keys:
        assert by_key[key].schema == "credit_special_terms", key


def test_every_category_has_a_known_schema():
    known_schemas = {"credit_down_payment", "credit_special_terms"}
    assert all(c.schema in known_schemas for c in CATEGORIES)
```

Also update the one assertion in `tests/api/test_main.py` that hardcodes the old value — change line 120 from:

```python
    assert data[0]["schema"] == "credit"
```

to:

```python
    assert data[0]["schema"] == "credit_down_payment"
```

(`data[0]` is `avtokredit`, the first entry in `CATEGORIES`, which belongs to the down-payment family.)

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_categories.py tests/api/test_main.py -v`
Expected: `test_avtokredit_and_ipoteka_categories_use_down_payment_schema`, `test_mikroqarz_karta_and_istemol_categories_use_special_terms_schema`, and `test_list_categories_returns_eleven_entries` FAIL (schema is still `"credit"` for everything).

- [ ] **Step 3: Update `categories.py`**

Replace the `CATEGORIES` list in `categories.py` with:

```python
CATEGORIES: list[Category] = [
    Category(key="avtokredit", label_uz="Avtokredit (birlamchi bozor)", schema="credit_down_payment"),
    Category(
        key="avtokredit_ikkilamchi",
        label_uz="Avtokredit (ikkilamchi bozor)",
        schema="credit_down_payment",
    ),
    Category(
        key="avtokredit_brend_birlamchi",
        label_uz="Brendli avtokredit — birlamchi (GM, BYD, KIA, Hyundai, Renault, LADA, Volkswagen, Skoda, Chery)",
        schema="credit_down_payment",
    ),
    Category(
        key="avtokredit_brend_ikkilamchi",
        label_uz="Brendli avtokredit — ikkilamchi (GM, BYD, KIA, Hyundai, Renault, LADA, Volkswagen, Skoda, Chery)",
        schema="credit_down_payment",
    ),
    Category(key="avtokredit_elektro", label_uz="Elektromobil avtokrediti", schema="credit_down_payment"),
    Category(key="mikroqarz", label_uz="Mikroqarz (oflayn)", schema="credit_special_terms"),
    Category(key="mikroqarz_onlayn", label_uz="Mikroqarz (onlayn)", schema="credit_special_terms"),
    Category(key="kredit_karta", label_uz="Kredit kartalari", schema="credit_special_terms"),
    Category(key="istemol_krediti", label_uz="Iste'mol krediti", schema="credit_special_terms"),
    Category(key="ipoteka_tijorat", label_uz="Ipoteka krediti (tijorat)", schema="credit_down_payment"),
    Category(
        key="ipoteka_davlat",
        label_uz="Ipoteka krediti (Iqtisodiyot va moliya vazirligi mablag'lari hisobidan)",
        schema="credit_down_payment",
    ),
]
```

Leave the `Category` dataclass and `category_keys()` function untouched.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_categories.py tests/api/test_main.py -v`
Expected: PASS (all tests green).

- [ ] **Step 5: Commit**

```bash
git add categories.py tests/test_categories.py tests/api/test_main.py
git commit -m "feat: split category schema into credit_down_payment and credit_special_terms"
```

---

### Task 2: Frontend — column schema module

**Files:**
- Create: `frontend/src/lib/productColumns.ts`
- Create: `frontend/src/lib/productColumns.test.ts`

**Interfaces:**
- Consumes: `Product` type from `frontend/src/lib/types.ts` (fields: `down_payment_pct: number | null`, `grace_period_months: number | null`, `amount_max_som: number`, `special_terms: string | null`, `payment_method: string | null`, `requires_collateral: boolean`).
- Produces: `export interface ProductColumn { key: string; label: string; render: (product: Product) => string }` and `export function getProductColumns(schema: string | undefined): ProductColumn[]`. Task 3 imports both.

- [ ] **Step 1: Write the failing test**

Create `frontend/src/lib/productColumns.test.ts`:

```typescript
import { describe, it, expect } from 'vitest'
import { getProductColumns } from './productColumns'
import type { Product } from './types'

const baseProduct: Product = {
  bank: 'SQB',
  category: 'avtokredit',
  product_name: 'Test mahsulot',
  rate_min: 20,
  rate_max: 25,
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

describe('getProductColumns', () => {
  it('returns the down-payment column set in pptx order for credit_down_payment', () => {
    const columns = getProductColumns('credit_down_payment')
    expect(columns.map((c) => c.label)).toEqual([
      "Boshlang'ich badal",
      'Imtiyozli davr',
      'Kredit miqdori',
      "To'lov usuli",
      'Kredit kafolati',
    ])
  })

  it('returns the special-terms column set in pptx order for credit_special_terms', () => {
    const columns = getProductColumns('credit_special_terms')
    expect(columns.map((c) => c.label)).toEqual([
      'Kredit miqdori',
      'Imtiyozli davr',
      'Maxsus shartlari',
      "To'lov usuli",
      'Kredit kafolati',
    ])
  })

  it('defaults to the down-payment column set for an unknown or missing schema', () => {
    expect(getProductColumns(undefined).map((c) => c.label)).toContain("Boshlang'ich badal")
    expect(getProductColumns('something_else').map((c) => c.label)).toContain("Boshlang'ich badal")
  })

  it('renders down payment percentage or a dash when absent', () => {
    const [downPayment] = getProductColumns('credit_down_payment')
    expect(downPayment.render(baseProduct)).toBe('30%')
    expect(downPayment.render({ ...baseProduct, down_payment_pct: null })).toBe('—')
  })

  it('renders grace period in months or a dash when absent', () => {
    const [, gracePeriod] = getProductColumns('credit_down_payment')
    expect(gracePeriod.render(baseProduct)).toBe('3 oy')
    expect(gracePeriod.render({ ...baseProduct, grace_period_months: null })).toBe('—')
  })

  it('formats the credit amount in millions of soum', () => {
    const [, , amount] = getProductColumns('credit_down_payment')
    expect(amount.render(baseProduct)).toBe("800 mln so'm")
    expect(amount.render({ ...baseProduct, amount_max_som: 41_000_000 })).toBe("41 mln so'm")
    expect(amount.render({ ...baseProduct, amount_max_som: 1_012_500_000 })).toBe("1012.5 mln so'm")
  })

  it('renders special terms text or a dash when absent', () => {
    // credit_special_terms order is [amount, gracePeriod, specialTerms, paymentMethod, collateral]
    const [, , specialTerms] = getProductColumns('credit_special_terms')
    expect(specialTerms.render({ ...baseProduct, special_terms: 'Kredit yuklamasi hisobga olinadi' })).toBe(
      'Kredit yuklamasi hisobga olinadi',
    )
    expect(specialTerms.render({ ...baseProduct, special_terms: null })).toBe('—')
  })

  it('renders payment method or a dash when absent', () => {
    const [, , , paymentMethod] = getProductColumns('credit_down_payment')
    expect(paymentMethod.render(baseProduct)).toBe('Annuitet')
    expect(paymentMethod.render({ ...baseProduct, payment_method: null })).toBe('—')
  })

  it("renders collateral as Bor/Yo'q", () => {
    const [, , , , collateral] = getProductColumns('credit_down_payment')
    expect(collateral.render(baseProduct)).toBe('Bor')
    expect(collateral.render({ ...baseProduct, requires_collateral: false })).toBe("Yo'q")
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/lib/productColumns.test.ts`
Expected: FAIL with "Failed to resolve import './productColumns'" (module doesn't exist yet).

- [ ] **Step 3: Write the implementation**

Create `frontend/src/lib/productColumns.ts`:

```typescript
import type { Product } from './types'

export interface ProductColumn {
  key: string
  label: string
  render: (product: Product) => string
}

function formatAmount(amount: number): string {
  const millions = Math.round((amount / 1_000_000) * 10) / 10
  return `${millions} mln so'm`
}

const downPaymentColumn: ProductColumn = {
  key: 'down_payment',
  label: "Boshlang'ich badal",
  render: (product) => (product.down_payment_pct !== null ? `${product.down_payment_pct}%` : '—'),
}

const gracePeriodColumn: ProductColumn = {
  key: 'grace_period',
  label: 'Imtiyozli davr',
  render: (product) => (product.grace_period_months !== null ? `${product.grace_period_months} oy` : '—'),
}

const amountColumn: ProductColumn = {
  key: 'amount',
  label: 'Kredit miqdori',
  render: (product) => formatAmount(product.amount_max_som),
}

const specialTermsColumn: ProductColumn = {
  key: 'special_terms',
  label: 'Maxsus shartlari',
  render: (product) => product.special_terms ?? '—',
}

const paymentMethodColumn: ProductColumn = {
  key: 'payment_method',
  label: "To'lov usuli",
  render: (product) => product.payment_method ?? '—',
}

const collateralColumn: ProductColumn = {
  key: 'collateral',
  label: 'Kredit kafolati',
  render: (product) => (product.requires_collateral ? 'Bor' : "Yo'q"),
}

const CREDIT_DOWN_PAYMENT_COLUMNS: ProductColumn[] = [
  downPaymentColumn,
  gracePeriodColumn,
  amountColumn,
  paymentMethodColumn,
  collateralColumn,
]

const CREDIT_SPECIAL_TERMS_COLUMNS: ProductColumn[] = [
  amountColumn,
  gracePeriodColumn,
  specialTermsColumn,
  paymentMethodColumn,
  collateralColumn,
]

export function getProductColumns(schema: string | undefined): ProductColumn[] {
  if (schema === 'credit_special_terms') return CREDIT_SPECIAL_TERMS_COLUMNS
  return CREDIT_DOWN_PAYMENT_COLUMNS
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npx vitest run src/lib/productColumns.test.ts`
Expected: PASS (all 9 tests green).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/productColumns.ts frontend/src/lib/productColumns.test.ts
git commit -m "feat: add per-category product column schema"
```

---

### Task 3: Frontend — ProductTable renders columns dynamically

**Files:**
- Modify: `frontend/src/components/ProductTable.tsx`
- Modify: `frontend/src/components/ProductTable.test.tsx`
- Modify: `frontend/src/styles/tokens.css:449,462`

**Interfaces:**
- Consumes: `getProductColumns` from Task 2 (`frontend/src/lib/productColumns.ts`).
- Produces: `ProductTable` now accepts an optional `schema?: string` prop in addition to the existing `products` and `isLoading` props.

- [ ] **Step 1: Write the failing tests**

Replace `frontend/src/components/ProductTable.test.tsx` with:

```tsx
import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { ProductTable } from './ProductTable'
import type { Product } from '../lib/types'

const sampleProduct: Product = {
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

const cheaperProduct: Product = {
  ...sampleProduct,
  bank: 'NBU',
  product_name: 'NBU Avtokredit',
  rate_min: 20.9,
  rate_max: 23.9,
}

describe('ProductTable', () => {
  it('shows a loading skeleton instead of the empty-state message while loading', () => {
    render(<ProductTable products={[]} isLoading />)
    expect(screen.getByLabelText('Yuklanmoqda')).toBeInTheDocument()
    expect(
      screen.queryByText("Bu toifa uchun hozircha ma'lumot yo'q — banklar sahifalari navbatda kuzatilmoqda."),
    ).not.toBeInTheDocument()
  })

  it('shows the empty-state message when there are no products', () => {
    render(<ProductTable products={[]} />)
    expect(
      screen.getByText("Bu toifa uchun hozircha ma'lumot yo'q — banklar sahifalari navbatda kuzatilmoqda."),
    ).toBeInTheDocument()
  })

  it('renders one row per product with bank and rate range', () => {
    render(<ProductTable products={[sampleProduct]} />)
    expect(screen.getByText('SQB')).toBeInTheDocument()
    expect(screen.getByText('24.9% – 27.9%')).toBeInTheDocument()
  })

  it('ranks products by cheapest rate first and flags the SQB row', () => {
    render(<ProductTable products={[sampleProduct, cheaperProduct]} />)
    const rows = screen.getAllByText(/^0[12]$/)
    expect(rows[0]).toHaveTextContent('01')
    expect(screen.getByText('NBU').closest('.rate-row')).toHaveClass('is-best')
    expect(screen.getByText('Biz')).toBeInTheDocument()
    expect(screen.getByText('SQB').closest('.rate-row')).toHaveClass('is-house')
  })

  it('defaults to the credit_down_payment column set when no schema prop is given', () => {
    render(<ProductTable products={[sampleProduct]} />)
    expect(screen.getByText("Boshlang'ich badal")).toBeInTheDocument()
    expect(screen.getByText('30%')).toBeInTheDocument()
    expect(screen.getByText('Annuitet')).toBeInTheDocument()
    expect(screen.getByText('Bor')).toBeInTheDocument()
    expect(screen.getByText('3 oy')).toBeInTheDocument()
    expect(screen.getByText('Kredit miqdori')).toBeInTheDocument()
    expect(screen.getByText("800 mln so'm")).toBeInTheDocument()
  })

  it('falls back to a dash for missing optional fields', () => {
    const productWithoutExtras: Product = {
      ...sampleProduct,
      requires_collateral: false,
      down_payment_pct: null,
      payment_method: null,
      grace_period_months: null,
    }
    render(<ProductTable products={[productWithoutExtras]} />)
    expect(screen.getAllByText('—')).toHaveLength(3)
    expect(screen.getByText("Yo'q")).toBeInTheDocument()
  })

  it('renders the credit_special_terms column set: Maxsus shartlari shown, Boshlang\'ich badal hidden', () => {
    const microloanProduct: Product = {
      ...sampleProduct,
      category: 'mikroqarz',
      down_payment_pct: null,
      special_terms: 'Kredit yuklamasi hisobga olinadi',
    }
    render(<ProductTable products={[microloanProduct]} schema="credit_special_terms" />)
    expect(screen.getByText('Maxsus shartlari')).toBeInTheDocument()
    expect(screen.getByText('Kredit yuklamasi hisobga olinadi')).toBeInTheDocument()
    expect(screen.queryByText("Boshlang'ich badal")).not.toBeInTheDocument()
  })

  it('renders the credit_down_payment column set: Boshlang\'ich badal shown, Maxsus shartlari hidden', () => {
    render(<ProductTable products={[sampleProduct]} schema="credit_down_payment" />)
    expect(screen.getByText("Boshlang'ich badal")).toBeInTheDocument()
    expect(screen.queryByText('Maxsus shartlari')).not.toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Run tests to verify the new ones fail**

Run: `cd frontend && npx vitest run src/components/ProductTable.test.tsx`
Expected: FAIL on the "defaults to the credit_down_payment column set" (no `Kredit miqdori` text yet) and both new schema tests (`schema` prop doesn't exist / `Maxsus shartlari` never renders).

- [ ] **Step 3: Rewrite `ProductTable.tsx`**

Replace `frontend/src/components/ProductTable.tsx` with:

```tsx
import type { Product } from '../lib/types'
import { isHouseBank } from '../lib/bank'
import { getBankLogo } from '../lib/bankLogos'
import { getProductColumns } from '../lib/productColumns'

interface ProductTableProps {
  products: Product[]
  isLoading?: boolean
  schema?: string
}

function SkeletonRows({ schema }: { schema?: string }) {
  const columns = getProductColumns(schema)

  return (
    <div className="rate-board" aria-busy="true" aria-label="Yuklanmoqda">
      <div className="rate-board-head">
        <span>#</span>
        <span>Bank</span>
        <span>Mahsulot</span>
        <span>Stavka</span>
        <span>Muddat</span>
        {columns.map((column) => (
          <span key={column.key}>{column.label}</span>
        ))}
      </div>
      {[0, 1, 2].map((row) => (
        <div className="rate-row rate-row-skeleton" key={row}>
          <span className="skeleton skeleton-rank" />
          <span className="skeleton skeleton-bank" />
          <span className="skeleton skeleton-product" />
          <span className="skeleton skeleton-figure" />
          <span className="skeleton skeleton-term" />
          {columns.map((column) => (
            <span className="skeleton skeleton-term" key={column.key} />
          ))}
        </div>
      ))}
    </div>
  )
}

export function ProductTable({ products, isLoading = false, schema }: ProductTableProps) {
  const columns = getProductColumns(schema)

  if (isLoading) {
    return <SkeletonRows schema={schema} />
  }

  if (products.length === 0) {
    return (
      <p className="empty-state">
        Bu toifa uchun hozircha ma'lumot yo'q — banklar sahifalari navbatda kuzatilmoqda.
      </p>
    )
  }

  const ranked = [...products].sort((a, b) => a.rate_min - b.rate_min)
  const bestRate = ranked[0].rate_min
  const lastIndex = ranked.length - 1

  return (
    <div className="rate-board">
      <div className="rate-board-head">
        <span>#</span>
        <span>Bank</span>
        <span>Mahsulot</span>
        <span>Stavka</span>
        <span>Muddat</span>
        {columns.map((column) => (
          <span key={column.key}>{column.label}</span>
        ))}
      </div>
      {ranked.map((product, index) => {
        const isBest = product.rate_min === bestRate
        const house = isHouseBank(product.bank)
        const fillPct = lastIndex === 0 ? 100 : 100 - (index / lastIndex) * 100

        const rowClass = ['rate-row', isBest && 'is-best', house && 'is-house']
          .filter(Boolean)
          .join(' ')

        return (
          <div className={rowClass} key={`${product.bank}-${product.product_name}-${index}`}>
            <span className="rate-rank">{String(index + 1).padStart(2, '0')}</span>
            <span className="rate-bank">
              {getBankLogo(product.bank) && (
                <img src={getBankLogo(product.bank)} alt="" className="rate-bank-logo" />
              )}
              <span className="rate-bank-name">{product.bank}</span>
              {house && <span className="house-flag">Biz</span>}
            </span>
            <span className="rate-product">{product.product_name}</span>
            <span className="rate-figure">
              <span className="rate-figure-value">
                {product.rate_min}% – {product.rate_max}%
              </span>
              <span className="rate-bar-track">
                <span className="rate-bar-fill" style={{ width: `${fillPct}%` }} />
              </span>
            </span>
            <span className="rate-term">
              {product.term_min_months}–{product.term_max_months} oy
            </span>
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
      })}
    </div>
  )
}
```

- [ ] **Step 4: Update the CSS grid from 9 to 10 tracks**

In `frontend/src/styles/tokens.css`, both `.rate-board-head` (line 449) and `.rate-row` (line 462) currently read:

```css
  grid-template-columns: 32px 1.1fr 1.3fr 0.85fr 0.6fr 0.75fr 0.65fr 0.5fr 0.65fr;
```

Change both occurrences to 10 tracks (adds one track for the new `Kredit miqdori`/`Maxsus shartlari` slot):

```css
  grid-template-columns: 32px 1.1fr 1.3fr 0.85fr 0.6fr 0.75fr 0.65fr 0.75fr 0.65fr 0.5fr;
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd frontend && npx vitest run src/components/ProductTable.test.tsx`
Expected: PASS (all 9 tests green).

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/ProductTable.tsx frontend/src/components/ProductTable.test.tsx frontend/src/styles/tokens.css
git commit -m "feat: render product table columns per category schema"
```

---

### Task 4: Frontend — wire the active category's schema into App

**Files:**
- Modify: `frontend/src/App.tsx:63,89`

**Interfaces:**
- Consumes: `ProductTable`'s new `schema?: string` prop (Task 3); `Category.schema` from `frontend/src/lib/types.ts` (already exists, unchanged).

- [ ] **Step 1: Update `App.tsx`**

In `frontend/src/App.tsx`, replace:

```tsx
  const activeLabel = categories.find((c) => c.key === activeCategory)?.label ?? 'Bozor Tahlili'
```

with:

```tsx
  const activeCategoryData = categories.find((c) => c.key === activeCategory)
  const activeLabel = activeCategoryData?.label ?? 'Bozor Tahlili'
```

And replace:

```tsx
          <ProductTable products={products} isLoading={isLoading} />
```

with:

```tsx
          <ProductTable products={products} isLoading={isLoading} schema={activeCategoryData?.schema} />
```

- [ ] **Step 2: Type-check**

Run: `cd frontend && npx tsc -b --noEmit`
Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/App.tsx
git commit -m "feat: pass active category schema to ProductTable"
```

---

### Task 5: Full verification

**Files:** none (verification only).

- [ ] **Step 1: Run the full backend test suite**

Run: `python -m pytest -v`
Expected: all tests pass, including the Task 1 changes.

- [ ] **Step 2: Run the full frontend test suite**

Run: `cd frontend && npx vitest run`
Expected: all tests pass, including `productColumns.test.ts` and `ProductTable.test.tsx`.

- [ ] **Step 3: Manual browser check**

Run: `cd frontend && npm run dev` (and the backend API server per its own start command), then open the app in a browser:
- Select "Avtokredit (birlamchi bozor)" in the sidebar → table header must show `Boshlang'ich badal` and `Kredit miqdori`, must NOT show `Maxsus shartlari`.
- Select "Mikroqarz (oflayn)" in the sidebar → table header must show `Maxsus shartlari` and `Kredit miqdori`, must NOT show `Boshlang'ich badal`.
- Select "Ipoteka krediti (tijorat)" → must show `Boshlang'ich badal`, matching the Avtokredit pattern.
- Select "Iste'mol krediti" or "Kredit kartalari" → must show `Maxsus shartlari`, matching the Mikroqarz pattern.
- Confirm no layout overflow/clipping at 1440px and 1920px widths (per `web/testing.md` breakpoints).

- [ ] **Step 4: Report results to the user**

Summarize pass/fail for backend tests, frontend tests, and the manual browser check. If anything fails, stop and fix before considering this plan complete — do not report success without having actually run these commands and observed the output.