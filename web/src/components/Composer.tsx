import { ArrowUp, Paperclip } from 'lucide-react'
import { useRef, useState } from 'react'
import { MAX_QUESTION } from '../config.ts'
import { useI18n } from '../i18n.tsx'

interface Props {
  busy: boolean
  hasInvoice: boolean
  onFile: (file: File) => void
  onAsk: (q: string) => void
}

export function Composer({ busy, hasInvoice, onFile, onAsk }: Props) {
  const { t } = useI18n()
  const [text, setText] = useState('')
  const file = useRef<HTMLInputElement>(null)

  return (
    <form
      className="mx-auto flex max-w-[760px] items-end gap-2 rounded-xl border border-[#cdd6d0] bg-white p-2 shadow-[0_6px_20px_-14px_rgba(28,36,33,.5)] focus-within:border-register"
      onSubmit={(e) => {
        e.preventDefault()
        onAsk(text)
        setText('')
      }}
    >
      <input
        ref={file}
        type="file"
        accept="image/jpeg,image/png"
        className="hidden"
        aria-label={t.fileLabel}
        onChange={(e) => {
          const f = e.target.files?.[0]
          if (f) onFile(f)
          e.target.value = ''
        }}
      />
      <button
        type="button"
        onClick={() => file.current?.click()}
        disabled={busy}
        className="flex h-10 shrink-0 items-center gap-2 rounded-lg px-3 text-sm font-medium text-register hover:bg-paper disabled:opacity-40"
      >
        <Paperclip className="size-4" aria-hidden />
        <span className="hidden sm:inline">{hasInvoice ? t.attachOther : t.attach}</span>
        <span className="sm:hidden">{t.attachShort}</span>
      </button>
      <label className="sr-only" htmlFor="question">{t.questionLabel}</label>
      <input
        id="question"
        value={text}
        maxLength={MAX_QUESTION}
        autoComplete="off"
        onChange={(e) => setText(e.target.value)}
        placeholder={hasInvoice ? t.placeholderAsk : t.placeholderStart}
        className="h-10 min-w-0 flex-1 bg-transparent px-1 outline-none placeholder:text-[#8a9690] focus-visible:outline-none"
      />
      <button
        type="submit"
        disabled={busy || !text.trim()}
        aria-label={t.send}
        className="grid size-10 shrink-0 place-items-center rounded-lg bg-register text-white hover:bg-register-deep disabled:opacity-30"
      >
        <ArrowUp className="size-5" aria-hidden />
      </button>
    </form>
  )
}
