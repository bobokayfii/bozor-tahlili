import { describe, it, expect, vi, beforeEach } from 'vitest'
import { fetchCategories, fetchProducts, fetchRecommendation, fetchUnavailableBanks } from './api'

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

  it('fetchUnavailableBanks returns parsed JSON on success', async () => {
    const mockBanks = [{ bank: 'TBC Bank', reason: 'Mahsulot mavjud emas' }]
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => mockBanks }))

    const result = await fetchUnavailableBanks('avtokredit')
    expect(result).toEqual(mockBanks)
  })

  it('fetchUnavailableBanks throws with the status code when the response is not ok', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 500 }))

    await expect(fetchUnavailableBanks('avtokredit')).rejects.toThrow(
      "Mavjud bo'lmagan banklar ro'yxatini yuklab bo'lmadi: 500",
    )
  })

  it('fetchRecommendation posts the criteria as JSON and returns parsed JSON on success', async () => {
    const mockResponse = { recommendations: [{ bank: 'SQB', product_name: 'Mikroqarz', score: 0.9 }], explanation: 'SQB tavsiya etiladi.' }
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => mockResponse })
    vi.stubGlobal('fetch', fetchMock)

    const request = { category: 'mikroqarz', amount_som: 50_000_000, term_months: 12, collateral_ok: true }
    const result = await fetchRecommendation(request)

    expect(result).toEqual(mockResponse)
    const [url, options] = fetchMock.mock.calls[0]
    expect(url).toBe('http://localhost:8000/recommend')
    expect(options.method).toBe('POST')
    expect(JSON.parse(options.body)).toEqual(request)
  })

  it('fetchRecommendation throws with the status code when the response is not ok', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 500 }))

    await expect(
      fetchRecommendation({ category: 'mikroqarz', amount_som: 1, term_months: 1, collateral_ok: true }),
    ).rejects.toThrow("AI tavsiyasini olib bo'lmadi: 500")
  })
})
