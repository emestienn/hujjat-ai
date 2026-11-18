import clsx from 'clsx'
import { Check, FileText, Loader2, Sparkles, Trash2, UploadCloud, X, Zap } from 'lucide-react'
import { useRef, useState } from 'react'
import type { DocumentInfo, Health } from '../api'
import { Logo } from './Logo'

interface Props {
  health: Health | null
  documents: DocumentInfo[]
  selected: Set<string>
  uploading: string[]
  onToggle: (id: string) => void
  onUpload: (files: File[]) => void
  onDelete: (id: string) => void
  onClose?: () => void
}

const PROVIDER_LABEL = { claude: 'Claude', gemini: 'Gemini', demo: 'Demo mode' } as const

function formatSize(bytes: number) {
  if (bytes < 1024 * 1024) return `${Math.max(1, Math.round(bytes / 1024))} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

export function Sidebar({ health, documents, selected, uploading, onToggle, onUpload, onDelete, onClose }: Props) {
  const input = useRef<HTMLInputElement>(null)
  const [dragging, setDragging] = useState(false)

  const handleFiles = (list: FileList | null) => {
    if (list?.length) onUpload(Array.from(list))
  }

  return (
    <aside className="flex h-full w-80 shrink-0 flex-col border-r border-white/5 bg-ink-900">
      <div className="flex items-center justify-between px-5 pt-5 pb-4">
        <Logo />
        {onClose && (
          <button onClick={onClose} className="rounded-lg p-1.5 text-zinc-400 hover:bg-white/5 lg:hidden" aria-label="Close">
            <X className="size-5" />
          </button>
        )}
      </div>

      {health && (
        <div className="mx-5 mb-4 flex flex-wrap gap-2 text-xs">
          <span
            className={clsx(
              'inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 font-medium ring-1',
              health.provider === 'demo'
                ? 'bg-amber-500/10 text-amber-300 ring-amber-500/20'
                : 'bg-emerald-500/10 text-emerald-300 ring-emerald-500/20',
            )}
          >
            <Sparkles className="size-3" />
            {PROVIDER_LABEL[health.provider]}
          </span>
          <span className="inline-flex items-center gap-1.5 rounded-full bg-white/5 px-2.5 py-1 font-medium text-zinc-400 ring-1 ring-white/10">
            <Zap className="size-3" />
            {health.semantic_search ? 'Hybrid search' : 'Keyword search'}
          </span>
        </div>
      )}

      <div className="px-5">
        <button
          onClick={() => input.current?.click()}
          onDragOver={(e) => {
            e.preventDefault()
            setDragging(true)
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={(e) => {
            e.preventDefault()
            setDragging(false)
            handleFiles(e.dataTransfer.files)
          }}
          className={clsx(
            'group flex w-full flex-col items-center gap-2 rounded-2xl border border-dashed px-4 py-6 text-center transition',
            dragging
              ? 'border-clay bg-clay/10'
              : 'border-white/10 bg-white/[0.02] hover:border-clay/60 hover:bg-white/[0.04]',
          )}
        >
          <span className="brand-gradient grid size-10 place-items-center rounded-xl shadow-lg shadow-clay/20 transition group-hover:scale-105">
            <UploadCloud className="size-5 text-white" />
          </span>
          <span className="text-sm font-semibold text-zinc-100">Upload documents</span>
          <span className="text-xs text-zinc-500">PDF, DOCX, TXT · drag & drop</span>
        </button>
        <input
          ref={input}
          type="file"
          multiple
          accept=".pdf,.docx,.txt,.md"
          className="hidden"
          onChange={(e) => {
            handleFiles(e.target.files)
            e.target.value = ''
          }}
        />
      </div>

      <div className="mt-6 flex items-center justify-between px-5 text-[11px] font-semibold tracking-wider text-zinc-500 uppercase">
        <span>Your documents</span>
        <span>{documents.length}</span>
      </div>

      <ul className="mt-2 flex-1 space-y-1 overflow-y-auto px-3 pb-4">
        {uploading.map((name) => (
          <li key={name} className="flex items-center gap-3 rounded-xl px-2 py-2.5 text-sm text-zinc-400">
            <Loader2 className="size-4 animate-spin text-clay" />
            <span className="truncate">Indexing {name}…</span>
          </li>
        ))}

        {documents.map((doc) => {
          const active = selected.has(doc.id)
          return (
            <li key={doc.id} className="animate-fade-up">
              <div
                className={clsx(
                  'group flex items-center gap-3 rounded-xl px-2 py-2.5 transition',
                  active ? 'bg-white/[0.06] ring-1 ring-white/10' : 'hover:bg-white/[0.03]',
                )}
              >
                <button
                  onClick={() => onToggle(doc.id)}
                  className={clsx(
                    'grid size-5 shrink-0 place-items-center rounded-md ring-1 transition',
                    active ? 'brand-gradient ring-transparent' : 'ring-white/20 hover:ring-white/40',
                  )}
                  aria-label={active ? `Stop searching ${doc.filename}` : `Search only ${doc.filename}`}
                  title="Limit questions to selected documents"
                >
                  {active && <Check className="size-3.5 text-white" strokeWidth={3} />}
                </button>
                <FileText className="size-4 shrink-0 text-zinc-500" />
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium text-zinc-200" title={doc.filename}>
                    {doc.filename}
                  </p>
                  <p className="text-xs text-zinc-500">
                    {doc.pages} {doc.pages === 1 ? 'page' : 'pages'} · {formatSize(doc.size_bytes)}
                  </p>
                </div>
                <button
                  onClick={() => onDelete(doc.id)}
                  className="rounded-lg p-1.5 text-zinc-500 opacity-0 transition group-hover:opacity-100 hover:bg-red-500/10 hover:text-red-400 focus:opacity-100"
                  aria-label={`Delete ${doc.filename}`}
                >
                  <Trash2 className="size-4" />
                </button>
              </div>
            </li>
          )
        })}

        {!documents.length && !uploading.length && (
          <li className="px-2 py-6 text-center text-sm text-zinc-500">
            No documents yet. Upload a PDF to start asking questions.
          </li>
        )}
      </ul>

      <div className="border-t border-white/5 px-5 py-4 text-xs text-zinc-500">
        Answers come only from your files, with page citations.
      </div>
    </aside>
  )
}
