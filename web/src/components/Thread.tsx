import { useEffect, useRef } from 'react'
import { useI18n, type Messages } from '../i18n.tsx'
import { verdict } from '../lib/checks.ts'
import type { Message } from '../lib/conversation.ts'
import { EntrySlip } from './EntrySlip.tsx'

export function Thread({ messages, onAsk }: { messages: Message[]; onAsk: (q: string) => void }) {
  const end = useRef<HTMLDivElement>(null)
  const last = messages.at(-1)
  useEffect(() => {
    if (last) end.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [last])

  return (
    <ol className="mx-auto flex max-w-[760px] flex-col gap-6" aria-live="polite">
      {messages.map((m) => (
        <li key={m.id} className={m.role === 'user' ? 'self-end max-w-[85%]' : 'w-full'}>
          {m.role === 'user' ? <UserMessage m={m} /> : <BotMessage m={m} onAsk={onAsk} />}
        </li>
      ))}
      <div ref={end} />
    </ol>
  )
}

function UserMessage({ m }: { m: Extract<Message, { role: 'user' }> }) {
  const { t } = useI18n()
  if (m.kind === 'invoice') {
    return (
      <figure className="rotate-1 bg-white p-1.5 shadow-[0_8px_18px_-10px_rgba(28,36,33,.5)]">
        <img src={m.url} alt={t.sentInvoice(m.name)} className="block max-h-56 w-auto" />
      </figure>
    )
  }
  return <p className="rounded-2xl rounded-br-sm bg-register px-4 py-2.5 text-white">{m.text}</p>
}

/** Known server refusals are worded in the interface language; anything else shows the server's text. */
function noteText(m: Extract<Message, { kind: 'note' }>, t: Messages): string {
  if (m.code !== 'status') return t.notes[m.code]
  if (m.status === 413) return t.notes.tooBig
  if (m.status === 429) return t.notes.rateLimited(Number(/(\d+) seconds/.exec(m.detail ?? '')?.[1] ?? 60))
  if (m.status === 422 && /image/i.test(m.detail ?? '')) return t.notes.notImage
  return m.detail || t.notes.status(m.status ?? 0)
}

function BotMessage({ m, onAsk }: { m: Extract<Message, { role: 'bot' }>; onAsk: (q: string) => void }) {
  const { t } = useI18n()
  switch (m.kind) {
    case 'pending':
      return <p className="writing font-medium">{m.task === 'reading' ? t.reading : t.searching}…</p>
    case 'note':
      return <p className={m.error ? 'font-medium text-refuse' : ''}>{noteText(m, t)}</p>
    case 'answer':
      return (
        <div>
          <p className="font-typed text-2xl font-bold">{m.result.answer || '—'}</p>
          {!m.result.answer && <p className="text-sm text-ink-soft">{t.notFound}</p>}
        </div>
      )
    case 'extract': {
      const v = verdict(m.result.checks)
      const failed = m.result.checks.filter((c) => !c.ok).length
      const intro = v === 'unknown' ? t.introUnknown : v === 'verified' ? t.introVerified : t.introReview(failed)
      return (
        <div>
          <p>{intro}</p>
          <EntrySlip result={m.result} />
          <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-sm">
            <span className="text-ink-soft">{t.askPrompt}</span>
            {t.suggestions.map((q) => (
              <button key={q} type="button" onClick={() => onAsk(q)} className="text-register underline decoration-1 underline-offset-[3px] hover:decoration-2">
                {q}
              </button>
            ))}
          </div>
        </div>
      )
    }
  }
}
