'use client'

import { useState, useEffect } from 'react'
import Image from 'next/image'
import Link from 'next/link'

export default function ConfigPage() {
  const [health, setHealth] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch('/health')
      .then(res => res.json())
      .then(data => setHealth(data))
      .catch(() => setHealth({ error: 'Erro ao carregar' }))
      .finally(() => setLoading(false))
  }, [])

  return (
    <div className="min-h-screen bg-bg-dark">
      <header className="bg-bg-dark-secondary border-b border-white/5">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center gap-4">
              <Link href="/admin"><Image src="/images/iconsai-logo.png" alt="Iconsai" width={120} height={34} className="h-8 w-auto" /></Link>
              <span className="text-logo-gray/40">|</span>
              <h1 className="text-logo-gray font-semibold">Configuracoes</h1>
            </div>
            <Link href="/admin" className="text-logo-gray/60 hover:text-logo-gray text-sm">Voltar</Link>
          </div>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 py-8">
        <h2 className="text-xl font-bold text-logo-gray mb-6">Status do Sistema</h2>

        {loading && <div className="flex justify-center py-12"><div className="animate-spin h-8 w-8 border-2 border-cyan-500 border-t-transparent rounded-full" /></div>}

        {health && !health.error && (
          <div className="space-y-6">
            <div className="p-6 bg-bg-dark-secondary rounded-lg border border-white/5">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-logo-gray font-semibold">Status Geral</h3>
                <span className={`px-3 py-1 rounded-full text-sm ${health.status === 'healthy' ? 'bg-green-500/20 text-green-400' : 'bg-yellow-500/20 text-yellow-400'}`}>
                  {health.status}
                </span>
              </div>
              <p className="text-logo-gray/60">Versao: {health.version}</p>
              <p className="text-logo-gray/60">APIs configuradas: {health.apis_configured}</p>
            </div>

            <div className="p-6 bg-bg-dark-secondary rounded-lg border border-white/5">
              <h3 className="text-logo-gray font-semibold mb-4">APIs Externas</h3>
              <div className="grid grid-cols-2 gap-4">
                {health.apis && Object.entries(health.apis).map(([api, status]) => (
                  <div key={api} className="flex items-center justify-between p-3 bg-bg-dark rounded-lg">
                    <span className="text-logo-gray capitalize">{api}</span>
                    <span className={`w-3 h-3 rounded-full ${status ? 'bg-green-500' : 'bg-red-500'}`} />
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {health?.error && (
          <div className="p-4 bg-red-500/10 border border-red-500/20 rounded-lg">
            <p className="text-red-400">{health.error}</p>
          </div>
        )}
      </main>
    </div>
  )
}
