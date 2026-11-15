import { Menu, Plus, Trash2, X } from 'lucide-react'
import { useEffect } from 'react'
import { APP_NAME } from '../config.ts'
import { LANGS, MESSAGES, useI18n } from '../i18n.tsx'
import { IN_BROWSER } from '../lib/api.ts'
import type { Chat } from '../lib/conversation.ts'

interface Props {
  chats: Chat[]
  activeId: string | null
  open: boolean
  onOpenChange: (open: boolean) => void
  onNew: () => void
  onSelect: (chatId: string) => void
  onRemove: (chatId: string) => void
}

/** Left side: the register cover. Brand, language, and this tab's chats (memory only). */
export function Rail({ chats, activeId, open, onOpenChange, onNew, onSelect, onRemove }: Props) {
  const { t } = useI18n()

  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onOpenChange(false)
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open, onOpenChange])

  const panel = (
    <>
      <div className="px-5 pb-4 pt-5">
        <button
          type="button"
          onClick={() => {
            onNew()
            onOpenChange(false)
          }}
          className="flex w-full items-center justify-center gap-2 rounded-lg bg-[#e7efe9] px-3 py-2.5 font-semibold text-register hover:bg-white"
        >
          <Plus className="size-4" aria-hidden />
          {t.newChat}
        </button>
      </div>
      <nav aria-label={t.history} className="min-h-0 flex-1 overflow-y-auto px-3 pb-4">
        <p className="px-2 pb-2 text-xs text-[#88a69b]">{t.history}</p>
        {chats.length === 0 ? (
          <p className="px-2 text-sm text-[#a9c2b8]">{t.historyEmpty}</p>
        ) : (
          <ul className="space-y-1">
            {chats.map((c) => (
              <ChatItem
                key={c.id}
                chat={c}
                active={c.id === activeId}
                onSelect={() => {
                  onSelect(c.id)
                  onOpenChange(false)
                }}
                onRemove={() => onRemove(c.id)}
              />
            ))}
          </ul>
        )}
      </nav>
      <p className="border-t border-register-line px-5 py-4 text-xs leading-relaxed text-[#88a69b]">
        {t.historyNote}
        <br />
        <span className="mt-1.5 block">{IN_BROWSER ? t.railNoteBrowser : t.railNote}</span>
      </p>
    </>
  )

  return (
    <>
      <header className="flex items-center gap-3 bg-register px-4 py-3 text-white md:hidden">
        <button type="button" onClick={() => onOpenChange(true)} aria-label={t.openHistory} className="-ml-1 rounded p-1 hover:bg-register-deep">
          <Menu className="size-5" aria-hidden />
        </button>
        <span className="flex-1 text-xl font-bold tracking-tight">{APP_NAME}</span>
        <LanguageSwitch />
      </header>

      <aside className="hidden w-[300px] shrink-0 flex-col bg-register text-[#e7efe9] md:flex">
        <div className="flex items-start justify-between gap-3 border-b border-register-line px-5 py-5">
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-white">{APP_NAME}</h1>
            <p className="mt-0.5 text-sm text-[#a9c2b8]">{t.tagline}</p>
          </div>
          <LanguageSwitch />
        </div>
        {panel}
      </aside>

      {open && (
        <div className="fixed inset-0 z-40 md:hidden">
          <button type="button" aria-label={t.closeHistory} className="absolute inset-0 bg-ink/50" onClick={() => onOpenChange(false)} />
          <aside className="relative flex h-full w-[86%] max-w-[320px] flex-col bg-register text-[#e7efe9] shadow-2xl">
            <div className="flex items-center justify-between border-b border-register-line px-5 py-4">
              <span className="text-xl font-bold text-white">{APP_NAME}</span>
              <button type="button" onClick={() => onOpenChange(false)} aria-label={t.closeHistory} className="rounded p-1 hover:bg-register-deep">
                <X className="size-5" aria-hidden />
              </button>
            </div>
            {panel}
          </aside>
        </div>
      )}
    </>
  )
}

function ChatItem({ chat, active, onSelect, onRemove }: { chat: Chat; active: boolean; onSelect: () => void; onRemove: () => void }) {
  const { t, lang } = useI18n()
  const reading = chat.messages.some((m) => m.kind === 'pending' && m.task === 'reading')
  const title = chat.vendor ?? (chat.invoice ? t.untitled(chat.invoice.name) : t.noInvoiceChat)
  const time = new Date(chat.createdAt).toLocaleTimeString(lang === 'fr' ? 'fr-FR' : 'en-GB', { hour: '2-digit', minute: '2-digit' })
  const sub = reading ? t.readingShort : [chat.total && `${chat.total} DA`, time].filter(Boolean).join(' · ')
  const flag = !reading && chat.review

  return (
    <li className="group relative">
      <button
        type="button"
        onClick={onSelect}
        aria-current={active ? 'true' : undefined}
        className={`flex w-full items-center gap-3 rounded-lg py-2 pl-2 pr-9 text-left ${active ? 'bg-register-deep text-white' : 'hover:bg-register-deep/60'}`}
      >
        {chat.invoice ? (
          <img src={chat.invoice.url} alt="" className="h-11 w-8 shrink-0 bg-white object-cover object-top" />
        ) : (
          <span className="h-11 w-8 shrink-0 rounded-sm border border-dashed border-register-line" aria-hidden />
        )}
        <span className="min-w-0">
          <span className="block truncate text-sm font-semibold">{title}</span>
          <span className="block truncate text-xs text-[#a9c2b8]">
            {flag && <span className="mr-1.5 font-semibold text-[#f0a49b]">{t.toReview} ·</span>}
            {sub}
          </span>
        </span>
      </button>
      <button
        type="button"
        onClick={onRemove}
        aria-label={t.deleteChat(title)}
        className="absolute right-1.5 top-1/2 -translate-y-1/2 rounded p-1.5 text-[#a9c2b8] opacity-0 hover:bg-register hover:text-white focus-visible:opacity-100 group-hover:opacity-100 max-md:opacity-100"
      >
        <Trash2 className="size-4" aria-hidden />
      </button>
    </li>
  )
}

/** Two plain buttons, the current one filled: switching is one click and always visible. */
function LanguageSwitch() {
  const { lang, setLang } = useI18n()
  return (
    <fieldset className="flex shrink-0 overflow-hidden rounded-md border border-register-line text-xs font-semibold">
      <legend className="sr-only">Language / Langue</legend>
      {LANGS.map((l) => (
        <button
          key={l}
          type="button"
          lang={l}
          aria-pressed={lang === l}
          title={MESSAGES[l].langName}
          onClick={() => setLang(l)}
          className={`px-2.5 py-1 uppercase tracking-wide ${lang === l ? 'bg-[#e7efe9] text-register' : 'text-[#a9c2b8] hover:text-white'}`}
        >
          {l}
        </button>
      ))}
    </fieldset>
  )
}
