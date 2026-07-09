import { useState, type FormEvent } from 'react'
import { fetchRecommendation } from '../lib/api'
import type { RecommendResponse } from '../lib/types'

interface RecommendPanelProps {
  category: string
}

export function RecommendPanel({ category }: RecommendPanelProps) {
  const [amountSom, setAmountSom] = useState(50_000_000)
  const [termMonths, setTermMonths] = useState(12)
  const [collateralOk, setCollateralOk] = useState(false)
  const [result, setResult] = useState<RecommendResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setError(null)
    try {
      const response = await fetchRecommendation(category, amountSom, termMonths, collateralOk)
      setResult(response)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Xatolik yuz berdi')
    }
  }

  return (
    <section className="recommend-panel">
      <h3>Tavsiya olish</h3>
      <form onSubmit={handleSubmit}>
        <label>
          Summa (so'm)
          <input
            type="number"
            min={1_000_000}
            step={1_000_000}
            value={amountSom}
            onChange={(e) => setAmountSom(Number(e.target.value))}
          />
        </label>
        <label>
          Muddat (oy)
          <input
            type="number"
            min={1}
            max={120}
            value={termMonths}
            onChange={(e) => setTermMonths(Number(e.target.value))}
          />
        </label>
        <label>
          <input
            type="checkbox"
            checked={collateralOk}
            onChange={(e) => setCollateralOk(e.target.checked)}
          />
          Garov taqdim eta olaman
        </label>
        <button type="submit">Tavsiya olish</button>
      </form>
      {error && <p className="error-state">{error}</p>}
      {result && (
        <div className="recommend-result">
          {result.recommendations.map((item) => (
            <p key={`${item.bank}-${item.product_name}`}>
              <strong>{item.bank}</strong> — {item.product_name} (ball: {item.score})
            </p>
          ))}
          <p>{result.explanation}</p>
        </div>
      )}
    </section>
  )
}
