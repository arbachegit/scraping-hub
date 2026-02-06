'use client'

import { useState } from 'react'
import Image from 'next/image'
import Link from 'next/link'

export default function IndicadoresPage() {
  const [city, setCity] = useState('')
  const [state, setState] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<any>(null)
  const [error, setError] = useState('')

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!city.trim()) return

    setLoading(true)
    setError('')
    try {
      const token = localStorage.getItem('token')
      const res = await fetch(`/api/v2/indicators/municipality?city=${encodeURIComponent(city)}&state=${encodeURIComponent(state)}`, {
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
              <h1 className="text-logo-gray font-semibold">Indicadores Fiscais</h1>
            </div>
            <Link href="/admin" className="text-logo-gray/60 hover:text-logo-gray text-sm">Voltar</Link>
          </div>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 py-8">
        <form onSubmit={handleSearch} className="mb-8">
          <div className="flex gap-4">
            <input type="text" value={city} onChange={(e) => setCity(e.target.value)} placeholder="Cidade..." className="flex-1 px-4 py-3 bg-bg-dark-secondary border border-white/10 rounded-lg text-logo-gray placeholder-logo-gray/40 focus:outline-none focus:ring-2 focus:ring-cyan-500/50" />
            <input type="text" value={state} onChange={(e) => setState(e.target.value)} placeholder="UF" maxLength={2} className="w-20 px-4 py-3 bg-bg-dark-secondary border border-white/10 rounded-lg text-logo-gray placeholder-logo-gray/40 focus:outline-none focus:ring-2 focus:ring-cyan-500/50 uppercase" />
            <button type="submit" disabled={loading} className="px-6 py-3 bg-purple-500 hover:bg-purple-600 disabled:bg-purple-500/50 text-white font-semibold rounded-lg">{loading ? 'Buscando...' : 'Buscar'}</button>
          </div>
        </form>

        {error && <div className="p-4 bg-red-500/10 border border-red-500/20 rounded-lg mb-6"><p className="text-red-400">{error}</p></div>}
        {loading && <div className="flex justify-center py-12"><div className="animate-spin h-8 w-8 border-2 border-cyan-500 border-t-transparent rounded-full" /></div>}

        {result && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {result.pib && (
              <div className="p-6 bg-bg-dark-secondary rounded-lg border border-white/5">
                <h3 className="text-logo-gray font-semibold mb-4">PIB</h3>
                <p className="text-2xl text-cyan-400 font-bold">R$ {(result.pib.pib_total / 1e9).toFixed(2)} bi</p>
                <p className="text-logo-gray/60 text-sm">Per capita: R$ {result.pib.pib_per_capita?.toLocaleString()}</p>
              </div>
            )}
            {result.idhm && (
              <div className="p-6 bg-bg-dark-secondary rounded-lg border border-white/5">
                <h3 className="text-logo-gray font-semibold mb-4">IDHM</h3>
                <p className="text-2xl text-green-400 font-bold">{result.idhm.idhm_2010}</p>
                <p className="text-logo-gray/60 text-sm">{result.idhm.classificacao_2010}</p>
              </div>
            )}
            {result.populacao && (
              <div className="p-6 bg-bg-dark-secondary rounded-lg border border-white/5">
                <h3 className="text-logo-gray font-semibold mb-4">Populacao</h3>
                <p className="text-2xl text-logo-orange font-bold">{result.populacao.populacao?.toLocaleString()}</p>
                <p className="text-logo-gray/60 text-sm">habitantes</p>
              </div>
            )}
          </div>
        )}

        {result && !result.pib && !result.idhm && (
          <div className="p-6 bg-bg-dark-secondary rounded-lg border border-white/5">
            <pre className="text-logo-gray/60 text-sm">{JSON.stringify(result, null, 2)}</pre>
          </div>
        )}
      </main>
    </div>
  )
}
