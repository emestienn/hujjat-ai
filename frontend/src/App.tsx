import { Menu, RotateCcw } from 'lucide-react'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { api, streamChat, type DocumentInfo, type Health, type Source } from './api'
import { Composer } from './components/Composer'
import { EmptyState } from './components/EmptyState'
import { Logo } from './components/Logo'
import { Message, type ChatMessage } from './components/Message'
import { Sidebar } from './components/Sidebar'
import { SourcePanel } from './components/SourcePanel'

const uid = () => Math.random().toString(36).slice(2)

export default function App() {
  const [health, setHealth] = useState<Health | null>(null)
  const [documents, setDocuments] = useState<DocumentInfo[]>([])
  const [selected, setSelected] = useState<Set<string>>(new Set())
  const [uploading, setUploading] = useState<string[]>([])
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [busy, setBusy] = useState(false)
  const [openSource, setOpenSource] = useState<{ source: Source; query: string } | null>(null)
  const [toast, setToast] = useState<string | null>(null)
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const abort = useRef<AbortController | null>(null)
  const bottom = useRef<HTMLDivElement>(null)

  const notify = (msg: string) => {
    setToast(msg)
    setTimeout(() => setToast(null), 4000)
  }

  const refresh = useCallback(async () => {
    try {
      const [h, docs] = await Promise.all([api.health(), api.listDocuments()])
      setHealth(h)
      setDocuments(docs)
    } catch {
      notify('Cannot reach the backend. Is the API running on port 8000?')
    }
  }, [])

  useEffect(() => {
    refresh()
  }, [refresh])

  useEffect(() => {
    bottom.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [messages])

  const upload = async (files: File[]) => {
    setUploading((u) => [...u, ...files.map((f) => f.name)])
    for (const file of files) {
      try {
        await api.upload(file)
      } catch (e) {
        notify(`${file.name}: ${(e as Error).message}`)
      } finally {
        setUploading((u) => u.filter((n) => n !== file.name))
      }
    }
    refresh()
  }

  const [loadingSample, setLoadingSample] = useState(false)
  const loadSample = async () => {
    setLoadingSample(true)
    try {
      const blob = await fetch('/samples/student-handbook.pdf').then((r) => r.blob())
      await upload([new File([blob], 'student-handbook.pdf', { type: 'application/pdf' })])
    } finally {
      setLoadingSample(false)
    }
  }

  const remove = async (id: string) => {
    try {
      await api.remove(id)
      setSelected((s) => {
        const next = new Set(s)
        next.delete(id)
        return next
      })
      refresh()
    } catch (e) {
      notify((e as Error).message)
    }
  }

  const toggle = (id: string) =>
    setSelected((s) => {
      const next = new Set(s)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })

  const patchLast = (fn: (m: ChatMessage) => ChatMessage) =>
    setMessages((ms) => [...ms.slice(0, -1), fn(ms[ms.length - 1])])

  const ask = async (question: string) => {
    if (busy) return
    const history = messages
      .filter((m) => !m.error && m.content)
      .slice(-6)
      .map((m) => ({ role: m.role, content: m.content }))

    setMessages((ms) => [
      ...ms,
      { id: uid(), role: 'user', content: question },
      { id: uid(), role: 'assistant', content: '', streaming: true },
    ])
    setBusy(true)
    abort.current = new AbortController()

    try {
      await streamChat(
        { question, document_ids: selected.size ? [...selected] : null, history },
        {
          onSources: (sources) => patchLast((m) => ({ ...m, sources })),
          onToken: (t) => patchLast((m) => ({ ...m, content: m.content + t })),
          onDone: () => patchLast((m) => ({ ...m, streaming: false })),
          onError: (error) => patchLast((m) => ({ ...m, streaming: false, error })),
        },
        abort.current.signal,
      )
    } catch (e) {
      if ((e as Error).name !== 'AbortError') {
        patchLast((m) => ({ ...m, error: 'Connection lost. Please try again.' }))
      }
    } finally {
      patchLast((m) => ({ ...m, streaming: false }))
      setBusy(false)
    }
  }

  const lastQuestion = useMemo(() => {
    const users = messages.filter((m) => m.role === 'user')
    return users[users.length - 1]?.content ?? ''
  }, [messages])

  const scopeLabel = selected.size
    ? `${selected.size} selected ${selected.size === 1 ? 'document' : 'documents'}`
    : `all documents (${documents.length})`

  const sidebar = (onClose?: () => void) => (
    <Sidebar
      health={health}
      documents={documents}
      selected={selected}
      uploading={uploading}
      onToggle={toggle}
      onUpload={upload}
      onDelete={remove}
      onClose={onClose}
    />
  )

  return (
    <div className="flex h-full">
      <div className="hidden lg:block">{sidebar()}</div>
      {sidebarOpen && (
        <div className="fixed inset-0 z-40 flex lg:hidden">
          {sidebar(() => setSidebarOpen(false))}
          <div className="flex-1 bg-black/50 backdrop-blur-sm" onClick={() => setSidebarOpen(false)} />
        </div>
      )}

      <main className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center justify-between border-b border-white/5 px-4 py-3 sm:px-8">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setSidebarOpen(true)}
              className="rounded-lg p-1.5 text-zinc-400 hover:bg-white/5 lg:hidden"
              aria-label="Open documents"
            >
              <Menu className="size-5" />
            </button>
            <div className="lg:hidden">
              <Logo />
            </div>
            <p className="hidden text-sm text-zinc-400 lg:block">
              {messages.length ? `Chatting with ${scopeLabel}` : 'New conversation'}
            </p>
          </div>
          {messages.length > 0 && (
            <button
              onClick={() => {
                abort.current?.abort()
                setMessages([])
                setOpenSource(null)
              }}
              className="inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm text-zinc-400 transition hover:bg-white/5 hover:text-zinc-200"
            >
              <RotateCcw className="size-4" />
              New chat
            </button>
          )}
        </header>

        {messages.length === 0 ? (
          <EmptyState
            hasDocuments={documents.length > 0}
            onAsk={ask}
            onLoadSample={loadSample}
            loadingSample={loadingSample}
          />
        ) : (
          <div className="flex-1 overflow-y-auto">
            <div className="mx-auto max-w-3xl space-y-8 px-4 py-8 sm:px-8">
              {messages.map((m) => (
                <Message key={m.id} message={m} onOpenSource={(source) => setOpenSource({ source, query: lastQuestion })} />
              ))}
              <div ref={bottom} />
            </div>
          </div>
        )}

        <Composer
          disabled={documents.length === 0}
          busy={busy}
          scopeLabel={scopeLabel}
          onSend={ask}
          onStop={() => abort.current?.abort()}
        />
      </main>

      <SourcePanel
        source={openSource?.source ?? null}
        query={openSource?.query ?? ''}
        onClose={() => setOpenSource(null)}
      />

      {toast && (
        <div className="fixed bottom-24 left-1/2 z-50 -translate-x-1/2 animate-fade-up rounded-xl bg-ink-700 px-4 py-3 text-sm text-zinc-100 shadow-2xl ring-1 ring-white/10">
          {toast}
        </div>
      )}
    </div>
  )
}
