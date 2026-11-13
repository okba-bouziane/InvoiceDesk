import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render } from '@testing-library/react'
import type { ReactElement } from 'react'
import { I18nProvider, type Lang } from '../i18n.tsx'

/** Render with the providers the app uses, in a fixed language. */
export function renderWith(ui: ReactElement, lang: Lang = 'fr') {
  const client = new QueryClient({ defaultOptions: { mutations: { retry: 0 } } })
  return render(
    <QueryClientProvider client={client}>
      <I18nProvider lang={lang}>{ui}</I18nProvider>
    </QueryClientProvider>,
  )
}
