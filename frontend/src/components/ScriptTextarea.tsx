import { forwardRef, useImperativeHandle, useMemo, useRef, useState } from 'react'
import {
  ScriptToken,
  TAG_COLORS,
  SCRIPT_TAGS,
  tokenizeScript,
  countWords,
  estimateMinutes,
  splitByQuery,
} from '../utils/scriptHighlight'

export interface ScriptTextareaHandle {
  insertAtCursor: (snippet: string) => void
  focus: () => void
}

interface Props {
  value: string
  onChange: (value: string) => void
  placeholder?: string
  autoFocus?: boolean
  minHeight?: string
  /** Muestra la botonera de etiquetas de emoción/prosodia/sfx. */
  showTagButtons?: boolean
  /** Minutos objetivo para teñir el contador (null = sin objetivo). */
  targetMinutes?: number | null
  className?: string
}

// Editor de guion "potenciado" sin dependencias: textarea real transparente
// sobre un <pre> que pinta las etiquetas <|...|> como chips de color, con
// números de línea, buscar/reemplazar y pantalla completa. El valor que se
// edita y guarda es siempre texto plano, igual que antes.

const EDITOR_FONT =
  'font-sans text-[15px] leading-7 tracking-normal whitespace-pre-wrap break-words'

function renderTokens(tokens: ScriptToken[], query: string) {
  return tokens.map((token, i) => {
    if (token.type === 'tag' && token.tagKind) {
      const colors = TAG_COLORS[token.tagKind]
      return (
        <span
          key={i}
          className={`rounded border px-1 text-[12px] leading-7 font-medium ${colors.chip}`}
          title={`<|${token.tagKind}:${token.tagName}|>`}
        >
          {token.tagKind}:{token.tagName}
        </span>
      )
    }
    return splitByQuery(token, query).map((part, j) =>
      part.match ? (
        <mark key={`${i}-${j}`} className="bg-yellow-400/40 text-inherit rounded-sm">
          {part.value}
        </mark>
      ) : (
        <span key={`${i}-${j}`}>{part.value}</span>
      )
    )
  })
}

