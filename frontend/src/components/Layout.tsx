import { type ReactNode } from 'react'
import { Link } from '@tanstack/react-router'
import { useAuthStore } from '../stores/authStore'

interface LayoutProps {
  children: ReactNode
}

const NAV_ITEMS = [
  { to: '/', label: 'Inicio', icon: '🏠' },
  { to: '/voices', label: 'Voces', icon: '🎤' },
  { to: '/create', label: 'Crear', icon: '➕' },
  { to: '/queue', label: 'Cola', icon: '📋' },
  { to: '/channels', label: 'Canales', icon: '📡' },
  { to: '/studio', label: 'Studio', icon: '🎬' },
  { to: '/books', label: 'Libros', icon: '📚' },
] as const

export default function Layout({ children }: LayoutProps) {
  const username = useAuthStore((state) => state.username)
  const logout = useAuthStore((state) => state.logout)

  return (
    <div className="flex h-screen bg-slate-950">
      <aside className="w-64 shrink-0 bg-slate-950 border-r border-slate-800 text-slate-100 p-4 flex flex-col">
        <h1 className="text-xl font-bold tracking-tight mb-6 px-2 flex items-center gap-2">
          <span aria-hidden="true">🎙️</span>
          <span>
            Podcast <span className="text-purple-400">Studio</span>
          </span>
        </h1>
        <nav className="space-y-1 flex-1" aria-label="Navegación principal">
          {NAV_ITEMS.map((item) => (
            <Link
              key={item.to}
              to={item.to}
              className="flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium text-slate-300 border-l-2 border-transparent hover:bg-slate-800/70 hover:text-slate-100 transition-colors"
              activeProps={{
                className:
                  'bg-purple-600/20 border-l-purple-500 text-purple-200 hover:bg-purple-600/20 hover:text-purple-200',
              }}
              activeOptions={{ exact: item.to === '/' }}
            >
              <span aria-hidden="true">{item.icon}</span>
              {item.label}
            </Link>
          ))}
        </nav>

        <div className="pt-4 border-t border-slate-800">
          <div className="px-3 mb-2 text-xs text-slate-500 truncate" title={username || undefined}>
            {username || 'Usuario'}
          </div>
          <button
            onClick={logout}
            className="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium text-slate-400 hover:bg-slate-800/70 hover:text-slate-100 transition-colors text-left"
          >
            <span aria-hidden="true">🚪</span>
            Cerrar sesión
          </button>
        </div>
      </aside>
      <main className="flex-1 p-6 overflow-auto bg-slate-900 text-slate-100">{children}</main>
    </div>
  )
}
