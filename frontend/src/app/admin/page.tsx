'use client'

import Image from 'next/image'
import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'

interface User {
  email: string
  name?: string
}

export default function AdminPage() {
  const router = useRouter()
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const token = localStorage.getItem('token')
    if (!token) {
      router.push('/')
      return
    }

    // Verificar token e obter usuario
    fetch('/api/auth/me', {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((res) => {
        if (!res.ok) throw new Error('Unauthorized')
        return res.json()
      })
      .then((data) => {
        setUser(data)
        setLoading(false)
      })
      .catch(() => {
        localStorage.removeItem('token')
        router.push('/')
      })
  }, [router])

  const handleLogout = () => {
    localStorage.removeItem('token')
    router.push('/')
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-bg-dark flex items-center justify-center">
        <div className="animate-spin h-8 w-8 border-2 border-logo-red border-t-transparent rounded-full" />
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-bg-dark">
      {/* Header */}
      <header className="bg-bg-dark-secondary border-b border-white/5">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            {/* Logo */}
            <div className="flex items-center gap-3">
              <Image
                src="/images/iconsai-logo.png"
                alt="Iconsai"
                width={160}
                height={45}
                className="h-10 w-auto"
              />
            </div>

            {/* User Menu */}
            <div className="flex items-center gap-4">
              <span className="text-logo-gray/70 text-sm">
                {user?.email}
              </span>
              <button
                onClick={handleLogout}
                className="px-4 py-2 text-sm text-logo-gray/70 hover:text-logo-red transition-colors"
              >
                Sair
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <h1 className="text-2xl font-bold text-logo-gray mb-8">
          Painel Administrativo
        </h1>

        {/* Cards Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {/* Card: Empresas */}
          <div className="bg-bg-dark-secondary rounded-xl p-6 border border-white/5 hover:border-logo-red/30 transition-colors">
            <div className="flex items-center gap-4 mb-4">
              <div className="p-3 bg-logo-red/10 rounded-lg">
                <svg className="w-6 h-6 text-logo-red" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
                </svg>
              </div>
              <h2 className="text-lg font-semibold text-logo-gray">Empresas</h2>
            </div>
            <p className="text-logo-gray/60 text-sm mb-4">
              Analise empresas, gere relatorios SWOT e inteligencia competitiva.
            </p>
            <a href="/admin/empresas" className="text-logo-red text-sm font-medium hover:underline">
              Acessar →
            </a>
          </div>

          {/* Card: Pessoas */}
          <div className="bg-bg-dark-secondary rounded-xl p-6 border border-white/5 hover:border-logo-red/30 transition-colors">
            <div className="flex items-center gap-4 mb-4">
              <div className="p-3 bg-logo-orange/10 rounded-lg">
                <svg className="w-6 h-6 text-logo-orange" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
                </svg>
              </div>
              <h2 className="text-lg font-semibold text-logo-gray">Pessoas</h2>
            </div>
            <p className="text-logo-gray/60 text-sm mb-4">
              Pesquise perfis profissionais e analise talentos do mercado.
            </p>
            <a href="/admin/pessoas" className="text-logo-orange text-sm font-medium hover:underline">
              Acessar →
            </a>
          </div>

          {/* Card: Politicos */}
          <div className="bg-bg-dark-secondary rounded-xl p-6 border border-white/5 hover:border-logo-red/30 transition-colors">
            <div className="flex items-center gap-4 mb-4">
              <div className="p-3 bg-blue-500/10 rounded-lg">
                <svg className="w-6 h-6 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 21v-4m0 0V5a2 2 0 012-2h6.5l1 1H21l-3 6 3 6h-8.5l-1-1H5a2 2 0 00-2 2zm9-13.5V9" />
                </svg>
              </div>
              <h2 className="text-lg font-semibold text-logo-gray">Politicos</h2>
            </div>
            <p className="text-logo-gray/60 text-sm mb-4">
              Pesquise perfis de politicos e figuras publicas brasileiras.
            </p>
            <a href="/admin/politicos" className="text-blue-400 text-sm font-medium hover:underline">
              Acessar →
            </a>
          </div>

          {/* Card: Noticias */}
          <div className="bg-bg-dark-secondary rounded-xl p-6 border border-white/5 hover:border-logo-red/30 transition-colors">
            <div className="flex items-center gap-4 mb-4">
              <div className="p-3 bg-green-500/10 rounded-lg">
                <svg className="w-6 h-6 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 20H5a2 2 0 01-2-2V6a2 2 0 012-2h10a2 2 0 012 2v1m2 13a2 2 0 01-2-2V7m2 13a2 2 0 002-2V9a2 2 0 00-2-2h-2m-4-3H9M7 16h6M7 8h6v4H7V8z" />
                </svg>
              </div>
              <h2 className="text-lg font-semibold text-logo-gray">Noticias</h2>
            </div>
            <p className="text-logo-gray/60 text-sm mb-4">
              Monitore noticias e tendencias do mercado brasileiro.
            </p>
            <a href="/admin/noticias" className="text-green-400 text-sm font-medium hover:underline">
              Acessar →
            </a>
          </div>

          {/* Card: Indicadores */}
          <div className="bg-bg-dark-secondary rounded-xl p-6 border border-white/5 hover:border-logo-red/30 transition-colors">
            <div className="flex items-center gap-4 mb-4">
              <div className="p-3 bg-purple-500/10 rounded-lg">
                <svg className="w-6 h-6 text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                </svg>
              </div>
              <h2 className="text-lg font-semibold text-logo-gray">Indicadores</h2>
            </div>
            <p className="text-logo-gray/60 text-sm mb-4">
              Acompanhe indicadores fiscais e economicos regionais.
            </p>
            <a href="/admin/indicadores" className="text-purple-400 text-sm font-medium hover:underline">
              Acessar →
            </a>
          </div>

          {/* Card: Configuracoes */}
          <div className="bg-bg-dark-secondary rounded-xl p-6 border border-white/5 hover:border-logo-red/30 transition-colors">
            <div className="flex items-center gap-4 mb-4">
              <div className="p-3 bg-logo-gray/10 rounded-lg">
                <svg className="w-6 h-6 text-logo-gray" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                </svg>
              </div>
              <h2 className="text-lg font-semibold text-logo-gray">Configuracoes</h2>
            </div>
            <p className="text-logo-gray/60 text-sm mb-4">
              Gerencie usuarios, APIs e configuracoes do sistema.
            </p>
            <a href="/admin/config" className="text-logo-gray text-sm font-medium hover:underline">
              Acessar →
            </a>
          </div>
        </div>
      </main>
    </div>
  )
}
