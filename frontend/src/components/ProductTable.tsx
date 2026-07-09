import type { Product } from '../lib/types'

interface ProductTableProps {
  products: Product[]
}

export function ProductTable({ products }: ProductTableProps) {
  if (products.length === 0) {
    return <p className="empty-state">Bu kategoriya uchun hozircha ma'lumot yo'q.</p>
  }

  return (
    <table className="product-table">
      <thead>
        <tr>
          <th>Bank</th>
          <th>Mahsulot</th>
          <th>Stavka</th>
          <th>Muddat</th>
        </tr>
      </thead>
      <tbody>
        {products.map((product, index) => (
          <tr key={`${product.bank}-${product.product_name}-${index}`}>
            <td>{product.bank}</td>
            <td>{product.product_name}</td>
            <td>
              {product.rate_min}% – {product.rate_max}%
            </td>
            <td>
              {product.term_min_months}–{product.term_max_months} oy
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}
