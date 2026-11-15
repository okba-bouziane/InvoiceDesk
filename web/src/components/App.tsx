import { useEffect, useState } from 'react'
import { useI18n } from '../i18n.tsx'
import { IN_BROWSER } from '../lib/api.ts'
import { useChats } from '../lib/useChats.ts'
import { Composer } from './Composer.tsx'
import { EmptyState } from './EmptyState.tsx'
import { Rail } from './Rail.tsx'
import { Thread } from './Thread.tsx'

export function App() {
  const { chats, active, busy, sendInvoice, sendQuestion, newChat, selectChat, removeChat } = useChats()
  const { t } = useI18n()
  const [dragging, setDragging] = useState(false)
  const [drawer, setDrawer] = useState(false)
  const download = useModelDownload()

  const pickSample = async (file: string, label: string) => {
    const res = await fetch(`/samples/${file}`)
    const blob = await res.blob()
    sendInvoice(new Blob([blob], { type: 'image/jpeg' }), label)
  }

  return (
    <div
      className="flex h-dvh flex-col md:flex-row"
      onDragOver={(e) => {
        e.preventDefault()
        setDragging(true)
      }}
      onDragLeave={(e) => {
        if (!e.currentTarget.contains(e.relatedTarget as Node | null)) setDragging(false)
      }}
      onDrop={(e) => {
        e.preventDefault()
        setDragging(false)
        const f = e.dataTransfer.files[0]
        if (f) sendInvoice(f, f.name)
      }}
    >
      <Rail
        chats={chats}
        activeId={active?.id ?? null}
        open={drawer}
        onOpenChange={setDrawer}
        onNew={newChat}
        onSelect={selectChat}
        onRemove={removeChat}
      />
      <main className="relative flex min-h-0 min-w-0 flex-1 flex-col">
        <div className="min-h-0 flex-1 overflow-y-auto px-4 py-6 sm:px-8">
          {active ? <Thread key={active.id} messages={active.messages} onAsk={sendQuestion} /> : <EmptyState onSample={pickSample} />}
        </div>
        <div className="relative px-3 pb-3 pt-1 sm:px-8 sm:pb-5">
          <div aria-hidden className="pointer-events-none absolute inset-x-0 -top-8 h-8 bg-gradient-to-b from-paper/0 to-paper" />
          <Composer busy={busy} hasInvoice={Boolean(active?.invoice)} onFile={(f) => sendInvoice(f, f.name)} onAsk={sendQuestion} />
          {download ? (
            <output className="mx-auto mt-2 block max-w-[760px] text-xs font-medium text-register">
              {t.modelLoading(download.got, download.total)}
            </output>
          ) : (
            <p className="mx-auto mt-2 hidden max-w-[760px] text-xs text-ink-soft sm:block">{t.hint}</p>
          )}
        </div>
        {dragging && (
          <div className="pointer-events-none absolute inset-3 grid place-items-center rounded-xl border-2 border-dashed border-register bg-paper/85 text-lg font-semibold text-register">
            {t.dropHere}
          </div>
        )}
      </main>
    </div>
  )
}

/** In the browser build: how much of the model has been downloaded, while it is downloading. */
function useModelDownload(): { got: number; total: number } | null {
  const [state, setState] = useState<{ got: number; total: number } | null>(null)
  useEffect(() => {
    if (!IN_BROWSER) return
    let off: (() => void) | undefined
    let alive = true
    void import('../reader/browser.ts').then(({ onModelProgress }) => {
      if (!alive) return
      off = onModelProgress(({ loaded, total }) =>
        setState(total && loaded < total ? { got: Math.round(loaded / 1e6), total: Math.round(total / 1e6) } : null),
      )
    })
    return () => {
      alive = false
      off?.()
    }
  }, [])
  return state
}
