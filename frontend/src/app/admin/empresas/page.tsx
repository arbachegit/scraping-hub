'use client'

import { useState } from 'react'
import Image from 'next/image'
import Link from 'next/link'

export default function EmpresasPage() {
  const [query, setQuery] = useState('')
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
      const res = await fetch(`/api/v2/company/analyze`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ name: query })
      })

      const data = await res.json()

      if (!res.ok) {
        setError(data.detail || 'Erro ao analisar empresa')
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
      {/* Header */}
      <header className="bg-bg-dark-secondary border-b border-white/5">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center gap-4">
              <Link href="/admin">
                <Image
                  src="/images/iconsai-logo.png"
                  alt="Iconsai"
                  width={120}
                  height={34}
                  className="h-8 w-auto"
                />
              </Link>
              <span className="text-logo-gray/40">|</span>
              <h1 className="text-logo-gray font-semibold">Empresas</h1>
            </div>
            <Link href="/admin" className="text-logo-gray/60 hover:text-logo-gray text-sm">
              Voltar
            </Link>
          </div>
        </div>
      </header>

      {/* Main */}
      <main className="max-w-4xl mx-auto px-4 py-8">
        {/* Search Form */}
        <form onSubmit={handleSearch} className="mb-8">
          <div className="flex gap-4">
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Nome da empresa ou CNPJ..."
              className="flex-1 px-4 py-3 bg-bg-dark-secondary border border-white/10 rounded-lg text-logo-gray placeholder-logo-gray/40 focus:outline-none focus:ring-2 focus:ring-cyan-500/50 focus:border-cyan-500"
            />
            <button
              type="submit"
              disabled={loading}
              className="px-6 py-3 bg-logo-red hover:bg-logo-red/90 disabled:bg-logo-red/50 text-white font-semibold rounded-lg transition-colors"
            >
              {loading ? 'Analisando...' : 'Analisar'}
            </button>
          </div>
        </form>

        {/* Error */}
        {error && (
          <div className="p-4 bg-red-500/10 border border-red-500/20 rounded-lg mb-6">
            <p className="text-red-400">{error}</p>
          </div>
        )}

        {/* Loading */}
        {loading && (
          <div className="flex flex-col items-center justify-center py-12">
            <div className="animate-spin h-8 w-8 border-2 border-cyan-500 border-t-transparent rounded-full mb-4" />
            <p className="text-logo-gray/60">Coletando dados de multiplas fontes...</p>
          </div>
        )}

        {/* Result */}
        {result && (
          <div className="space-y-6">
            {/* Quality Score */}
            {result.data_quality && (
              <div className="p-4 bg-bg-dark-secondary rounded-lg border border-white/5">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-logo-gray/60 text-sm">Qualidade dos dados</span>
                  <span className="text-cyan-400 font-mono">{result.data_quality.completeness}</span>
                </div>
                {result.data_quality.sources_failed?.length > 0 && (
                  <p className="text-yellow-400/80 text-xs">
                    Fontes com falha: {result.data_quality.sources_failed.join(', ')}
                  </p>
                )}
              </div>
            )}

            {/* Company Profile */}
            {result.company_profile && (
              <div className="p-6 bg-bg-dark-secondary rounded-lg border border-white/5">
                <h2 className="text-xl font-bold text-logo-gray mb-4">
                  {result.company_profile.nome_fantasia || result.company_profile.razao_social || query}
                </h2>
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <span className="text-logo-gray/60">CNPJ:</span>
                    <span className="text-logo-gray ml-2">{result.company_profile.cnpj || 'N/A'}</span>
                  </div>
                  <div>
                    <span className="text-logo-gray/60">Situacao:</span>
                    <span className="text-logo-gray ml-2">{result.company_profile.situacao_cadastral || 'N/A'}</span>
                  </div>
                  <div>
                    <span className="text-logo-gray/60">Porte:</span>
                    <span className="text-logo-gray ml-2">{result.company_profile.porte || 'N/A'}</span>
                  </div>
                  <div>
                    <span className="text-logo-gray/60">Setor:</span>
                    <span className="text-logo-gray ml-2">{result.company_profile.cnae_principal?.descricao || 'N/A'}</span>
                  </div>
                </div>
              </div>
            )}

            {/* Analysis */}
            {result.complete_analysis && (
              <div className="p-6 bg-bg-dark-secondary rounded-lg border border-white/5">
                <h3 className="text-lg font-semibold text-logo-gray mb-4">Analise Completa</h3>
                <div className="prose prose-invert prose-sm max-w-none">
                  <pre className="whitespace-pre-wrap text-logo-gray/80 text-sm font-sans">
                    {typeof result.complete_analysis === 'string'
                      ? result.complete_analysis
                      : JSON.stringify(result.complete_analysis, null, 2)}
                  </pre>
                </div>
              </div>
            )}

            {/* Raw JSON (collapsible) */}
            <details className="p-4 bg-bg-dark-secondary rounded-lg border border-white/5">
              <summary className="text-logo-gray/60 text-sm cursor-pointer">Ver dados brutos (JSON)</summary>
              <pre className="mt-4 text-xs text-logo-gray/60 overflow-auto max-h-96">
                {JSON.stringify(result, null, 2)}
              </pre>
            </details>
          </div>
        )}
      </main>
    </div>
  )
}
