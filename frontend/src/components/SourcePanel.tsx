import { FileText, X } from 'lucide-react'
import { Fragment, useEffect } from 'react'
import type { Source } from '../api'

interface Props {
  source: Source | null
  query: string
  onClose: () => void
}

const STOP = new Set(['the', 'and', 'for', 'what', 'how', 'is', 'are', 'uchun', 'nima', 'qanday', 'что', 'как'])

/** Highlight the words from the question inside the passage. */
function highlight(text: string, query: string) {
  const words = query
    .toLowerCase()
    .split(/[^\p{L}\p{N}]+/u)
    .filter((w) => w.length > 2 && !STOP.has(w))
  if (!words.length) return text
  const escaped = words.map((w) => w.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'))
  const re = new RegExp(`(${escaped.join('|')})`, 'giu')
  return text.split(re).map((part, i) => (i % 2 ? <mark key={i}>{part}</mark> : <Fragment key={i}>{part}</Fragment>))
}

export function SourcePanel({ source, query, onClose }: Props) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  if (!source) return null

  return (
    <>
      <div className="fixed inset-0 z-30 bg-black/50 backdrop-blur-sm xl:hidden" onClick={onClose} />
      <aside className="fixed inset-y-0 right-0 z-40 flex w-full max-w-md animate-fade-up flex-col border-l border-white/5 bg-ink-900 xl:static xl:z-auto">
        <header className="flex items-start gap-3 border-b border-white/5 px-5 py-4">
          <span className="brand-gradient grid size-8 shrink-0 place-items-center rounded-lg text-sm font-bold text-white">
            {source.index}
          </span>
          <div className="min-w-0 flex-1">
            <p className="flex items-center gap-1.5 truncate text-sm font-semibold text-white">
              <FileText className="size-4 shrink-0 text-zinc-500" />
              <span className="truncate">{source.filename}</span>
            </p>
            <p className="mt-0.5 text-xs text-zinc-500">
              Page {source.page} · relevance {Math.round(source.score * 100)}%
            </p>
          </div>
          <button onClick={onClose} className="rounded-lg p-1.5 text-zinc-400 hover:bg-white/5" aria-label="Close source">
            <X className="size-5" />
          </button>
        </header>
        <div className="flex-1 overflow-y-auto px-5 py-5">
          <p className="mb-3 text-[11px] font-semibold tracking-wider text-zinc-500 uppercase">Original passage</p>
          <blockquote className="rounded-xl border-l-2 border-clay bg-ink-800/60 px-4 py-3 text-[14px] leading-7 whitespace-pre-wrap text-zinc-300">
            {highlight(source.text, query)}
          </blockquote>
        </div>
      </aside>
    </>
  )
}
