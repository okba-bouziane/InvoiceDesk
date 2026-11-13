import type { Messages } from '../i18n.tsx'
import type { Check } from './api.ts'

/** The API names its checks in English; show them in the interface language. */
export function checkLabel(name: string, t: Messages): string {
  const tva = /^TVA = (.+) of HT$/.exec(name)
  if (tva) return t.checks.tva(tva[1] ?? '')
  const known: Record<string, string> = {
    'HT + TVA + timbre = TTC': t.checks.total,
    'sum of lines = HT': t.checks.lines,
    'NIF has 15 digits': t.checks.nif,
    'date is valid': t.checks.date,
  }
  return known[name] ?? name
}

/** 106251.99 -> "106 251,99" (French grouping with a plain space, as printed on the invoices). */
function invoiceAmount(s: string): string {
  if (!/^-?\d+(\.\d+)?$/.test(s)) return s
  return Number(s).toLocaleString('fr-FR', { minimumFractionDigits: 2 }).replace(/[  ]/g, ' ')
}

/** "106251.99 vs 106251.98" -> "expected 106 251,99, read 106 251,98" (computed first, then read). */
export function checkDetail(detail: string, t: Messages): string {
  const [want, got] = detail.split(' vs ')
  return got === undefined ? detail : t.checks.detail(invoiceAmount(want ?? ''), invoiceAmount(got))
}

export function verdict(checks: Check[]): 'verified' | 'review' | 'unknown' {
  if (checks.length === 0) return 'unknown'
  return checks.every((c) => c.ok) ? 'verified' : 'review'
}
