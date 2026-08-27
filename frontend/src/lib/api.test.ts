import { describe, it, expect, vi, beforeEach } from 'vitest'
import {
  clearToken,
  createUser,
  downloadFile,
  fetchCategories,
  fetchCurrentUser,
  fetchProductExplanation,
  fetchProducts,
  fetchRecommendation,
  fetchUnavailableBanks,
  fetchUsers,
  getExportExcelUrl,
  getToken,
  login,
  setToken,
  setUnauthorizedHandler,
  updateUser,
} from './api'

describe('api client', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    window.localStorage.clear()
    setUnauthorizedHandler(null)
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
    const mockResponse = {
      recommendations: [
        {
          bank: 'SQB',
          product_name: 'Mikroqarz',
          score: 0.9,
          rate_min: 28.0,
          rate_max: 31.0,
          term_min_months: 3,
          term_max_months: 36,
          amount_max_som: 100_000_000,
          requires_collateral: false,
          down_payment_pct: null,
          payment_method: 'Annuitet',
          grace_period_months: null,
        },
      ],
      explanation: 'SQB tavsiya etiladi.',
    }
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

  it('fetchProductExplanation posts the product as JSON and returns parsed JSON on success', async () => {
    const mockResponse = { explanation: 'HamkorBank past stavka bilan ajralib turadi.' }
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => mockResponse })
    vi.stubGlobal('fetch', fetchMock)

    const request = {
      category: 'avtokredit',
      bank: 'HamkorBank',
      product_name: 'Auto DAMAS',
      rate_min: 0.0,
      rate_max: 19.0,
      term_min_months: 60,
      term_max_months: 60,
      amount_max_som: 600_000_000,
      requires_collateral: true,
      down_payment_pct: 25.0,
    }
    const result = await fetchProductExplanation(request)

    expect(result).toEqual(mockResponse)
    const [url, options] = fetchMock.mock.calls[0]
    expect(url).toBe('http://localhost:8000/explain-product')
    expect(options.method).toBe('POST')
    expect(JSON.parse(options.body)).toEqual(request)
  })

  it('fetchProductExplanation throws with the status code when the response is not ok', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 500 }))

    await expect(
      fetchProductExplanation({
        category: 'avtokredit',
        bank: 'HamkorBank',
        product_name: 'Auto DAMAS',
        rate_min: 0.0,
        rate_max: 19.0,
        term_min_months: 60,
        term_max_months: 60,
        amount_max_som: 600_000_000,
        requires_collateral: true,
        down_payment_pct: 25.0,
      }),
    ).rejects.toThrow("AI izohini olib bo'lmadi: 500")
  })

  it('getExportExcelUrl builds a URL with category and language as query params', () => {
    const url = getExportExcelUrl('avtokredit', 'ru')
    expect(url).toBe('http://localhost:8000/export-excel?category=avtokredit&language=ru')
  })

  it('setToken/getToken/clearToken round-trip through localStorage', () => {
    expect(getToken()).toBeNull()
    setToken('abc123')
    expect(getToken()).toBe('abc123')
    clearToken()
    expect(getToken()).toBeNull()
  })

  it('fetchProducts sends the stored token as a Bearer header', async () => {
    setToken('my-token')
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => [] })
    vi.stubGlobal('fetch', fetchMock)

    await fetchProducts('mikroqarz')

    const [, options] = fetchMock.mock.calls[0]
    expect(options.headers.Authorization).toBe('Bearer my-token')
  })

  it('clears the token and calls the unauthorized handler on a 401 response', async () => {
    setToken('stale-token')
    const handler = vi.fn()
    setUnauthorizedHandler(handler)
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 401 }))

    await fetchProducts('mikroqarz').catch(() => {})

    expect(getToken()).toBeNull()
    expect(handler).toHaveBeenCalledOnce()
  })

  it('login posts credentials without requiring an existing token', async () => {
    const mockResponse = { access_token: 'new-token', username: 'admin', role: 'admin' }
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => mockResponse })
    vi.stubGlobal('fetch', fetchMock)

    const result = await login('admin', 'secret')

    expect(result).toEqual(mockResponse)
    const [url, options] = fetchMock.mock.calls[0]
    expect(url).toBe('http://localhost:8000/auth/login')
    expect(JSON.parse(options.body)).toEqual({ username: 'admin', password: 'secret' })
  })

  it('login throws on a failed response', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 401 }))
    await expect(login('admin', 'wrong')).rejects.toThrow("Login yoki parol noto'g'ri")
  })

  it('fetchCurrentUser returns the parsed user on success', async () => {
    const mockUser = { username: 'admin', role: 'admin' }
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => mockUser }))
    const result = await fetchCurrentUser()
    expect(result).toEqual(mockUser)
  })

  it('fetchUsers returns the parsed list on success', async () => {
    const mockUsers = [{ id: 1, username: 'admin', role: 'admin', created_at: '2026-01-01T00:00:00Z' }]
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => mockUsers }))
    const result = await fetchUsers()
    expect(result).toEqual(mockUsers)
  })

  it('createUser throws USERNAME_TAKEN on a 409 response', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 409 }))
    await expect(createUser({ username: 'jane', password: 'pw', role: 'user' })).rejects.toThrow('USERNAME_TAKEN')
  })

  it('updateUser throws SELF_DEMOTE on a 400 response', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 400 }))
    await expect(updateUser(1, { role: 'user' })).rejects.toThrow('SELF_DEMOTE')
  })

  it('downloadFile throws when the response is not ok', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 500 }))
    await expect(downloadFile('http://localhost:8000/export-excel', 'f.xlsx')).rejects.toThrow(
      "Faylni yuklab olib bo'lmadi: 500",
    )
  })
})
