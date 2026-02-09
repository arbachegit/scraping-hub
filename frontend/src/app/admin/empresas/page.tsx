'use client'

import { useState } from 'react'
import Image from 'next/image'
import Link from 'next/link'
import { AnalysisBlock, CompetitorStamp, SwotMatrix, SynthesisSection } from '@/components/analysis'

interface AnalysisResult {
  metadata: {
    company_name: string
    cnpj: string | null
    analysis_date: string
    data_quality_score: number
    sources_used: string[]
    processing_time_seconds?: number
  }
  blocks: Record<string, {
    title: string
    content: string
    highlights?: string[]
    confidence?: number
    error?: string
  }>
  synthesis: {
    hypothesis_objective?: {
      inferred: string
      evidence: string[]
    }
    suggested_okr?: {
      objectives: Array<{
        objective: string
        key_results: string[]
      }>
    }
    competitors?: Array<{
      name: string
      description: string
      stamp: 'Forte' | 'Medio' | 'Fraco'
      stamp_color: 'green' | 'yellow' | 'red'
      justification: string
    }>
    swot?: {
      strengths: Array<{ point: string; score: number; source_blocks: string[] }>
      weaknesses: Array<{ point: string; score: number; source_blocks: string[] }>
      opportunities: Array<{ point: string; score: number; source_blocks: string[] }>
      threats: Array<{ point: string; score: number; source_blocks: string[] }>
      tows_strategies: {
        so: string[]
        wo: string[]
        st: string[]
        wt: string[]
      }
      error?: string
    }
  }
  status: string
  error?: string
}

const BLOCK_ORDER = [
  { key: '1_empresa', number: 1 },
  { key: '2_pessoas', number: 2 },
  { key: '3_formacao', number: 3 },
  { key: '4_ativo_humano', number: 4 },
  { key: '5_capacidade', number: 5 },
  { key: '6_comunicacao', number: 6 },
  { key: '7_fraquezas', number: 7 },
  { key: '8_visao_leigo', number: 8 },
  { key: '9_visao_profissional', number: 9 },
  { key: '10_visao_concorrente', number: 10 },
  { key: '11_visao_fornecedor', number: 11 },
]

