import { ArrowUp, Square } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'

interface Props {
  disabled: boolean
  busy: boolean
  scopeLabel: string
  onSend: (text: string) => void
  onStop: () => void
}

export function Composer({ disabled, busy, scopeLabel, onSend, onStop }: Props) {
  const [text, setText] = useState('')
  const ref = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    const el = ref.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = `${Math.min(el.scrollHeight, 180)}px`
  }, [text])

  const submit = () => {
    const q = text.trim()
    if (!q || disabled || busy) return
    onSend(q)
    setText('')
  }

  return (
    <div className="border-t border-white/5 bg-ink-950/80 px-4 pt-3 pb-4 backdrop-blur sm:px-8">
      <div className="mx-auto max-w-3xl">
        <div className="flex items-end gap-2 rounded-2xl bg-ink-850 p-2 ring-1 ring-white/10 transition focus-within:ring-clay/60">
          <textarea
            ref={ref}
            rows={1}
            value={text}
            disabled={disabled}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault()
                submit()
              }
            }}
            placeholder={disabled ? 'Upload a document to start…' : 'Ask in Uzbek, Russian or English…'}
            className="max-h-44 flex-1 resize-none bg-transparent px-3 py-2 text-[15px] text-zinc-100 placeholder:text-zinc-500 focus:outline-none disabled:cursor-not-allowed"
          />
          {busy ? (
            <button
              onClick={onStop}
              className="grid size-10 place-items-center rounded-xl bg-ink-700 text-zinc-200 transition hover:bg-ink-600"
              aria-label="Stop generating"
            >
              <Square className="size-4 fill-current" />
            </button>
          ) : (
            <button
              onClick={submit}
              disabled={disabled || !text.trim()}
              className="brand-gradient grid size-10 place-items-center rounded-xl text-white shadow-lg shadow-clay/20 transition hover:brightness-110 disabled:opacity-40 disabled:shadow-none"
              aria-label="Send"
            >
              <ArrowUp className="size-5" strokeWidth={2.5} />
            </button>
          )}
        </div>
        <p className="mt-2 text-center text-xs text-zinc-500">
          Searching <span className="text-zinc-300">{scopeLabel}</span>
          <span className="hidden sm:inline"> · Enter to send, Shift+Enter for a new line</span>
        </p>
      </div>
    </div>
  )
}
