import { Check as CheckIcon, X } from 'lucide-react'
import { useState } from 'react'
import { useI18n } from '../i18n.tsx'
import type { Check, ExtractResult } from '../lib/api.ts'
import { checkDetail, checkLabel, verdict } from '../lib/checks.ts'
import { Stamp } from './Stamp.tsx'

function Mark({ ok }: { ok: boolean | undefined }) {
  const { t } = useI18n()
  if (ok === undefined) return <span className="w-4" />
  return ok ? (
    <CheckIcon aria-label={t.slip.ok} className="size-4 text-ok" strokeWidth={3} />
  ) : (
    <X aria-label={t.slip.bad} className="size-4 text-refuse" strokeWidth={3} />
  )
}

function Typed({ children, strong }: { children: React.ReactNode; strong?: boolean }) {
  return <span className={`font-typed ${strong ? 'font-bold' : ''}`}>{children}</span>
}

/** The extracted invoice, laid out as the duplicate sheet a bookkeeper types from. */
export function EntrySlip({ result }: { result: ExtractResult }) {
  const { t, lang } = useI18n()
  const [showJson, setShowJson] = useState(false)
  const f = result.fields
  const byName = new Map(result.checks.map((c) => [c.name, c.ok]))
  const tvaCheck = result.checks.find((c) => c.name.startsWith('TVA ='))
  const ttcOk = byName.get('HT + TVA + timbre = TTC')
  const v = verdict(result.checks)
  const refs: [string, string | undefined][] = [
    [t.slip.invoiceNumber, f.invoice_number],
    [t.slip.date, f.date],
    ['NIF', f.vendor_nif],
    ['RC', f.vendor_rc],
  ]
  const totals: [string, string | undefined, boolean | undefined][] = [
    [t.slip.totalHt, f.total_ht, byName.get('sum of lines = HT')],
    [`${t.slip.tva} ${f.tva_rate ?? ''}`.trim(), f.tva, tvaCheck?.ok],
    [t.slip.timbre, f.timbre, undefined],
  ]

  return (
    <article aria-label={t.slip.label} className="relative mt-2 overflow-hidden rounded-b-md bg-carbon text-ink shadow-[0_1px_0_#d9cb7f,0_10px_24px_-14px_rgba(28,36,33,.45)]">
      <div className="perforated h-2 bg-carbon" />
      <div className="px-5 pb-4 pt-3 sm:px-7">
        <header className="flex items-start justify-between gap-4 border-b border-dashed border-carbon-line pb-3">
          <div className="min-w-0">
            <p className="text-xs text-ink-soft">{t.slip.vendor}</p>
            <p className="text-lg font-semibold leading-snug">{f.vendor ?? t.slip.notRead}</p>
            {f.vendor_address && <p className="text-sm text-ink-soft">{f.vendor_address}</p>}
            <p className="mt-2 text-xs text-ink-soft">{t.slip.client}</p>
            <p className="font-medium">{f.client ?? t.slip.notRead}</p>
          </div>
          {v !== 'unknown' && (
            <div className="shrink-0 origin-top-right scale-[.8] pt-1 sm:scale-100">
              <Stamp verdict={v} />
            </div>
          )}
        </header>

        <dl className="grid grid-cols-[max-content_1fr] gap-x-4 gap-y-1 py-3 text-sm sm:grid-cols-[max-content_1fr_max-content_1fr]">
          {refs.filter(([, val]) => val).map(([k, val]) => (
            <div key={k} className="contents">
              <dt className="text-ink-soft">{k}</dt>
              <dd className="min-w-0 break-all"><Typed>{val}</Typed></dd>
            </div>
          ))}
        </dl>

        {f.items && f.items.length > 0 && (
          <div className="-mx-1">
            <table className="w-full border-collapse text-sm">
              <thead>
                <tr className="border-b-2 border-ink text-left text-ink-soft">
                  <th className="px-1 py-1.5 font-medium">{t.slip.item}</th>
                  <th className="px-1 py-1.5 text-right font-medium">{t.slip.qty}</th>
                  <th className="hidden px-1 py-1.5 text-right font-medium sm:table-cell">{t.slip.unitPrice}</th>
                  <th className="px-1 py-1.5 text-right font-medium">{t.slip.amount}</th>
                </tr>
              </thead>
              <tbody>
                {f.items.map((it, i) => (
                  <tr key={i} className="border-b border-carbon-line">
                    <td className="px-1 py-1.5">{it.name}</td>
                    <td className="px-1 py-1.5 text-right"><Typed>{it.qty}</Typed></td>
                    <td className="hidden whitespace-nowrap px-1 py-1.5 text-right sm:table-cell"><Typed>{it.unit_price}</Typed></td>
                    <td className="whitespace-nowrap px-1 py-1.5 text-right"><Typed>{it.amount}</Typed></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        <div className="ml-auto mt-3 w-full max-w-[340px] text-sm">
          {totals.filter(([, val]) => val).map(([k, val, ok]) => (
            <div key={k} className="grid grid-cols-[20px_1fr_auto] items-center py-0.5">
              <Mark ok={ok} />
              <span>{k}</span>
              <Typed>{val} DA</Typed>
            </div>
          ))}
          {f.total_ttc && (
            <div className="mt-1 grid grid-cols-[20px_1fr_auto] items-center border-t-2 border-ink pt-1.5 text-base font-bold">
              <Mark ok={ttcOk} />
              <span>{t.slip.totalTtc}</span>
              <span className={`border-b-[3px] border-double ${ttcOk === false ? 'border-refuse text-refuse' : 'border-ink'}`}>
                <Typed strong>{f.total_ttc} DA</Typed>
              </span>
            </div>
          )}
        </div>

        {result.checks.length > 0 && <CheckList checks={result.checks} />}

        <div className="mt-3 flex items-center justify-between gap-3 text-xs text-ink-soft">
          <button type="button" onClick={() => setShowJson((s) => !s)} className="underline decoration-1 underline-offset-2 hover:text-ink">
            {showJson ? t.slip.hideJson : t.slip.showJson}
          </button>
          <span>{t.slip.readIn(result.seconds.toLocaleString(lang === 'fr' ? 'fr-FR' : 'en-US'))}</span>
        </div>
        {showJson && (
          <pre className="mt-2 max-h-72 overflow-auto rounded border border-carbon-line bg-white/60 p-3 text-xs">
            {JSON.stringify({ ...result.fields, typed: result.typed }, null, 2)}
          </pre>
        )}
      </div>
    </article>
  )
}

function CheckList({ checks }: { checks: Check[] }) {
  const { t } = useI18n()
  return (
    <ul className="mt-3 space-y-0.5 border-t border-dashed border-carbon-line pt-2 text-[13px]" aria-label={t.slip.checks}>
      {checks.map((c) => (
        <li key={c.name} className={`flex items-start gap-1.5 ${c.ok ? 'text-ink-soft' : 'font-medium text-refuse'}`}>
          <span className="mt-0.5"><Mark ok={c.ok} /></span>
          <span>
            {checkLabel(c.name, t)}
            {!c.ok && <span className="font-normal"> ({checkDetail(c.detail, t)})</span>}
          </span>
        </li>
      ))}
    </ul>
  )
}