const ScriptTextarea = forwardRef<ScriptTextareaHandle, Props>(function ScriptTextarea(
  {
    value,
    onChange,
    placeholder,
    autoFocus,
    minHeight = '300px',
    showTagButtons = true,
    targetMinutes = null,
    className = '',
  },
  ref
) {
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const preRef = useRef<HTMLPreElement>(null)
  const gutterRef = useRef<HTMLDivElement>(null)
  const [query, setQuery] = useState('')
  const [replaceWith, setReplaceWith] = useState('')
  const [showSearch, setShowSearch] = useState(false)
  const [fullscreen, setFullscreen] = useState(false)

  const tokens = useMemo(() => tokenizeScript(value), [value])
  const words = useMemo(() => countWords(value), [value])
  const minutes = useMemo(() => estimateMinutes(value), [value])
  const lineCount = useMemo(() => value.split('\n').length, [value])
  const matchCount = useMemo(() => {
    if (!query) return 0
    return value.toLowerCase().split(query.toLowerCase()).length - 1
  }, [value, query])

  const syncScroll = () => {
    const ta = textareaRef.current
    if (!ta) return
    if (preRef.current) {
      preRef.current.scrollTop = ta.scrollTop
      preRef.current.scrollLeft = ta.scrollLeft
    }
    if (gutterRef.current) gutterRef.current.scrollTop = ta.scrollTop
  }

  const insertAtCursor = (snippet: string) => {
    const ta = textareaRef.current
    if (!ta) {
      onChange(value + snippet)
      return
    }
    const start = ta.selectionStart ?? value.length
    const end = ta.selectionEnd ?? value.length
    const next = value.slice(0, start) + snippet + value.slice(end)
    onChange(next)
    const pos = start + snippet.length
    requestAnimationFrame(() => {
      ta.focus()
      ta.setSelectionRange(pos, pos)
      syncScroll()
    })
  }

  useImperativeHandle(ref, () => ({
    insertAtCursor,
    focus: () => textareaRef.current?.focus(),
  }))

  const jumpToMatch = (direction: 1 | -1) => {
    const ta = textareaRef.current
    if (!ta || !query) return
    const lower = value.toLowerCase()
    const q = query.toLowerCase()
    const from = direction === 1 ? ta.selectionEnd : ta.selectionStart - 1
    let idx = direction === 1 ? lower.indexOf(q, from) : lower.lastIndexOf(q, Math.max(0, from))
    if (idx === -1) {
      idx = direction === 1 ? lower.indexOf(q) : lower.lastIndexOf(q)
    }
    if (idx !== -1) {
      ta.focus()
      ta.setSelectionRange(idx, idx + q.length)
      const lineHeight = 28
      const line = value.slice(0, idx).split('\n').length - 1
      ta.scrollTop = Math.max(0, line * lineHeight - ta.clientHeight / 2)
      syncScroll()
    }
  }

  const replaceCurrent = () => {
    const ta = textareaRef.current
    if (!ta || !query) return
    const sel = value.slice(ta.selectionStart, ta.selectionEnd)
    if (sel.toLowerCase() === query.toLowerCase()) {
      const next = value.slice(0, ta.selectionStart) + replaceWith + value.slice(ta.selectionEnd)
      onChange(next)
      requestAnimationFrame(() => {
        ta.focus()
        ta.setSelectionRange(ta.selectionStart, ta.selectionStart)
      })
    } else {
      jumpToMatch(1)
    }
  }

  const replaceAll = () => {
    if (!query) return
    const escaped = query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
    onChange(value.replace(new RegExp(escaped, 'gi'), replaceWith))
  }

  const pad = 'px-4 py-3'
  const lineNumbers = useMemo(
    () => Array.from({ length: lineCount }, (_, i) => i + 1).join('\n'),
    [lineCount]
  )

  const editorBody = (
    <div
      className={`flex flex-1 min-h-0 border border-slate-600 rounded-lg overflow-hidden bg-slate-800 focus-within:ring-2 focus-within:ring-purple-500 ${className}`}
    >
      {/* Números de línea */}
      <div
        ref={gutterRef}
        aria-hidden
        className={`shrink-0 w-10 overflow-hidden bg-slate-900/70 text-right text-slate-600 select-none ${EDITOR_FONT} py-3 pr-2 border-r border-slate-700/60`}
        style={{ minHeight }}
      >
        {lineNumbers}
      </div>

      <div className="relative flex-1 min-w-0">
        {/* Capa de resaltado */}
        <pre
          ref={preRef}
          aria-hidden
          className={`absolute inset-0 m-0 overflow-hidden ${EDITOR_FONT} ${pad} text-slate-100 pointer-events-none`}
          style={{ minHeight }}
        >
          {renderTokens(tokens, query)}
          {'\n'}
        </pre>
        {/* Textarea real (texto transparente, caret visible) */}
        <textarea
          ref={textareaRef}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onScroll={syncScroll}
          placeholder={placeholder}
          autoFocus={autoFocus}
          spellCheck={false}
          data-testid="script-textarea"
          className={`absolute inset-0 w-full h-full resize-none bg-transparent ${EDITOR_FONT} ${pad} text-transparent caret-slate-100 placeholder:text-slate-500 placeholder:text-transparent focus:outline-none selection:bg-purple-500/30 selection:text-transparent`}
          style={{ minHeight }}
        />
      </div>
    </div>
  )

  return (
    <div className={`flex flex-col gap-2 min-h-0 ${fullscreen ? 'fixed inset-0 z-[70] bg-slate-950 p-4 gap-3' : 'flex-1'}`}>
      {/* Toolbar */}
      <div className="flex items-center gap-2 flex-wrap shrink-0">
        {showTagButtons && (
          <div className="flex flex-wrap gap-1.5 flex-1 min-w-0">
            {SCRIPT_TAGS.map((tag) => (
              <button
                key={tag}
                type="button"
                onClick={() => insertAtCursor(tag + ' ')}
                title={tag}
                className="text-[11px] px-2 py-0.5 rounded border bg-purple-900/40 border-purple-700/50 text-purple-300 hover:bg-purple-800/60 transition-colors"
              >
                {tag.replace('<|', '').replace('|>', '')}
              </button>
            ))}
          </div>
        )}
        <div className="flex items-center gap-2 shrink-0 ml-auto">
          <span className="text-xs text-slate-500 whitespace-nowrap">
            {words.toLocaleString()} palabras · ~{minutes} min
            {targetMinutes != null && (
              <span className={minutes >= targetMinutes ? 'text-green-400' : 'text-amber-400'}>
                {' '}/ objetivo {targetMinutes} min
              </span>
            )}
          </span>
          <button
            type="button"
            onClick={() => setShowSearch((s) => !s)}
            title="Buscar y reemplazar"
            className={`text-xs px-2 py-1 rounded border transition-colors ${
              showSearch
                ? 'bg-slate-600 border-slate-500 text-slate-100'
                : 'bg-slate-800 border-slate-600 text-slate-400 hover:text-slate-200'
            }`}
          >
            🔍 Buscar
          </button>
          <button
            type="button"
            onClick={() => setFullscreen((f) => !f)}
            title={fullscreen ? 'Salir de pantalla completa' : 'Pantalla completa'}
            className="text-xs px-2 py-1 rounded border bg-slate-800 border-slate-600 text-slate-400 hover:text-slate-200 transition-colors"
          >
            {fullscreen ? '⤡ Salir' : '⤢ Pantalla completa'}
          </button>
        </div>
      </div>

      {/* Buscar y reemplazar */}
      {showSearch && (
        <div className="flex items-center gap-2 flex-wrap shrink-0 text-sm">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter') jumpToMatch(e.shiftKey ? -1 : 1) }}
            placeholder="Buscar…"
            className="bg-slate-800 border border-slate-600 rounded-lg px-3 py-1.5 text-slate-100 focus:outline-none focus:ring-2 focus:ring-purple-500 w-48"
          />
          <span className="text-xs text-slate-500" data-testid="match-count">
            {query ? `${matchCount} coincidencia${matchCount === 1 ? '' : 's'}` : ''}
          </span>
          <button type="button" onClick={() => jumpToMatch(-1)} disabled={!query} className="px-2 py-1 rounded bg-slate-700 text-slate-200 disabled:opacity-40">↑</button>
          <button type="button" onClick={() => jumpToMatch(1)} disabled={!query} className="px-2 py-1 rounded bg-slate-700 text-slate-200 disabled:opacity-40">↓</button>
          <input
            type="text"
            value={replaceWith}
            onChange={(e) => setReplaceWith(e.target.value)}
            placeholder="Reemplazar por…"
            className="bg-slate-800 border border-slate-600 rounded-lg px-3 py-1.5 text-slate-100 focus:outline-none focus:ring-2 focus:ring-purple-500 w-48"
          />
          <button type="button" onClick={replaceCurrent} disabled={!query} className="px-2 py-1 rounded bg-slate-700 text-slate-200 disabled:opacity-40">Reemplazar</button>
          <button type="button" onClick={replaceAll} disabled={!query} className="px-2 py-1 rounded bg-slate-700 text-slate-200 disabled:opacity-40">Reemplazar todo</button>
        </div>
      )}

      {editorBody}
    </div>
  )
})

export default ScriptTextarea
