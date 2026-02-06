'use client'

import { useState } from 'react'
import Image from 'next/image'
import Link from 'next/link'

export default function PessoasPage() {
  const [query, setQuery] = useState('')
  const [company, setCompany] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<any>(null)
  const [error, setError] = useState('')

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!query.trim()) return

    setLoading(true)
    setError('')
    setResult(null)

    try {
      const token = localStorage.getItem('token')
      const res = await fetch(`/api/v2/person/analyze`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ name: query, company: company || undefined })
      })

      const data = await res.json()

      if (!res.ok) {
        setError(data.detail || 'Erro ao analisar pessoa')
        return
      }

      setResult(data)
    } catch {
      setError('Erro ao conectar com o servidor')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-bg-dark">
      <header className="bg-bg-dark-secondary border-b border-white/5">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center gap-4">
              <Link href="/admin">
                <Image src="/images/iconsai-logo.png" alt="Iconsai" width={120} height={34} className="h-8 w-auto" />
              </Link>
              <span className="text-logo-gray/40">|</span>
              <h1 className="text-logo-gray font-semibold">Pessoas</h1>
            </div>
            <Link href="/admin" className="text-logo-gray/60 hover:text-logo-gray text-sm">Voltar</Link>
          </div>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 py-8">
        <form onSubmit={handleSearch} className="mb-8 space-y-4">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Nome da pessoa..."
            className="w-full px-4 py-3 bg-bg-dark-secondary border border-white/10 rounded-lg text-logo-gray placeholder-logo-gray/40 focus:outline-none focus:ring-2 focus:ring-cyan-500/50"
          />
          <div className="flex gap-4">
            <input
              type="text"
              value={company}
              onChange={(e) => setCompany(e.target.value)}
              placeholder="Empresa (opcional)..."
              className="flex-1 px-4 py-3 bg-bg-dark-secondary border border-white/10 rounded-lg text-logo-gray placeholder-logo-gray/40 focus:outline-none focus:ring-2 focus:ring-cyan-500/50"
            />
            <button
              type="submit"
              disabled={loading}
              className="px-6 py-3 bg-logo-orange hover:bg-logo-orange/90 disabled:bg-logo-orange/50 text-white font-semibold rounded-lg transition-colors"
            >
              {loading ? 'Analisando...' : 'Analisar'}
            </button>
          </div>
        </form>

        {error && (
          <div className="p-4 bg-red-500/10 border border-red-500/20 rounded-lg mb-6">
            <p className="text-red-400">{error}</p>
          </div>
        )}

        {loading && (
          <div className="flex flex-col items-center justify-center py-12">
            <div className="animate-spin h-8 w-8 border-2 border-cyan-500 border-t-transparent rounded-full mb-4" />
            <p className="text-logo-gray/60">Pesquisando perfil profissional...</p>
          </div>
        )}

        {result && (
          <div className="space-y-6">
            {result.profile && (
              <div className="p-6 bg-bg-dark-secondary rounded-lg border border-white/5">
                <h2 className="text-xl font-bold text-logo-gray mb-4">{result.profile.name || query}</h2>
                <p className="text-logo-gray/60">{result.profile.title || ''}</p>
                <p className="text-logo-gray/60">{result.profile.company || ''}</p>
              </div>
            )}

            {result.ai_analysis && (
              <div className="p-6 bg-bg-dark-secondary rounded-lg border border-white/5">
                <h3 className="text-lg font-semibold text-logo-gray mb-4">Analise</h3>
                <pre className="whitespace-pre-wrap text-logo-gray/80 text-sm">
                  {typeof result.ai_analysis === 'string' ? result.ai_analysis : JSON.stringify(result.ai_analysis, null, 2)}
                </pre>
              </div>
            )}

            <details className="p-4 bg-bg-dark-secondary rounded-lg border border-white/5">
              <summary className="text-logo-gray/60 text-sm cursor-pointer">Ver dados brutos</summary>
              <pre className="mt-4 text-xs text-logo-gray/60 overflow-auto max-h-96">{JSON.stringify(result, null, 2)}</pre>
            </details>
          </div>
        )}
      </main>
    </div>
  )
}
