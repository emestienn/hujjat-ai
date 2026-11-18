import clsx from 'clsx'
import { AlertTriangle, Check, Copy, FileText } from 'lucide-react'
import { isValidElement, useState, type ReactNode } from 'react'
import Markdown from 'react-markdown'
import rehypeKatex from 'rehype-katex'
import remarkGfm from 'remark-gfm'
import remarkMath from 'remark-math'
import type { Source } from '../api'
import { Mermaid } from './Mermaid'

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  sources?: Source[]
  streaming?: boolean
  error?: string
}

interface Props {
  message: ChatMessage
  onOpenSource: (source: Source) => void
}

/** Turn "[1]" citations into markdown links that we render as clickable chips. */
const linkCitations = (text: string) => text.replace(/\[(\d+)\](?!\()/g, '[$1](#cite-$1)')

export function Message({ message, onOpenSource }: Props) {
  const [copied, setCopied] = useState(false)

  if (message.role === 'user') {
    return (
      <div className="flex animate-fade-up justify-end">
        <div className="max-w-[80%] rounded-2xl rounded-br-md bg-ink-700 px-4 py-2.5 text-[15px] leading-relaxed text-zinc-100">
          {message.content}
        </div>
      </div>
    )
  }

  const sources = message.sources ?? []
  const byIndex = new Map(sources.map((s) => [s.index, s]))
  const waiting = message.streaming && !message.content

  return (
    <div className="flex animate-fade-up gap-3">
      <img src="/favicon.svg" alt="" className="mt-0.5 size-8 shrink-0 rounded-lg" />
      <div className="min-w-0 flex-1">
        {waiting ? (
          <div className="flex items-center gap-1.5 py-2" aria-label="Thinking">
            {[0, 150, 300].map((d) => (
              <span key={d} className="size-2 animate-bounce rounded-full bg-zinc-500" style={{ animationDelay: `${d}ms` }} />
            ))}
            <span className="ml-2 text-sm text-zinc-500">Searching your documents…</span>
          </div>
        ) : (
          <div className="prose prose-invert max-w-none text-[15px] prose-p:leading-relaxed prose-li:my-0.5 prose-ul:my-2">
            <Markdown
              remarkPlugins={[remarkGfm, remarkMath]}
              rehypePlugins={[rehypeKatex]}
              components={{
                a: ({ href, children }) => {
                  const match = href?.match(/^#cite-(\d+)$/)
                  const source = match ? byIndex.get(Number(match[1])) : undefined
                  if (!source) return <a href={href}>{children}</a>
                  return (
                    <button
                      onClick={() => onOpenSource(source)}
                      title={`${source.filename} · page ${source.page}`}
                      className="brand-gradient mx-0.5 inline-grid h-5 min-w-5 -translate-y-0.5 place-items-center rounded-md px-1 align-middle text-[11px] font-bold text-white no-underline shadow-sm transition hover:brightness-110"
                    >
                      {source.index}
                    </button>
                  )
                },
                // Fenced ```mermaid blocks become flowcharts/trees/graphs/charts instead of raw text.
                pre: ({ children }) => {
                  const code = Array.isArray(children) ? children[0] : children
                  if (
                    isValidElement<{ className?: string; children?: ReactNode }>(code) &&
                    /(?:^|\s)language-mermaid(?:\s|$)/.test(code.props.className ?? '')
                  ) {
                    return <Mermaid code={String(code.props.children).replace(/\n$/, '')} ready={!message.streaming} />
                  }
                  return <pre>{children}</pre>
                },
              }}
            >
              {linkCitations(message.content)}
            </Markdown>
            {message.streaming && <span className="ml-0.5 inline-block h-4 w-2 animate-blink bg-clay align-middle" />}
          </div>
        )}

        {message.error && (
          <div className="mt-3 flex items-start gap-2 rounded-xl bg-red-500/10 px-3 py-2.5 text-sm text-red-300 ring-1 ring-red-500/20">
            <AlertTriangle className="mt-0.5 size-4 shrink-0" />
            {message.error}
          </div>
        )}

        {!message.streaming && sources.length > 0 && (
          <div className="mt-4">
            <p className="mb-2 text-[11px] font-semibold tracking-wider text-zinc-500 uppercase">Sources</p>
            <div className="flex flex-wrap gap-2">
              {sources.map((s) => (
                <button
                  key={s.index}
                  onClick={() => onOpenSource(s)}
                  className="group flex max-w-xs items-center gap-2 rounded-xl bg-ink-800 px-3 py-2 text-left text-xs ring-1 ring-white/5 transition hover:ring-clay/50"
                >
                  <span className="brand-gradient grid size-5 shrink-0 place-items-center rounded-md text-[10px] font-bold text-white">
                    {s.index}
                  </span>
                  <FileText className="size-3.5 shrink-0 text-zinc-500" />
                  <span className="truncate text-zinc-300 group-hover:text-white">{s.filename}</span>
                  <span className="shrink-0 text-zinc-500">p. {s.page}</span>
                </button>
              ))}
            </div>
          </div>
        )}

        {!message.streaming && message.content && (
          <button
            onClick={() => {
              navigator.clipboard.writeText(message.content)
              setCopied(true)
              setTimeout(() => setCopied(false), 1500)
            }}
            className={clsx(
              'mt-3 inline-flex items-center gap-1.5 rounded-lg px-2 py-1 text-xs transition',
              copied ? 'text-emerald-400' : 'text-zinc-500 hover:bg-white/5 hover:text-zinc-300',
            )}
          >
            {copied ? <Check className="size-3.5" /> : <Copy className="size-3.5" />}
            {copied ? 'Copied' : 'Copy answer'}
          </button>
        )}
      </div>
    </div>
  )
}
