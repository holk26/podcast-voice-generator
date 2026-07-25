import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { useEffect, useState } from 'react'
import { api } from '../api/client'
import { useVoiceStore } from '../stores/voiceStore'
import { BookResult, BookChapter } from '../types'

export const Route = createFileRoute('/books')({
  component: BooksPage,
})

function BooksPage() {
  const navigate = useNavigate()
  const { voices, fetchVoices } = useVoiceStore()
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<BookResult[]>([])
  const [searching, setSearching] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [selected, setSelected] = useState<BookResult | null>(null)
  const [chapters, setChapters] = useState<BookChapter[]>([])
  const [loadingChapters, setLoadingChapters] = useState(false)
  const [voiceId, setVoiceId] = useState('jorge')
  const [converting, setConverting] = useState<number | null>(null)

  useEffect(() => {
    fetchVoices()
  }, [fetchVoices])

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault()
    setSearching(true)
    setError(null)
    setSelected(null)
    try {
      setResults(await api.searchBooks(query))
    } catch (err) {
      setError(String(err))
    } finally {
      setSearching(false)
    }
  }

  const handleSelect = async (book: BookResult) => {
    setSelected(book)
    setChapters([])
    setLoadingChapters(true)
    setError(null)
    try {
      setChapters(await api.getBookChapters(book.book_id))
    } catch (err) {
      setError(String(err))
    } finally {
      setLoadingChapters(false)
    }
  }

  const handleConvert = async (chapter: BookChapter) => {
    if (!selected) return
    setConverting(chapter.index)
    setError(null)
    try {
      await api.convertBookChapter(selected.book_id, chapter.index, voiceId)
      navigate({ to: '/queue' })
    } catch (err) {
      setError(String(err))
      setConverting(null)
    }
  }

  return (
    <div>
      <h2 className="text-2xl font-bold tracking-tight mb-4">Libros → Audiolibros</h2>
      <p className="text-sm text-slate-400 mb-4">
        Busca libros de dominio público (Project Gutenberg) y convierte capítulos en audio.
      </p>

      <form onSubmit={handleSearch} className="flex gap-2 mb-4">
        <input
          className="bg-slate-800 border border-slate-600 text-slate-100 placeholder-slate-500 rounded-lg p-2 flex-1 focus:outline-none focus:ring-2 focus:ring-purple-500"
          placeholder="Buscar libro (p. ej. Quijote, Poe, Austen…)"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        <button
          type="submit"
          disabled={searching}
          className="bg-purple-600 text-white px-4 py-2 rounded-lg hover:bg-purple-500 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {searching ? 'Buscando...' : 'Buscar'}
        </button>
      </form>

      {error && (
        <div className="bg-red-500/10 border border-red-500/40 text-red-300 p-3 rounded-lg mb-4">Error: {error}</div>
      )}

      {results.length > 0 && !selected && (
        <div className="grid gap-3 md:grid-cols-2 mb-4">
          {results.map((book) => (
            <button
              key={book.book_id}
              type="button"
              onClick={() => handleSelect(book)}
              className="bg-slate-800/50 border border-slate-700 p-4 rounded-xl shadow-lg shadow-black/20 text-left hover:border-purple-500/60 hover:bg-slate-800 transition-colors"
            >
              <strong className="block text-slate-100">{book.title}</strong>
              <span className="text-sm text-slate-400">{book.author}</span>
            </button>
          ))}
        </div>
      )}

      {selected && (
        <div className="bg-slate-800/50 border border-slate-700 p-6 rounded-xl shadow-lg shadow-black/20">
          <div className="flex justify-between items-start mb-4">
            <div>
              <h3 className="text-lg font-bold tracking-tight">{selected.title}</h3>
              <p className="text-sm text-slate-400">{selected.author}</p>
            </div>
            <button
              type="button"
              onClick={() => setSelected(null)}
              className="text-sm text-slate-400 hover:text-slate-200 transition-colors"
            >
              ← Volver a resultados
            </button>
          </div>

          <div className="mb-4">
            <label className="block text-sm font-medium text-slate-200 mb-1">Voz del audiolibro</label>
            <select
              className="bg-slate-800 border border-slate-600 text-slate-100 rounded-lg p-2 focus:outline-none focus:ring-2 focus:ring-purple-500"
              value={voiceId}
              onChange={(e) => setVoiceId(e.target.value)}
            >
              {voices.map((v) => (
                <option key={v.id} value={v.id}>
                  {v.name} ({v.engine})
                </option>
              ))}
            </select>
          </div>

          {loadingChapters && <p className="text-slate-400">Descargando y analizando el libro…</p>}

          {chapters.length > 0 && (
            <ul className="divide-y divide-slate-700/60">
              {chapters.map((ch) => (
                <li key={ch.index} className="py-2 flex justify-between items-center">
                  <div>
                    <span className="font-medium text-slate-100">{ch.title}</span>
                    <span className="text-sm text-slate-400 ml-2">
                      {ch.words.toLocaleString()} palabras
                    </span>
                  </div>
                  <button
                    type="button"
                    disabled={converting !== null}
                    onClick={() => handleConvert(ch)}
                    className="bg-green-600 text-white px-3 py-1 rounded-lg text-sm hover:bg-green-500 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {converting === ch.index ? 'Creando...' : 'Convertir a audio'}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  )
}
