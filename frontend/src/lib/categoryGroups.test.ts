import { describe, it, expect } from 'vitest'
import { CATEGORY_GROUPS } from './categoryGroups'

describe('CATEGORY_GROUPS', () => {
  it('does not list the same category key in more than one group', () => {
    const allKeys = CATEGORY_GROUPS.flatMap((group) => group.keys)
    expect(allKeys.length).toBe(new Set(allKeys).size)
  })

  it('gives every multi-key group a shortLabel for each of its keys', () => {
    for (const group of CATEGORY_GROUPS) {
      if (group.keys.length > 1) {
        for (const key of group.keys) {
          expect(group.shortLabels?.[key]).toBeTruthy()
        }
      }
    }
  })

  it('gives every group an icon and a distinct icon color', () => {
    const colors = CATEGORY_GROUPS.map((group) => group.iconColor)
    for (const group of CATEGORY_GROUPS) {
      expect(group.icon).toBeTruthy()
      expect(group.iconColor).toBeTruthy()
    }
    expect(colors.length).toBe(new Set(colors).size)
  })
})
