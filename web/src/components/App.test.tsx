import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { extractOk } from '../test/fixtures.ts'
import { renderWith } from '../test/render.tsx'
import { App } from './App.tsx'

const renderApp = (lang: 'fr' | 'en' = 'fr') => renderWith(<App />, lang)

afterEach(() => vi.restoreAllMocks())

describe('App', () => {
  it('reads an uploaded invoice, then answers a question about it', async () => {
    const fetch = vi.spyOn(globalThis, 'fetch').mockImplementation(async (url) => {
      const body = String(url).endsWith('/api/extract')
        ? extractOk
        : { model: 'test', question: 'Quel est le NIF ?', answer: '992034626202338', seconds: 0.4 }
      return new Response(JSON.stringify(body), { status: 200 })
    })
    renderApp()
    const user = userEvent.setup()
    await user.upload(screen.getByLabelText('Fichier de la facture'), new File(['x'], 'facture.jpg', { type: 'image/jpeg' }))

    expect(await screen.findByRole('article', { name: 'Fiche de saisie' })).toBeInTheDocument()
    expect(screen.getByText(/Les totaux se recalculent correctement/)).toBeInTheDocument()

    await user.type(screen.getByLabelText('Question'), 'Quel est le NIF ?')
    await user.click(screen.getByRole('button', { name: 'Envoyer la question' }))
    expect(await screen.findAllByText('992034626202338')).toHaveLength(2) // on the slip and as the answer
    expect(fetch).toHaveBeenCalledTimes(2)
  })

  it('asks for an invoice before answering', async () => {
    renderApp()
    const user = userEvent.setup()
    await user.type(screen.getByLabelText('Question'), 'Total ?')
    await user.click(screen.getByRole('button', { name: 'Envoyer la question' }))
    expect(screen.getByText(/Joignez d’abord une facture/)).toBeInTheDocument()
  })

  it('refuses files that are not images', async () => {
    renderApp()
    const user = userEvent.setup({ applyAccept: false })
    await user.upload(screen.getByLabelText('Fichier de la facture'), new File(['x'], 'notes.txt', { type: 'text/plain' }))
    expect(screen.getByText(/n’est pas une image JPEG ou PNG/)).toBeInTheDocument()
  })

  it('shows a rate-limit refusal in the interface language', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(JSON.stringify({ detail: 'Too many requests. Try again in 30 seconds.' }), { status: 429 }))
    renderApp()
    await userEvent.upload(screen.getByLabelText('Fichier de la facture'), new File(['x'], 'f.png', { type: 'image/png' }))
    expect(await screen.findByText('Trop de demandes d’affilée. Réessayez dans 30 secondes.')).toBeInTheDocument()
  })

  it('switches the whole conversation to English', async () => {
    const user = userEvent.setup()
    renderApp('fr')
    await user.type(screen.getByLabelText('Question'), 'Total ?')
    await user.click(screen.getByRole('button', { name: 'Envoyer la question' }))
    expect(screen.getByText(/Joignez d’abord une facture/)).toBeInTheDocument()
    await user.click(screen.getAllByRole('button', { name: 'en' })[0]!) // header and sidebar both have one
    expect(screen.getByText(/Attach an invoice first/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Send the question' })).toBeInTheDocument()
    expect(document.documentElement.lang).toBe('en')
  })

  it('keeps each invoice in its own chat in this tab’s history', async () => {
    let n = 0
    vi.spyOn(globalThis, 'fetch').mockImplementation(async () => {
      n += 1
      const vendor = n === 1 ? 'SPA Ouarsenis' : 'SARL Atlas'
      return new Response(JSON.stringify({ ...extractOk, fields: { ...extractOk.fields, vendor } }), { status: 200 })
    })
    const user = userEvent.setup()
    renderApp('en')
    const file = screen.getByLabelText('Invoice file')
    await user.upload(file, new File(['a'], 'first.jpg', { type: 'image/jpeg' }))
    await screen.findByRole('article', { name: 'Entry sheet' })
    await user.upload(file, new File(['b'], 'second.jpg', { type: 'image/jpeg' }))
    await screen.findByText('SARL Atlas', { selector: 'article p' })

    const history = screen.getByRole('navigation', { name: 'Chats in this session' })
    const items = within(history).getAllByRole('listitem')
    expect(items.map((li) => li.textContent)).toEqual([
      expect.stringContaining('SARL Atlas'),
      expect.stringContaining('SPA Ouarsenis'),
    ])

    await user.click(within(history).getByRole('button', { name: /^SPA Ouarsenis/ }))
    expect(screen.getByText('SPA Ouarsenis', { selector: 'article p' })).toBeInTheDocument()

    await user.click(within(history).getByRole('button', { name: 'Delete “SPA Ouarsenis”' }))
    expect(within(history).getAllByRole('listitem')).toHaveLength(1)
    expect(screen.getByRole('heading', { name: /Send an invoice/ })).toBeInTheDocument() // the deleted chat was open

    await user.click(within(history).getByRole('button', { name: /^SARL Atlas/ }))
    await user.click(screen.getByRole('button', { name: 'New chat' }))
    expect(screen.getByRole('heading', { name: /Send an invoice/ })).toBeInTheDocument()
    expect(within(history).getAllByRole('listitem')).toHaveLength(1)
  })
})
