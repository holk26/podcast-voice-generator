import { FormEvent, useState } from 'react'
import { useAuthStore } from '../stores/authStore'

export default function LoginForm() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const { login, isLoading, error, clearError } = useAuthStore()

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    clearError()
    if (!username.trim() || !password.trim()) return
    try {
      await login(username.trim(), password)
    } catch {
      // el error ya queda en el store
    }
  }

  return (
    <div className="min-h-screen w-full flex items-center justify-center bg-slate-950 p-4">
      <div className="w-full max-w-sm bg-slate-900/80 border border-slate-800 rounded-2xl shadow-2xl shadow-black/40 p-8">
        <div className="flex items-center justify-center gap-3 mb-8">
          <span className="text-3xl" aria-hidden="true">🎙️</span>
          <div>
            <h1 className="text-xl font-bold tracking-tight text-slate-100">
              Podcast <span className="text-purple-400">Studio</span>
            </h1>
            <p className="text-xs text-slate-500">Acceso privado</p>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="space-y-5">
          <div>
            <label htmlFor="username" className="block text-sm font-medium text-slate-300 mb-1.5">
              Usuario
            </label>
            <input
              id="username"
              type="text"
              autoComplete="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              disabled={isLoading}
              className="w-full rounded-lg bg-slate-950 border border-slate-700 px-3.5 py-2.5 text-sm text-slate-100 placeholder:text-slate-600 focus:border-purple-500 focus:ring-1 focus:ring-purple-500 focus:outline-none transition-colors disabled:opacity-60"
              placeholder="admin"
            />
          </div>

          <div>
            <label htmlFor="password" className="block text-sm font-medium text-slate-300 mb-1.5">
              Contraseña
            </label>
            <input
              id="password"
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              disabled={isLoading}
              className="w-full rounded-lg bg-slate-950 border border-slate-700 px-3.5 py-2.5 text-sm text-slate-100 placeholder:text-slate-600 focus:border-purple-500 focus:ring-1 focus:ring-purple-500 focus:outline-none transition-colors disabled:opacity-60"
              placeholder="••••••••"
            />
          </div>

          {error && (
            <div className="bg-red-500/10 border border-red-500/30 text-red-300 text-sm px-3.5 py-2.5 rounded-lg">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={isLoading || !username.trim() || !password.trim()}
            className="w-full rounded-lg bg-purple-600 text-white text-sm font-semibold px-4 py-2.5 hover:bg-purple-500 focus:outline-none focus:ring-2 focus:ring-purple-500 focus:ring-offset-2 focus:ring-offset-slate-900 transition-colors disabled:opacity-60 disabled:cursor-not-allowed"
          >
            {isLoading ? 'Entrando…' : 'Entrar al estudio'}
          </button>
        </form>
      </div>
    </div>
  )
}
