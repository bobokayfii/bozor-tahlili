import { useState } from 'react'
import type { Category } from '../lib/types'
import { CATEGORY_GROUPS, type CategoryGroup } from '../lib/categoryGroups'

interface SidebarProps {
  categories: Category[]
  activeCategory: string | null
  onSelect: (categoryKey: string) => void
}

function GroupIcon({ group }: { group: CategoryGroup }) {
  const maskImage = `url(${group.icon})`
  return (
    <span
      className="sidebar-icon"
      style={{
        backgroundColor: group.iconColor,
        WebkitMaskImage: maskImage,
        maskImage,
      }}
    />
  )
}

function Chevron({ open }: { open: boolean }) {
  return (
    <svg
      className={open ? 'chevron chevron-open' : 'chevron'}
      width="11"
      height="11"
      viewBox="0 0 12 12"
      fill="none"
      aria-hidden="true"
    >
      <path
        d="M3 4.5L6 7.5L9 4.5"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}

export function Sidebar({ categories, activeCategory, onSelect }: SidebarProps) {
  const byKey = new Map(categories.map((category) => [category.key, category]))

  const activeGroupLabel = CATEGORY_GROUPS.find((group) => group.keys.includes(activeCategory ?? ''))?.label

  const [expanded, setExpanded] = useState<Set<string>>(
    () => new Set(activeGroupLabel ? [activeGroupLabel] : []),
  )

  function toggleGroup(label: string) {
    setExpanded((prev) => {
      const next = new Set(prev)
      if (next.has(label)) {
        next.delete(label)
      } else {
        next.add(label)
      }
      return next
    })
  }

  return (
    <nav className="sidebar" aria-label="Mahsulot kategoriyalari">
      <div className="sidebar-group-label">Kredit mahsulotlari</div>
      <ul className="sidebar-tree">
        {CATEGORY_GROUPS.map((group) => {
          const availableKeys = group.keys.filter((key) => byKey.has(key))
          if (availableKeys.length === 0) {
            return null
          }

          if (availableKeys.length === 1) {
            const key = availableKeys[0]
            return (
              <li key={group.label}>
                <button
                  type="button"
                  className={key === activeCategory ? 'sidebar-item active' : 'sidebar-item'}
                  onClick={() => onSelect(key)}
                >
                  <GroupIcon group={group} />
                  {group.label}
                </button>
              </li>
            )
          }

          const isOpen = expanded.has(group.label)
          const groupIsActive = availableKeys.includes(activeCategory ?? '')

          return (
            <li key={group.label} className="sidebar-tree-group">
              <button
                type="button"
                className={groupIsActive ? 'sidebar-item sidebar-parent active' : 'sidebar-item sidebar-parent'}
                onClick={() => toggleGroup(group.label)}
                aria-expanded={isOpen}
              >
                <span className="sidebar-parent-label">
                  <GroupIcon group={group} />
                  {group.label}
                </span>
                <Chevron open={isOpen} />
              </button>
              {isOpen && (
                <ul className="sidebar-submenu">
                  {availableKeys.map((key) => (
                    <li key={key}>
                      <button
                        type="button"
                        className={key === activeCategory ? 'sidebar-subitem active' : 'sidebar-subitem'}
                        onClick={() => onSelect(key)}
                      >
                        {group.shortLabels?.[key] ?? byKey.get(key)?.label}
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </li>
          )
        })}
      </ul>
      <div className="sidebar-foot">SQB · Strategiya bo'limi</div>
    </nav>
  )
}
