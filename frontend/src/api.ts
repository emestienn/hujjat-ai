export interface DocumentInfo {
  id: string
  filename: string
  pages: number
  chunks: number
  size_bytes: number
  created_at: string
}

export interface Source {
  index: number
  document_id: string
  filename: string
  page: number
  text: string
  score: number
}

export interface Health {
  status: string
  provider: 'claude' | 'gemini' | 'demo'
  semantic_search: boolean
  documents: number
}

export interface ChatTurn {
  role: 'user' | 'assistant'
  content: string
}

async function json<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let message = `Request failed (${res.status})`
    try {
      const body = await res.json()
      if (typeof body.detail === 'string') message = body.detail
    } catch {
      /* keep the generic message */
    }
    throw new Error(message)
  }
  return res.json() as Promise<T>
}

export const api = {
  health: () => fetch('/api/health').then((r) => json<Health>(r)),

  listDocuments: () => fetch('/api/documents').then((r) => json<DocumentInfo[]>(r)),

  upload: (file: File) => {
    const body = new FormData()
    body.append('file', file)
    return fetch('/api/documents', { method: 'POST', body }).then((r) => json<DocumentInfo>(r))
  },

  remove: async (id: string) => {
    const res = await fetch(`/api/documents/${id}`, { method: 'DELETE' })
    if (!res.ok && res.status !== 404) throw new Error('Could not delete the document')
  },
}

export interface StreamHandlers {
  onSources: (sources: Source[]) => void
  onToken: (token: string) => void
  onDone: (provider: string) => void
  onError: (message: string) => void
}

/** POST a question and read the Server-Sent Events stream from /api/chat/stream. */
export async function streamChat(
  body: { question: string; document_ids: string[] | null; history: ChatTurn[] },
  handlers: StreamHandlers,
  signal?: AbortSignal,
) {
  const res = await fetch('/api/chat/stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    signal,
  })
  if (!res.ok || !res.body) {
    let message = 'The server did not return a stream'
    try {
      await json<unknown>(res)
    } catch (e) {
      message = (e as Error).message
    }
    handlers.onError(message)
    return
  }

  const reader = res.body.pipeThrough(new TextDecoderStream()).getReader()
  let buffer = ''
  for (;;) {
    const { value, done } = await reader.read()
    if (done) break
    buffer += value
    let sep: number
    while ((sep = buffer.indexOf('\n\n')) !== -1) {
      const block = buffer.slice(0, sep)
      buffer = buffer.slice(sep + 2)
      const event = /^event: (.*)$/m.exec(block)?.[1]
      const data = /^data: (.*)$/m.exec(block)?.[1]
      if (!event || data === undefined) continue
      const payload = JSON.parse(data)
      if (event === 'sources') handlers.onSources(payload)
      else if (event === 'token') handlers.onToken(payload)
      else if (event === 'done') handlers.onDone(payload.provider)
      else if (event === 'error') handlers.onError(payload.message)
    }
  }
}
