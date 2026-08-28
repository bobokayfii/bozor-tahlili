import { useState } from 'react'
import type { Category } from '../lib/types'
import { CATEGORY_GROUPS, groupLabel, groupShortLabel, type CategoryGroup } from '../lib/categoryGroups'
import { useLanguage } from '../lib/LanguageContext'
import { UsersIcon } from './icons'

interface SidebarProps {
  categories: Category[]
  activeCategory: string | null
  onSelect: (categoryKey: string) => void
  isAdmin?: boolean
  isAdminView?: boolean
  onSelectAdmin?: () => void
}

// "SQB AI" always appears verbatim inside poweredByLabel (uz/ru), regardless
// of word order, so it can be highlighted without a separate translation key.
function poweredByParts(label: string) {
  const [before, after] = label.split('SQB AI')
  return (
    <>
      {before}
      <strong>SQB AI</strong>
      {after}
    </>
  )
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

export function Sidebar({
  categories,
  activeCategory,
  onSelect,
  isAdmin = false,
  isAdminView = false,
  onSelectAdmin,
}: SidebarProps) {
  const { lang, t } = useLanguage()
  const byKey = new Map(categories.map((category) => [category.key, category]))

  // group.label (Uzbek) is used as a stable internal identity key for the
  // expanded-set, independent of the currently displayed language.
  const activeGroupKey = CATEGORY_GROUPS.find((group) => group.keys.includes(activeCategory ?? ''))?.label

  const [expanded, setExpanded] = useState<Set<string>>(
    () => new Set(activeGroupKey ? [activeGroupKey] : []),
  )

  function toggleGroup(groupKey: string) {
    setExpanded((prev) => {
      const next = new Set(prev)
      if (next.has(groupKey)) {
        next.delete(groupKey)
      } else {
        next.add(groupKey)
      }
      return next
    })
  }

  return (
    <nav className="sidebar" aria-label={t('sidebarTitle')}>
      <div className="sidebar-group-label">{t('sidebarTitle')}</div>
      <ul className="sidebar-tree">
        {CATEGORY_GROUPS.map((group) => {
          const availableKeys = group.keys.filter((key) => byKey.has(key))
          if (availableKeys.length === 0) {
            return null
          }
          const label = groupLabel(group, lang)

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
                  {label}
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
                  {label}
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
                        {groupShortLabel(group, key, lang) ?? byKey.get(key)?.label}
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </li>
          )
        })}
      </ul>
      {isAdmin && (
        <div className="sidebar-admin-section">
          <div className="sidebar-group-label">{t('adminSectionLabel')}</div>
          <ul className="sidebar-tree">
            <li>
              <button
                type="button"
                className={isAdminView ? 'sidebar-item active' : 'sidebar-item'}
                onClick={onSelectAdmin}
              >
                <UsersIcon />
                {t('adminUsersNavLabel')}
              </button>
            </li>
          </ul>
        </div>
      )}
      <div className="sidebar-foot">
        <span className="sidebar-powered-by">{poweredByParts(t('poweredByLabel'))}</span>
      </div>
    </nav>
  )
}
