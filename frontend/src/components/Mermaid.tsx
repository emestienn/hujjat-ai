import { useEffect, useId, useRef, useState } from 'react'

let mermaidModule: Promise<typeof import('mermaid').default> | null = null

/** Loaded on first use (mermaid is large), configured once, then cached for reuse. */
function loadMermaid() {
  if (!mermaidModule) {
    mermaidModule = import('mermaid').then(({ default: mermaid }) => {
      mermaid.initialize({
        startOnLoad: false,
        securityLevel: 'strict',
        theme: 'base',
        fontFamily: 'Plus Jakarta Sans, ui-sans-serif, system-ui, sans-serif',
        themeVariables: {
          darkMode: true,
          background: '#0d0f15',
          primaryColor: '#181c26',
          primaryTextColor: '#e4e4e7',
          primaryBorderColor: '#e8875f',
          secondaryColor: '#232836',
          secondaryBorderColor: '#8e75b2',
          tertiaryColor: '#12151d',
          lineColor: '#71717a',
          textColor: '#e4e4e7',
        },
      })
      return mermaid
    })
  }
  return mermaidModule
}

// mermaid.render() keeps shared internal state and isn't safe to call concurrently (two
// overlapping calls can corrupt each other's output). React 19 StrictMode double-invokes
// effects in dev, which triggers exactly that, so every render is queued through here.
let renderQueue: Promise<unknown> = Promise.resolve()

function renderMermaid(id: string, code: string) {
  const result = renderQueue.then(() => loadMermaid().then((mermaid) => mermaid.render(id, code)))
  renderQueue = result.catch(() => {})
  return result
}

interface Props {
  code: string
  /** False while the answer is still streaming: the diagram source may be cut mid-syntax. */
  ready: boolean
}

/** Renders a ```mermaid code block as an SVG diagram (flowcharts, trees, graphs, pie/xy charts, …). */
export function Mermaid({ code, ready }: Props) {
  const rawId = useId().replace(/[^a-zA-Z0-9]/g, '')
  const attempt = useRef(0)
  const [svg, setSvg] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!ready) return
    let cancelled = false
    const id = `mermaid-${rawId}-${++attempt.current}`
    setError(null)
    renderMermaid(id, code)
      .then(({ svg }) => {
        if (!cancelled) setSvg(svg)
      })
      .catch((e: unknown) => {
        if (!cancelled) setError(e instanceof Error ? e.message : String(e))
        document.getElementById(id)?.remove() // mermaid can leave a detached error node behind
      })
    return () => {
      cancelled = true
    }
  }, [code, ready, rawId])

  if (!ready || (!svg && !error)) {
    return (
      <pre className="my-3 overflow-x-auto rounded-xl bg-ink-800 p-3 font-mono text-xs text-zinc-500">
        {ready ? 'Rendering diagram…' : code}
      </pre>
    )
  }

  if (error) {
    return (
      <div className="my-3 space-y-2">
        <p className="text-xs text-red-300">Couldn't render this diagram.</p>
        <pre className="overflow-x-auto rounded-xl bg-ink-800 p-3 font-mono text-xs text-zinc-500">{code}</pre>
      </div>
    )
  }

  return (
    // eslint-disable-next-line react/no-danger -- svg comes from our own mermaid.render() call, not raw model output
    <div
      className="my-3 overflow-x-auto rounded-xl bg-white/[0.03] p-4 [&_svg]:mx-auto"
      dangerouslySetInnerHTML={{ __html: svg! }}
    />
  )
}
