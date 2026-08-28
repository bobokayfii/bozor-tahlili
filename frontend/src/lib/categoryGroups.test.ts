import { describe, it, expect } from 'vitest'
import { CATEGORY_GROUPS, getCategoryHeading } from './categoryGroups'

describe('CATEGORY_GROUPS', () => {
  it('does not list the same category key in more than one group', () => {
    const allKeys = CATEGORY_GROUPS.flatMap((group) => group.keys)
    expect(allKeys.length).toBe(new Set(allKeys).size)
  })

  it('gives every multi-key group a shortLabel (uz and ru) for each of its keys', () => {
    for (const group of CATEGORY_GROUPS) {
      if (group.keys.length > 1) {
        for (const key of group.keys) {
          expect(group.shortLabels?.[key]).toBeTruthy()
          expect(group.shortLabelsRu?.[key]).toBeTruthy()
        }
      }
    }
  })

  it('gives every group a Russian label', () => {
    for (const group of CATEGORY_GROUPS) {
      expect(group.labelRu).toBeTruthy()
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

describe('getCategoryHeading', () => {
  it('uses "Group - shortLabel" for a category that belongs to a multi-key group', () => {
    expect(getCategoryHeading('avtokredit', 'fallback', 'uz')).toBe('Avtokredit - Birlamchi bozor')
    expect(getCategoryHeading('avtokredit_brend_ikkilamchi', 'fallback', 'uz')).toBe(
      'Brendli avtokredit - Ikkilamchi bozor',
    )
  })

  it('uses the Russian group label and short label when lang is ru', () => {
    expect(getCategoryHeading('avtokredit', 'fallback', 'ru')).toBe('Автокредит - Первичный рынок')
    expect(getCategoryHeading('avtokredit_brend_ikkilamchi', 'fallback', 'ru')).toBe(
      'Брендовый автокредит - Вторичный рынок',
    )
  })

  it('uses just the group label for a single-key group', () => {
    expect(getCategoryHeading('kredit_karta', 'fallback', 'uz')).toBe('Kredit kartalari')
    expect(getCategoryHeading('kredit_karta', 'fallback', 'ru')).toBe('Кредитные карты')
  })

  it('falls back to the given label for an unknown category key', () => {
    expect(getCategoryHeading('unknown_category', 'fallback label', 'uz')).toBe('fallback label')
  })
})
