import { z } from 'zod'

/** Values are kept exactly as printed on the invoice ("12 345,00"); `typed` holds the parsed ones. */
const Item = z.object({
  name: z.string().optional(),
  qty: z.string().optional(),
  unit_price: z.string().optional(),
  amount: z.string().optional(),
})

export const Fields = z
  .object({
    vendor: z.string(),
    vendor_address: z.string(),
    vendor_nif: z.string(),
    vendor_rc: z.string(),
    invoice_number: z.string(),
    date: z.string(),
    client: z.string(),
    total_ht: z.string(),
    tva_rate: z.string(),
    tva: z.string(),
    timbre: z.string(),
    total_ttc: z.string(),
    // a single line can come back as an object; normalise to a list
    items: z.union([z.array(Item), Item]).transform((v) => (Array.isArray(v) ? v : [v])),
  })
  .partial()

export const Check = z.object({ name: z.string(), ok: z.boolean(), detail: z.string() })

export const ExtractResponse = z.object({
  model: z.string(),
  fields: Fields,
  typed: z.record(z.string(), z.union([z.number(), z.string()])),
  checks: z.array(Check),
  seconds: z.number(),
})

export const AskResponse = z.object({
  model: z.string(),
  question: z.string(),
  answer: z.string(),
  seconds: z.number(),
})

export type Fields = z.infer<typeof Fields>
export type Check = z.infer<typeof Check>
export type ExtractResult = z.infer<typeof ExtractResponse>
export type AskResult = z.infer<typeof AskResponse>

/** `code` lets the interface word the error in its own language; `detail` is the server's message. */
export class ApiError extends Error {
  readonly code: 'offline' | 'unexpected' | 'status'
  readonly status: number
  readonly detail: string

  constructor(code: ApiError['code'], status = 0, detail = '') {
    super(detail || code)
    this.code = code
    this.status = status
    this.detail = detail
  }
}

async function post<T>(url: string, schema: z.ZodType<T>, form: FormData): Promise<T> {
  let res: Response
  try {
    res = await fetch(url, { method: 'POST', body: form })
  } catch {
    throw new ApiError('offline')
  }
  const body: unknown = await res.json().catch(() => null)
  if (!res.ok) {
    const detail = (body as { detail?: unknown } | null)?.detail
    throw new ApiError('status', res.status, typeof detail === 'string' ? detail : '')
  }
  const parsed = schema.safeParse(body)
  if (!parsed.success) throw new ApiError('unexpected')
  return parsed.data
}

export function extractInvoice(image: Blob): Promise<ExtractResult> {
  const form = new FormData()
  form.append('image', image, 'facture.jpg')
  return post('/api/extract', ExtractResponse, form)
}

export function askInvoice(image: Blob, question: string): Promise<AskResult> {
  const form = new FormData()
  form.append('image', image, 'facture.jpg')
  form.append('question', question)
  return post('/api/ask', AskResponse, form)
}
