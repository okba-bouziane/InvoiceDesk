import { describe, expect, it } from 'vitest'
import { MESSAGES } from '../i18n.tsx'
import { checkDetail, checkLabel, verdict } from './checks.ts'

const { fr, en } = MESSAGES

describe('checks', () => {
  it('names checks in the interface language', () => {
    expect(checkLabel('sum of lines = HT', fr)).toBe('Somme des lignes = HT')
    expect(checkLabel('TVA = 9% of HT', fr)).toBe('TVA = 9% du HT')
    expect(checkLabel('sum of lines = HT', en)).toBe('Sum of lines = net total')
    expect(checkLabel('TVA = 19% of HT', en)).toBe('VAT = 19% of net total')
  })

  it('formats amounts as printed on the invoices, in both languages', () => {
    expect(checkDetail('106251.99 vs 106251.98', fr)).toBe('attendu 106 251,99, lu 106 251,98')
    expect(checkDetail('106251.99 vs 106251.98', en)).toBe('expected 106 251,99, read 106 251,98')
    expect(checkDetail('12345', en)).toBe('12345')
  })

  it('gives one verdict for the stamp', () => {
    expect(verdict([])).toBe('unknown')
    expect(verdict([{ name: 'a', ok: true, detail: '' }])).toBe('verified')
    expect(verdict([{ name: 'a', ok: true, detail: '' }, { name: 'b', ok: false, detail: '' }])).toBe('review')
  })

  it('has every message in both languages', () => {
    const keys = (o: object): string[] =>
      Object.entries(o).flatMap(([k, v]) => (v && typeof v === 'object' && !Array.isArray(v) ? keys(v).map((s) => `${k}.${s}`) : [k]))
    expect(keys(en).toSorted()).toEqual(keys(fr).toSorted())
  })
})
