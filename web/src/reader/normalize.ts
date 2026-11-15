/** TypeScript twin of invoicedesk/normalize.py: typed values, the bookkeeping checks and tidy(). */
import type { Check } from '../lib/api.ts'

const MONTHS = ['janvier', 'février', 'mars', 'avril', 'mai', 'juin', 'juillet', 'août', 'septembre', 'octobre',
  'novembre', 'décembre']

/** '12 345,00' / '12.345,00' / '12345,00' / '12 345,00 DA' -> 12345. Anything else -> null. */
export function parseAmount(text: unknown): number | null {
  if (!text || typeof text !== 'string') return null
  let s = text.replace(/ /g, ' ').replace(/[^\d,.-]/g, '')
  if (s.includes(',')) s = s.split('.').join('').replace(',', '.')
  else if ((s.match(/\./g) ?? []).length > 1 || /\.\d{3}$/.test(s)) s = s.split('.').join('')
  if (!/^-?\d+(\.\d+)?$/.test(s)) return null
  return Number(s)
}

/** '29/12/2024', '29-12-2024', '29.12.2024', '29 décembre 2024' -> '2024-12-29'. */
export function parseDate(text: unknown): string | null {
  if (!text || typeof text !== 'string') return null
  const t = text.trim().toLowerCase()
  let d: number, mo: number, y: number
  const num = /^(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})$/.exec(t)
  if (num) {
    ;[d, mo, y] = [Number(num[1]), Number(num[2]), Number(num[3])]
  } else {
    const word = /^(\d{1,2})\s+([a-zéû]+)\s+(\d{4})$/.exec(t)
    const idx = word ? MONTHS.indexOf(word[2] ?? '') : -1
    if (!word || idx < 0) return null
    ;[d, mo, y] = [Number(word[1]), idx + 1, Number(word[3])]
  }
  const date = new Date(Date.UTC(y, mo - 1, d))
  if (date.getUTCFullYear() !== y || date.getUTCMonth() !== mo - 1 || date.getUTCDate() !== d) return null
  return date.toISOString().slice(0, 10)
}

// Like Python's round(x, 2): rounds the exact binary value (3642.395 is stored as 3642.39499…).
const round2 = (x: number) => Number(x.toFixed(2))

/** Consistency checks a bookkeeper would do by hand, with the same names as the API. */
export function checks(fields: Record<string, unknown>): Check[] {
  const out: Check[] = []
  const [ht, tva, ttc] = (['total_ht', 'tva', 'total_ttc'] as const).map((k) => parseAmount(fields[k]))
  const timbre = parseAmount(fields.timbre) ?? 0
  if (ht != null && tva != null && ttc != null) {
    const expected = round2(ht + tva + timbre)
    out.push({ name: 'HT + TVA + timbre = TTC', ok: Math.abs(expected - ttc) <= 0.02, detail: `${expected.toFixed(2)} vs ${ttc.toFixed(2)}` })
  }
  const rate = fields.tva_rate
  if (ht != null && tva != null && typeof rate === 'string' && rate) {
    const r = parseAmount(rate.replace('%', ''))
    if (r != null) {
      const want = round2((ht * r) / 100)
      out.push({ name: `TVA = ${rate} of HT`, ok: Math.abs(want - tva) <= 0.02, detail: `${want.toFixed(2)} vs ${tva.toFixed(2)}` })
    }
  }
  const items = Array.isArray(fields.items) ? fields.items : []
  const amounts = items.filter((i): i is Record<string, unknown> => !!i && typeof i === 'object').map((i) => parseAmount(i.amount))
  if (ht != null && amounts.length && amounts.every((a) => a != null)) {
    const s = round2(amounts.reduce<number>((a, b) => a + (b ?? 0), 0))
    out.push({ name: 'sum of lines = HT', ok: Math.abs(s - ht) <= 0.02, detail: `${s.toFixed(2)} vs ${ht.toFixed(2)}` })
  }
  if (typeof fields.vendor_nif === 'string' && fields.vendor_nif) {
    out.push({ name: 'NIF has 15 digits', ok: /^\d{15}$/.test(fields.vendor_nif), detail: fields.vendor_nif })
  }
  if (typeof fields.date === 'string' && fields.date) {
    out.push({ name: 'date is valid', ok: parseDate(fields.date) != null, detail: fields.date })
  }
  return out
}

function firstText(v: unknown): string | null {
  if (Array.isArray(v)) v = v.find((x) => typeof x === 'string' && x.trim())
  return typeof v === 'string' && v.trim() ? v.trim() : null
}

/** Header fields become strings and `items` a list of objects; a repeated field keeps its first value. */
export function tidy(fields: unknown): Record<string, unknown> {
  if (!fields || typeof fields !== 'object' || Array.isArray(fields)) return {}
  const out: Record<string, unknown> = {}
  for (const [k, v] of Object.entries(fields)) {
    if (k === 'items') {
      const rows = Array.isArray(v) ? v : [v]
      const items = rows
        .filter((r): r is Record<string, unknown> => !!r && typeof r === 'object' && !Array.isArray(r))
        .map((r) => Object.fromEntries(Object.entries(r).flatMap(([ik, iv]) => { const t = firstText(iv); return t ? [[ik, t]] : [] })))
        .filter((i) => Object.keys(i).length > 0)
      if (items.length) out.items = items
    } else {
      const t = firstText(v)
      if (t) out[k] = t
    }
  }
  return out
}

/** The values an accounting system needs as numbers and dates. */
export function typed(fields: Record<string, unknown>): Record<string, number | string> {
  const out: Record<string, number | string> = {}
  for (const k of ['total_ht', 'tva', 'timbre', 'total_ttc']) {
    const v = parseAmount(fields[k])
    if (v != null) out[k] = v
  }
  const d = parseDate(fields.date)
  if (d) out.date = d
  return out
}
