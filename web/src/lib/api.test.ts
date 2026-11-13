import { afterEach, describe, expect, it, vi } from 'vitest'
import { ApiError, ExtractResponse, extractInvoice } from './api.ts'
import { extractOk } from '../test/fixtures.ts'

const mockFetch = (status: number, body: unknown) =>
  vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(JSON.stringify(body), { status }))

afterEach(() => vi.restoreAllMocks())

describe('api', () => {
  it('validates and returns an extraction', async () => {
    mockFetch(200, extractOk)
    await expect(extractInvoice(new Blob(['x'], { type: 'image/jpeg' }))).resolves.toEqual(extractOk)
  })

  it('turns a single line item into a list', () => {
    const one = { ...extractOk, fields: { ...extractOk.fields, items: { name: 'A', amount: '1,00' } } }
    expect(ExtractResponse.parse(one).fields.items).toEqual([{ name: 'A', amount: '1,00' }])
  })

  it('surfaces the server message on an error status', async () => {
    mockFetch(413, { detail: 'The image must be at most 6 MB.' })
    await expect(extractInvoice(new Blob(['x']))).rejects.toThrow('The image must be at most 6 MB.')
  })

  it('rejects a response that does not match the contract', async () => {
    mockFetch(200, { fields: 'nope' })
    await expect(extractInvoice(new Blob(['x']))).rejects.toBeInstanceOf(ApiError)
  })
})
