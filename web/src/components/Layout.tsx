import { type ReactNode } from 'react'
import { Link } from '@tanstack/react-router'

interface LayoutProps {
  children: ReactNode
}

export default function Layout({ children }: LayoutProps) {
  return (
    <div className="flex h-screen">
      <aside className="w-64 bg-gray-900 text-white p-4">
        <h1 className="text-xl font-bold mb-6">Podcast Generator</h1>
        <nav className="space-y-2" aria-label="Navegación principal">
          <Link to="/" className="block p-2 rounded hover:bg-gray-800" activeProps={{ className: 'bg-gray-800' }}>Inicio</Link>
          <Link to="/voices" className="block p-2 rounded hover:bg-gray-800" activeProps={{ className: 'bg-gray-800' }}>Voces</Link>
          <Link to="/create" className="block p-2 rounded hover:bg-gray-800" activeProps={{ className: 'bg-gray-800' }}>Crear</Link>
          <Link to="/queue" className="block p-2 rounded hover:bg-gray-800" activeProps={{ className: 'bg-gray-800' }}>Cola</Link>
          <Link to="/channels" className="block p-2 rounded hover:bg-gray-800" activeProps={{ className: 'bg-gray-800' }}>Canales</Link>
          <Link to="/studio" className="block p-2 rounded hover:bg-gray-800" activeProps={{ className: 'bg-gray-800' }}>Studio</Link>
          <Link to="/books" className="block p-2 rounded hover:bg-gray-800" activeProps={{ className: 'bg-gray-800' }}>Libros</Link>
        </nav>
      </aside>
      <main className="flex-1 p-6 overflow-auto">{children}</main>
    </div>
  )
}
