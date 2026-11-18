import { FileSearch, Languages, Quote } from 'lucide-react'

const EXAMPLES = [
  { flag: '🇬🇧', text: 'What is the fee for retaking an exam?' },
  { flag: '🇺🇿', text: 'Stipendiya olish uchun qanday shartlar bor?' },
  { flag: '🇷🇺', text: 'До какого числа нужно оплатить обучение?' },
]

const FEATURES = [
  { icon: FileSearch, title: 'Hybrid search', text: 'Keyword + semantic search finds the right passage.' },
  { icon: Languages, title: '3 languages', text: 'Ask in Uzbek, Russian or English.' },
  { icon: Quote, title: 'Cited answers', text: 'Every claim links to its file and page.' },
]

interface Props {
  hasDocuments: boolean
  onAsk: (question: string) => void
  onLoadSample: () => void
  loadingSample: boolean
}

export function EmptyState({ hasDocuments, onAsk, onLoadSample, loadingSample }: Props) {
  return (
    <div className="aurora relative flex flex-1 flex-col items-center justify-center px-6 py-12 text-center">
      <img src="/favicon.svg" alt="" className="size-14 rounded-2xl shadow-2xl shadow-iris/30" />
      <h1 className="mt-6 text-3xl font-extrabold tracking-tight text-white sm:text-4xl">
        Ask your documents <span className="brand-text">anything</span>
      </h1>
      <p className="mt-3 max-w-md text-[15px] text-zinc-400">
        Upload PDFs, contracts, handbooks or lecture notes. Hujjat AI answers using only what's inside, and shows you
        the exact page.
      </p>

      {hasDocuments ? (
        <div className="mt-8 grid w-full max-w-xl gap-2">
          {EXAMPLES.map((e) => (
            <button
              key={e.text}
              onClick={() => onAsk(e.text)}
              className="flex items-center gap-3 rounded-xl bg-ink-850/80 px-4 py-3 text-left text-sm text-zinc-300 ring-1 ring-white/5 backdrop-blur transition hover:text-white hover:ring-clay/50"
            >
              <span className="text-base">{e.flag}</span>
              {e.text}
            </button>
          ))}
        </div>
      ) : (
        <button
          onClick={onLoadSample}
          disabled={loadingSample}
          className="brand-gradient mt-8 rounded-xl px-5 py-3 text-sm font-semibold text-white shadow-lg shadow-clay/20 transition hover:brightness-110 disabled:opacity-60"
        >
          {loadingSample ? 'Loading sample…' : 'Try it with a sample student handbook'}
        </button>
      )}

      <div className="mt-12 grid w-full max-w-2xl gap-3 sm:grid-cols-3">
        {FEATURES.map(({ icon: Icon, title, text }) => (
          <div key={title} className="rounded-2xl bg-ink-850/60 p-4 text-left ring-1 ring-white/5">
            <Icon className="size-5 text-clay" />
            <p className="mt-3 text-sm font-semibold text-zinc-100">{title}</p>
            <p className="mt-1 text-xs leading-relaxed text-zinc-500">{text}</p>
          </div>
        ))}
      </div>
    </div>
  )
}
