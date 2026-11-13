import type { ExtractResult } from '../lib/api.ts'

export const extractOk: ExtractResult = {
  model: 'test',
  fields: {
    vendor: 'SPA Ouarsenis',
    vendor_nif: '992034626202338',
    vendor_rc: '05/00-1120743 B 14',
    invoice_number: '985/2024',
    date: '27-09-2024',
    client: 'Leila Rahmani',
    total_ht: '1 000,00',
    tva_rate: '19%',
    tva: '190,00',
    total_ttc: '1 190,00',
    items: [{ name: 'Batterie 70 Ah', qty: '1', unit_price: '1 000,00', amount: '1 000,00' }],
  },
  typed: { total_ht: 1000, tva: 190, total_ttc: 1190, date: '2024-09-27' },
  checks: [
    { name: 'HT + TVA + timbre = TTC', ok: true, detail: '1190.00 vs 1190.00' },
    { name: 'TVA = 19% of HT', ok: true, detail: '190.00 vs 190.00' },
    { name: 'sum of lines = HT', ok: true, detail: '1000.00 vs 1000.00' },
  ],
  seconds: 1.42,
}

export const extractWrongTotal: ExtractResult = {
  ...extractOk,
  fields: { ...extractOk.fields, total_ttc: '1 200,00' },
  checks: [
    { name: 'HT + TVA + timbre = TTC', ok: false, detail: '1190.00 vs 1200.00' },
    { name: 'TVA = 19% of HT', ok: true, detail: '190.00 vs 190.00' },
  ],
}
