import { describe, it, expect, vi, beforeEach } from 'vitest'
import { fetchCategories, fetchProducts, fetchRecommendation } from './api'

describe('api client', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('fetchCategories returns parsed JSON on success', async () => {
    const mockCategories = [{ key: 'avtokredit', label: 'Avtokredit', schema: 'credit' }]
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({ ok: true, json: async () => mockCategories }),
    )

    const result = await fetchCategories()
    expect(result).toEqual(mockCategories)
  })

  it('fetchProducts throws with the status code when the response is not ok', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 500 }))

    await expect(fetchProducts('avtokredit')).rejects.toThrow("Mahsulotlarni yuklab bo'lmadi: 500")
  })

  it('fetchProducts requests the given category as a query param', async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => [] })
    vi.stubGlobal('fetch', fetchMock)

    await fetchProducts('mikroqarz')

    const calledUrl = fetchMock.mock.calls[0][0] as URL
    expect(calledUrl.toString()).toBe('http://localhost:8000/products?category=mikroqarz')
  })

  it('fetchRecommendation posts criteria as a JSON body', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ recommendations: [], explanation: 'test' }),
    })
    vi.stubGlobal('fetch', fetchMock)

    await fetchRecommendation('avtokredit', 50_000_000, 12, true)

    const [url, options] = fetchMock.mock.calls[0]
    expect(url).toBe('http://localhost:8000/recommend')
    expect(JSON.parse(options.body)).toEqual({
      category: 'avtokredit',
      amount_som: 50_000_000,
      term_months: 12,
      collateral_ok: true,
    })
  })
})
