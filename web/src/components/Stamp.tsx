import { useI18n } from '../i18n.tsx'

interface Props {
  verdict: 'verified' | 'review'
}

/** The office rubber stamp: violet ink, slightly crooked, pressed once. */
export function Stamp({ verdict }: Props) {
  const { t } = useI18n()
  const ok = verdict === 'verified'
  return (
    <div
      className={`stamp stamp-in pointer-events-none select-none rounded-[10px] border-[3px] px-4 py-2 text-center font-bold uppercase leading-none tracking-[0.12em] ${
        ok ? 'border-stamp text-stamp' : 'border-refuse text-refuse'
      }`}
    >
      <span className="sr-only">{ok ? t.stamp.verifiedSr : t.stamp.reviewSr}</span>
      <div aria-hidden className="text-[19px]">{ok ? t.stamp.verified : t.stamp.review}</div>
      <div aria-hidden className="mt-1 border-t-2 border-current pt-1 text-[10px] tracking-[0.2em]">{ok ? t.stamp.verifiedSub : t.stamp.reviewSub}</div>
    </div>
  )
}
