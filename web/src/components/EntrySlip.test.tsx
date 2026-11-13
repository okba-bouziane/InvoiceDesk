import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import { extractOk, extractWrongTotal } from '../test/fixtures.ts'
import { renderWith } from '../test/render.tsx'
import { EntrySlip } from './EntrySlip.tsx'

describe('EntrySlip', () => {
  it('shows the fields as printed and stamps a verified invoice', () => {
    renderWith(<EntrySlip result={extractOk} />)
    expect(screen.getByText('SPA Ouarsenis')).toBeInTheDocument()
    expect(screen.getByText('992034626202338')).toBeInTheDocument()
    expect(screen.getByText('1 190,00 DA')).toBeInTheDocument()
    expect(screen.getByText('Totaux vérifiés')).toBeInTheDocument()
  })

  it('flags a total that does not add up', () => {
    renderWith(<EntrySlip result={extractWrongTotal} />)
    expect(screen.getByText('À vérifier avant saisie')).toBeInTheDocument()
    const checks = screen.getByRole('list', { name: 'Contrôles' })
    expect(within(checks).getByText(/attendu 1 190,00, lu 1 200,00/)).toBeInTheDocument()
  })

  it('reveals the JSON to import', async () => {
    renderWith(<EntrySlip result={extractOk} />)
    await userEvent.click(screen.getByRole('button', { name: 'Voir le JSON à importer' }))
    expect(screen.getByText(/"total_ttc": 1190/)).toBeInTheDocument()
  })

  it('speaks English when asked to', () => {
    renderWith(<EntrySlip result={extractWrongTotal} />, 'en')
    expect(screen.getByText('Supplier')).toBeInTheDocument()
    expect(screen.getByText('Review before entry')).toBeInTheDocument()
    expect(screen.getByText(/expected 1 190,00, read 1 200,00/)).toBeInTheDocument()
  })
})
