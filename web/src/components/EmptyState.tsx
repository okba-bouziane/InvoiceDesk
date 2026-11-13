import { SAMPLES } from '../config.ts'
import { useI18n } from '../i18n.tsx'

const TILT = ['-rotate-6 translate-y-2', 'rotate-0 -translate-y-1 z-10', 'rotate-6 translate-y-3']

/** First screen: what to do, and three invoices to pick up if you have none at hand. */
export function EmptyState({ onSample }: { onSample: (file: string, label: string) => void }) {
  const { t } = useI18n()
  return (
    <section className="mx-auto flex max-w-[760px] flex-col items-start gap-8 pt-6 md:pt-14">
      <div>
        <h2 className="text-[clamp(30px,5vw,48px)] font-bold leading-[1.05] tracking-[-0.02em]">
          {t.headline[0]}
          <br />
          {t.headline[1]}
        </h2>
        <p className="mt-4 max-w-[54ch] text-ink-soft">
          {t.intro}
        </p>
      </div>
      <div>
        <p className="mb-4 text-sm text-ink-soft">{t.samplesPrompt}</p>
        <div className="flex items-end">
          {SAMPLES.map((s, i) => (
            <button
              key={s.file}
              type="button"
              onClick={() => onSample(s.file, t.sampleName(i + 1))}
              aria-label={t.sampleAria(i + 1)}
              className={`-mr-6 w-[112px] bg-white p-1 shadow-[0_8px_20px_-10px_rgba(28,36,33,.55)] transition-transform duration-200 last:mr-0 hover:z-20 hover:-translate-y-3 hover:rotate-0 focus-visible:z-20 sm:w-[132px] ${TILT[i]}`}
            >
              <img src={`/samples/${s.file}`} alt="" className="block aspect-[3/4] w-full object-cover object-top" />
            </button>
          ))}
        </div>
      </div>
    </section>
  )
}
