import { type ReactNode, useState, useEffect } from 'react'
import { Link, useLocation } from '@tanstack/react-router'
import { useAuthStore } from '../stores/authStore'
import Toast from './Toast'
import ConfirmDialog from './ConfirmDialog'

interface LayoutProps {
  children: ReactNode
}

type IconProps = { className?: string }

const HomeIcon = ({ className = 'w-5 h-5' }: IconProps) => (
  <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
    <path d="M3 12l9-9 9 9M5 10v10h14V10" />
  </svg>
)
const MicIcon = ({ className = 'w-5 h-5' }: IconProps) => (
  <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
    <rect x="9" y="2" width="6" height="12" rx="3" /><path d="M5 10a7 7 0 0 0 14 0M12 17v5" />
  </svg>
)
const PlusIcon = ({ className = 'w-5 h-5' }: IconProps) => (
  <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
    <path d="M12 5v14M5 12h14" />
  </svg>
)
const ListIcon = ({ className = 'w-5 h-5' }: IconProps) => (
  <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
    <path d="M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01" />
  </svg>
)
const BroadcastIcon = ({ className = 'w-5 h-5' }: IconProps) => (
  <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
    <circle cx="12" cy="12" r="2" /><path d="M7 7a7 7 0 0 0 0 10M17 7a7 7 0 0 1 0 10M4 4a12 12 0 0 0 0 16M20 4a12 12 0 0 1 0 16" />
  </svg>
)
const BookIcon = ({ className = 'w-5 h-5' }: IconProps) => (
  <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
    <path d="M4 4a2 2 0 0 1 2-2h12v18H6a2 2 0 0 1-2-2zM6 18h12" />
  </svg>
)

const NAV_ITEMS = [
  { to: '/', label: 'Inicio', Icon: HomeIcon },
  { to: '/voices', label: 'Voces', Icon: MicIcon },
  { to: '/create', label: 'Crear', Icon: PlusIcon },
  { to: '/queue', label: 'Cola', Icon: ListIcon },
  { to: '/channels', label: 'Canales', Icon: BroadcastIcon },
  { to: '/books', label: 'Libros', Icon: BookIcon },
] as const

export default function Layout({ children }: LayoutProps) {
  const username = useAuthStore((state) => state.username)
  const logout = useAuthStore((state) => state.logout)
  const [mobileOpen, setMobileOpen] = useState(false)
  const location = useLocation()

  useEffect(() => {
    setMobileOpen(false)
  }, [location.pathname])

  useEffect(() => {
    if (!mobileOpen) return
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && setMobileOpen(false)
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [mobileOpen])

  const sidebarContent = (
    <>
      <h1 className="text-xl font-bold tracking-tight mb-6 px-2 flex items-center gap-2">
        <span className="text-purple-400" aria-hidden="true">◆</span>
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
            <item.Icon className="w-5 h-5 shrink-0" />
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
          <svg className="w-5 h-5 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5-5-5M21 12H9" />
          </svg>
          Cerrar sesión
        </button>
      </div>
    </>
  )

  return (
    <div className="flex h-screen bg-slate-950">
      {/* Desktop sidebar */}
      <aside className="hidden md:flex w-64 shrink-0 bg-slate-950 border-r border-slate-800 text-slate-100 p-4 flex-col">
        {sidebarContent}
      </aside>

      {/* Mobile drawer */}
      {mobileOpen && (
        <div className="md:hidden fixed inset-0 z-40 flex">
          <div
            className="absolute inset-0 bg-black/60"
            onClick={() => setMobileOpen(false)}
            aria-hidden="true"
          />
          <aside className="relative w-64 bg-slate-950 border-r border-slate-800 text-slate-100 p-4 flex flex-col">
            {sidebarContent}
          </aside>
        </div>
      )}

      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Mobile top bar */}
        <header className="md:hidden flex items-center gap-3 px-4 py-3 bg-slate-950 border-b border-slate-800 text-slate-100">
          <button
            type="button"
            onClick={() => setMobileOpen(true)}
            className="p-1 rounded hover:bg-slate-800 transition-colors"
            aria-label="Abrir menú"
          >
            <svg className="w-6 h-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true">
              <path d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </button>
          <span className="text-lg font-bold">
            Podcast <span className="text-purple-400">Studio</span>
          </span>
        </header>

        <main className="flex-1 p-4 md:p-6 overflow-auto bg-slate-900 text-slate-100">
          {children}
        </main>
      </div>

      <Toast />
      <ConfirmDialog />
    </div>
  )
}