export default function EmpresasPage() {
  const [query, setQuery] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<AnalysisResult | null>(null)
  const [error, setError] = useState('')
  const [currentPhase, setCurrentPhase] = useState('')

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!query.trim()) return

    setLoading(true)
    setError('')
    setResult(null)
    setCurrentPhase('Iniciando analise...')

    try {
      const token = localStorage.getItem('token')

      // Simular fases de loading
      const phases = [
        'Coletando dados de multiplas fontes...',
        'Gerando blocos primarios...',
        'Analisando pessoas e formacao...',
        'Avaliando comunicacao...',
        'Gerando perspectivas...',
        'Finalizando sintese...'
      ]

      let phaseIndex = 0
      const phaseInterval = setInterval(() => {
        if (phaseIndex < phases.length) {
          setCurrentPhase(phases[phaseIndex])
          phaseIndex++
        }
      }, 8000)

      // Chamada direta ao backend (evita timeout do proxy Next.js)
      const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000'
      const res = await fetch(`${backendUrl}/api/v2/company/analyze-complete`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ name: query })
      })

      clearInterval(phaseInterval)

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
      setCurrentPhase('')
    }
  }

  return (
    <div className="min-h-screen bg-bg-dark">
      {/* Header */}
      <header className="bg-bg-dark-secondary border-b border-white/5 sticky top-0 z-50">
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
              <h1 className="text-logo-gray font-semibold">Analise de Empresas</h1>
              <span className="px-2 py-0.5 bg-cyan-500/20 text-cyan-400 text-xs rounded-full">11 Blocos</span>
            </div>
            <Link href="/admin" className="text-logo-gray/60 hover:text-logo-gray text-sm flex items-center gap-2">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
              </svg>
              Voltar
            </Link>
          </div>
        </div>
      </header>

      {/* Main */}
      <main className="max-w-5xl mx-auto px-4 py-8">
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
              className="px-6 py-3 bg-logo-red hover:bg-logo-red/90 disabled:bg-logo-red/50 text-white font-semibold rounded-lg transition-colors flex items-center gap-2"
            >
              {loading ? (
                <>
                  <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                  </svg>
                  Analisando...
                </>
              ) : (
                <>
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                  </svg>
                  Analisar
                </>
              )}
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
          <div className="space-y-6">
            <div className="flex flex-col items-center justify-center py-8">
              <div className="relative">
                <div className="animate-spin h-12 w-12 border-2 border-cyan-500 border-t-transparent rounded-full" />
                <div className="absolute inset-0 flex items-center justify-center">
                  <div className="h-6 w-6 bg-cyan-500/20 rounded-full animate-pulse" />
                </div>
              </div>
              <p className="text-logo-gray/60 mt-4">{currentPhase}</p>
            </div>

            {/* Skeleton blocks */}
            <div className="space-y-4">
              {BLOCK_ORDER.slice(0, 3).map(({ key, number }) => (
                <AnalysisBlock
                  key={key}
                  number={number}
                  title=""
                  content=""
                  isLoading={true}
                />
              ))}
            </div>
          </div>
        )}

        {/* Results */}
        {result && !loading && (
          <div className="space-y-6">
            {/* Metadata Bar */}
            <div className="flex items-center justify-between p-4 bg-bg-dark-secondary rounded-lg border border-white/5">
              <div className="flex items-center gap-4">
                <div>
                  <h2 className="text-xl font-bold text-logo-gray">
                    {result.metadata.company_name}
                  </h2>
                  {result.metadata.cnpj && (
                    <p className="text-sm text-logo-gray/50">CNPJ: {result.metadata.cnpj}</p>
                  )}
                </div>
              </div>
              <div className="flex items-center gap-4 text-sm">
                <div className="text-right">
                  <p className="text-logo-gray/50">Qualidade</p>
                  <p className="text-cyan-400 font-mono">
                    {Math.round(result.metadata.data_quality_score * 100)}%
                  </p>
                </div>
                {result.metadata.processing_time_seconds && (
                  <div className="text-right">
                    <p className="text-logo-gray/50">Tempo</p>
                    <p className="text-logo-gray font-mono">
                      {Math.round(result.metadata.processing_time_seconds)}s
                    </p>
                  </div>
                )}
                <div className="text-right">
                  <p className="text-logo-gray/50">Fontes</p>
                  <p className="text-logo-gray font-mono">
                    {result.metadata.sources_used?.length || 0}
                  </p>
                </div>
              </div>
            </div>

            {/* Sources */}
            {result.metadata.sources_used && result.metadata.sources_used.length > 0 && (
              <div className="flex flex-wrap gap-2">
                {result.metadata.sources_used.map((source, idx) => (
                  <span
                    key={idx}
                    className="px-2 py-1 bg-white/5 text-logo-gray/60 text-xs rounded"
                  >
                    {source}
                  </span>
                ))}
              </div>
            )}

            {/* 11 Analysis Blocks */}
            <div className="space-y-4">
              {BLOCK_ORDER.map(({ key, number }) => {
                const block = result.blocks[key]
                if (!block) return null
                return (
                  <AnalysisBlock
                    key={key}
                    number={number}
                    title={block.title}
                    content={block.content}
                    highlights={block.highlights}
                    confidence={block.confidence}
                  />
                )
              })}
            </div>

            {/* Synthesis Section */}
            <div className="border-t border-white/5 pt-6">
              <h2 className="text-xl font-bold text-logo-gray mb-6">Sintese Final</h2>

              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Hypothesis & OKRs */}
                <SynthesisSection
                  hypothesis={result.synthesis.hypothesis_objective}
                  okrs={result.synthesis.suggested_okr}
                />

                {/* Competitors */}
                <CompetitorStamp
                  competitors={result.synthesis.competitors || []}
                />
              </div>

              {/* SWOT Matrix */}
              <div className="mt-6">
                <SwotMatrix swot={result.synthesis.swot as any} />
              </div>
            </div>

            {/* Raw JSON (collapsible) */}
            <details className="p-4 bg-bg-dark-secondary rounded-lg border border-white/5 mt-8">
              <summary className="text-logo-gray/60 text-sm cursor-pointer hover:text-logo-gray transition-colors">
                Ver dados brutos (JSON)
              </summary>
              <pre className="mt-4 text-xs text-logo-gray/60 overflow-auto max-h-96 p-4 bg-bg-dark rounded">
                {JSON.stringify(result, null, 2)}
              </pre>
            </details>
          </div>
        )}

        {/* Empty State */}
        {!loading && !result && !error && (
          <div className="text-center py-16">
            <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-cyan-500/10 mb-4">
              <svg className="w-8 h-8 text-cyan-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
              </svg>
            </div>
            <h3 className="text-lg font-semibold text-logo-gray mb-2">Analise de Empresas</h3>
            <p className="text-logo-gray/60 max-w-md mx-auto">
              Digite o nome ou CNPJ de uma empresa para gerar uma analise completa com 11 blocos tematicos,
              incluindo perspectivas de leigo, profissional, concorrente e fornecedor.
            </p>
          </div>
        )}
      </main>
    </div>
  )
}
