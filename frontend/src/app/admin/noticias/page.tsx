'use client'

import { useState } from 'react'
import Image from 'next/image'
import Link from 'next/link'

export default function NoticiasPage() {
  const [query, setQuery] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<any>(null)
  const [error, setError] = useState('')

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!query.trim()) return

    setLoading(true)
    setError('')
    try {
      const token = localStorage.getItem('token')
      const res = await fetch(`/api/v2/news/search?query=${encodeURIComponent(query)}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      })
      const data = await res.json()
      if (!res.ok) { setError(data.detail || 'Erro'); return }
      setResult(data)
    } catch { setError('Erro ao conectar') }
    finally { setLoading(false) }
  }

  return (
    <div className="min-h-screen bg-bg-dark">
      <header className="bg-bg-dark-secondary border-b border-white/5">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center gap-4">
              <Link href="/admin"><Image src="/images/iconsai-logo.png" alt="Iconsai" width={120} height={34} className="h-8 w-auto" /></Link>
              <span className="text-logo-gray/40">|</span>
              <h1 className="text-logo-gray font-semibold">Noticias</h1>
            </div>
            <Link href="/admin" className="text-logo-gray/60 hover:text-logo-gray text-sm">Voltar</Link>
          </div>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 py-8">
        <form onSubmit={handleSearch} className="mb-8">
          <div className="flex gap-4">
            <input type="text" value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Buscar noticias..." className="flex-1 px-4 py-3 bg-bg-dark-secondary border border-white/10 rounded-lg text-logo-gray placeholder-logo-gray/40 focus:outline-none focus:ring-2 focus:ring-cyan-500/50" />
            <button type="submit" disabled={loading} className="px-6 py-3 bg-green-500 hover:bg-green-600 disabled:bg-green-500/50 text-white font-semibold rounded-lg">{loading ? 'Buscando...' : 'Buscar'}</button>
          </div>
        </form>

        {error && <div className="p-4 bg-red-500/10 border border-red-500/20 rounded-lg mb-6"><p className="text-red-400">{error}</p></div>}
        {loading && <div className="flex justify-center py-12"><div className="animate-spin h-8 w-8 border-2 border-cyan-500 border-t-transparent rounded-full" /></div>}

        {result?.results && (
          <div className="space-y-4">
            {result.results.map((news: any, i: number) => (
              <a key={i} href={news.url} target="_blank" rel="noopener noreferrer" className="block p-4 bg-bg-dark-secondary rounded-lg border border-white/5 hover:border-cyan-400 transition-colors">
                <h3 className="text-logo-gray font-medium mb-2">{news.title}</h3>
                <p className="text-logo-gray/60 text-sm">{news.snippet || news.content?.slice(0, 200)}</p>
                <p className="text-logo-gray/40 text-xs mt-2">{news.source} - {news.date}</p>
              </a>
            ))}
          </div>
        )}
      </main>
    </div>
  )
}
