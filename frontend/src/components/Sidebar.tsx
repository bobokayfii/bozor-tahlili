import type { Category } from '../lib/types'

interface SidebarProps {
  categories: Category[]
  activeCategory: string | null
  onSelect: (categoryKey: string) => void
}

export function Sidebar({ categories, activeCategory, onSelect }: SidebarProps) {
  return (
    <nav className="sidebar" aria-label="Mahsulot kategoriyalari">
      <div className="sidebar-brand">Bozor Tahlili</div>
      <ul>
        {categories.map((category) => (
          <li key={category.key}>
            <button
              type="button"
              className={category.key === activeCategory ? 'sidebar-item active' : 'sidebar-item'}
              onClick={() => onSelect(category.key)}
            >
              {category.label}
            </button>
          </li>
        ))}
      </ul>
    </nav>
  )
}
