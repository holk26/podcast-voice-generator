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
      <h2 className="text-2xl font-bold mb-4">Libros → Audiolibros</h2>
      <p className="text-sm text-gray-600 mb-4">
        Busca libros de dominio público (Project Gutenberg) y convierte capítulos en audio.
      </p>

      <form onSubmit={handleSearch} className="flex gap-2 mb-4">
        <input
          className="border rounded p-2 flex-1"
          placeholder="Buscar libro (p. ej. Quijote, Poe, Austen…)"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        <button
          type="submit"
          disabled={searching}
          className="bg-blue-600 text-white px-4 py-2 rounded disabled:opacity-50"
        >
          {searching ? 'Buscando...' : 'Buscar'}
        </button>
      </form>

      {error && (
        <div className="bg-red-100 text-red-800 p-3 rounded mb-4">Error: {error}</div>
      )}

      {results.length > 0 && !selected && (
        <div className="grid gap-3 md:grid-cols-2 mb-4">
          {results.map((book) => (
            <button
              key={book.book_id}
              type="button"
              onClick={() => handleSelect(book)}
              className="bg-white p-4 rounded shadow text-left hover:ring-2 hover:ring-blue-400"
            >
              <strong className="block">{book.title}</strong>
              <span className="text-sm text-gray-600">{book.author}</span>
            </button>
          ))}
        </div>
      )}

      {selected && (
        <div className="bg-white p-6 rounded shadow">
          <div className="flex justify-between items-start mb-4">
            <div>
              <h3 className="text-lg font-bold">{selected.title}</h3>
              <p className="text-sm text-gray-600">{selected.author}</p>
            </div>
            <button
              type="button"
              onClick={() => setSelected(null)}
              className="text-sm text-gray-500 hover:text-gray-700"
            >
              ← Volver a resultados
            </button>
          </div>

          <div className="mb-4">
            <label className="block text-sm font-medium mb-1">Voz del audiolibro</label>
            <select
              className="border rounded p-2"
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

          {loadingChapters && <p className="text-gray-500">Descargando y analizando el libro…</p>}

          {chapters.length > 0 && (
            <ul className="divide-y">
              {chapters.map((ch) => (
                <li key={ch.index} className="py-2 flex justify-between items-center">
                  <div>
                    <span className="font-medium">{ch.title}</span>
                    <span className="text-sm text-gray-500 ml-2">
                      {ch.words.toLocaleString()} palabras
                    </span>
                  </div>
                  <button
                    type="button"
                    disabled={converting !== null}
                    onClick={() => handleConvert(ch)}
                    className="bg-green-600 text-white px-3 py-1 rounded text-sm disabled:opacity-50"
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
