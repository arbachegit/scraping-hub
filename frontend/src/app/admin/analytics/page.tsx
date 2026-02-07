'use client'

import Image from 'next/image'
import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'

interface DailyMetrics {
  period_days: number
  start_date: string
  end_date: string
  total_searches: number
  total_api_calls: number
  total_company_analyses: number
  total_person_analyses: number
}

interface SearchTypeDistribution {
  search_type: string
  count: number
}

interface HourlyActivity {
  hour: number
  count: number
}

interface SourceQuality {
  source_name: string
  source_type: string
  total_calls: number
  success_rate: number
  avg_response_time_ms: number
  total_cost: number
  cache_hit_rate: number
}

interface DashboardData {
  metrics: DailyMetrics
  search_distribution: SearchTypeDistribution[]
  hourly_activity: HourlyActivity[]
  source_quality: SourceQuality[]
}

export default function AnalyticsPage() {
  const router = useRouter()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [data, setData] = useState<DashboardData | null>(null)
  const [days, setDays] = useState(30)

  useEffect(() => {
    const token = localStorage.getItem('token')
    if (!token) {
      router.push('/')
      return
    }

    fetchDashboard(token, days)
  }, [router, days])

  const fetchDashboard = async (token: string, periodDays: number) => {
    setLoading(true)
    setError(null)

    try {
      const res = await fetch(`/api/v2/analytics/dashboard?days=${periodDays}`, {
        headers: { Authorization: `Bearer ${token}` },
      })

      if (!res.ok) {
        if (res.status === 401) {
          localStorage.removeItem('token')
          router.push('/')
          return
        }
        throw new Error('Erro ao carregar dados')
      }

      const dashboardData = await res.json()
      setData(dashboardData)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erro desconhecido')
    } finally {
      setLoading(false)
    }
  }

  const handleLogout = () => {
    localStorage.removeItem('token')
    router.push('/')
  }

  const formatNumber = (num: number): string => {
    return new Intl.NumberFormat('pt-BR').format(num)
  }

  const formatPercentage = (num: number): string => {
    return `${num.toFixed(1)}%`
  }

  const getSearchTypeLabel = (type: string): string => {
    const labels: Record<string, string> = {
      company: 'Empresas',
      person: 'Pessoas',
      politician: 'Politicos',
      news: 'Noticias',
      indicator: 'Indicadores',
    }
    return labels[type] || type
  }

  const getSourceTypeColor = (type: string): string => {
    const colors: Record<string, string> = {
      search: 'text-blue-400',
      social: 'text-purple-400',
      fiscal: 'text-green-400',
      news: 'text-yellow-400',
      ai: 'text-logo-red',
    }
    return colors[type] || 'text-logo-gray'
  }

  const getMaxActivity = (): number => {
    if (!data?.hourly_activity) return 1
    return Math.max(...data.hourly_activity.map(h => h.count), 1)
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-bg-dark flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin h-8 w-8 border-2 border-logo-red border-t-transparent rounded-full mx-auto mb-4" />
          <p className="text-logo-gray/60">Carregando analytics...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-bg-dark">
      {/* Header */}
      <header className="bg-bg-dark-secondary border-b border-white/5">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center gap-3">
              <a href="/admin">
                <Image
                  src="/images/iconsai-logo.png"
                  alt="Iconsai"
                  width={160}
                  height={45}
                  className="h-10 w-auto"
                />
              </a>
              <span className="text-logo-gray/40 px-2">/</span>
              <h1 className="text-logo-gray font-medium">Analytics</h1>
            </div>

            <div className="flex items-center gap-4">
              <a
                href="/admin"
                className="px-4 py-2 text-sm text-logo-gray/70 hover:text-logo-gray transition-colors"
              >
                Voltar
              </a>
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
        {/* Period Selector */}
        <div className="flex items-center justify-between mb-8">
          <h2 className="text-2xl font-bold text-logo-gray">Dashboard de Analytics</h2>
          <div className="flex items-center gap-2">
            <span className="text-logo-gray/60 text-sm">Periodo:</span>
            <select
              value={days}
              onChange={(e) => setDays(Number(e.target.value))}
              className="bg-bg-dark-secondary border border-white/10 rounded-lg px-3 py-2 text-logo-gray text-sm focus:outline-none focus:border-logo-red"
            >
              <option value={7}>7 dias</option>
              <option value={30}>30 dias</option>
              <option value={90}>90 dias</option>
              <option value={365}>1 ano</option>
            </select>
          </div>
        </div>

        {error && (
          <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-4 mb-6">
            <p className="text-red-400">{error}</p>
          </div>
        )}

        {/* Metrics Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <div className="bg-bg-dark-secondary rounded-xl p-6 border border-white/5">
            <div className="flex items-center gap-3 mb-4">
              <div className="p-2 bg-logo-red/10 rounded-lg">
                <svg className="w-5 h-5 text-logo-red" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
              </div>
              <span className="text-logo-gray/60 text-sm">Pesquisas</span>
            </div>
            <p className="text-3xl font-bold text-logo-gray">
              {formatNumber(data?.metrics.total_searches || 0)}
            </p>
          </div>

          <div className="bg-bg-dark-secondary rounded-xl p-6 border border-white/5">
            <div className="flex items-center gap-3 mb-4">
              <div className="p-2 bg-blue-500/10 rounded-lg">
                <svg className="w-5 h-5 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
                </svg>
              </div>
              <span className="text-logo-gray/60 text-sm">Analises de Empresas</span>
            </div>
            <p className="text-3xl font-bold text-logo-gray">
              {formatNumber(data?.metrics.total_company_analyses || 0)}
            </p>
          </div>

          <div className="bg-bg-dark-secondary rounded-xl p-6 border border-white/5">
            <div className="flex items-center gap-3 mb-4">
              <div className="p-2 bg-purple-500/10 rounded-lg">
                <svg className="w-5 h-5 text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z" />
                </svg>
              </div>
              <span className="text-logo-gray/60 text-sm">Analises de Pessoas</span>
            </div>
            <p className="text-3xl font-bold text-logo-gray">
              {formatNumber(data?.metrics.total_person_analyses || 0)}
            </p>
          </div>

          <div className="bg-bg-dark-secondary rounded-xl p-6 border border-white/5">
            <div className="flex items-center gap-3 mb-4">
              <div className="p-2 bg-green-500/10 rounded-lg">
                <svg className="w-5 h-5 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 12h14M5 12a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v4a2 2 0 01-2 2M5 12a2 2 0 00-2 2v4a2 2 0 002 2h14a2 2 0 002-2v-4a2 2 0 00-2-2m-2-4h.01M17 16h.01" />
                </svg>
              </div>
              <span className="text-logo-gray/60 text-sm">Chamadas de API</span>
            </div>
            <p className="text-3xl font-bold text-logo-gray">
              {formatNumber(data?.metrics.total_api_calls || 0)}
            </p>
          </div>
        </div>

        {/* Charts Row */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
          {/* Search Distribution */}
          <div className="bg-bg-dark-secondary rounded-xl p-6 border border-white/5">
            <h3 className="text-lg font-semibold text-logo-gray mb-6">Distribuicao de Pesquisas</h3>
            {data?.search_distribution && data.search_distribution.length > 0 ? (
              <div className="space-y-4">
                {data.search_distribution.map((item) => {
                  const total = data.search_distribution.reduce((acc, i) => acc + i.count, 0)
                  const percentage = total > 0 ? (item.count / total) * 100 : 0
                  return (
                    <div key={item.search_type}>
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-logo-gray/80 text-sm">{getSearchTypeLabel(item.search_type)}</span>
                        <span className="text-logo-gray text-sm font-medium">
                          {formatNumber(item.count)} ({formatPercentage(percentage)})
                        </span>
                      </div>
                      <div className="h-2 bg-white/5 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-gradient-to-r from-logo-red to-logo-orange rounded-full transition-all duration-500"
                          style={{ width: `${percentage}%` }}
                        />
                      </div>
                    </div>
                  )
                })}
              </div>
            ) : (
              <p className="text-logo-gray/40 text-center py-8">Nenhum dado disponivel</p>
            )}
          </div>

          {/* Hourly Activity */}
          <div className="bg-bg-dark-secondary rounded-xl p-6 border border-white/5">
            <h3 className="text-lg font-semibold text-logo-gray mb-6">Atividade por Hora</h3>
            {data?.hourly_activity && data.hourly_activity.length > 0 ? (
              <div className="flex items-end justify-between h-40 gap-1">
                {data.hourly_activity.map((item) => {
                  const maxActivity = getMaxActivity()
                  const height = maxActivity > 0 ? (item.count / maxActivity) * 100 : 0
                  return (
                    <div
                      key={item.hour}
                      className="flex-1 flex flex-col items-center gap-1"
                      title={`${item.hour}:00 - ${formatNumber(item.count)} acessos`}
                    >
                      <div className="w-full flex-1 flex items-end">
                        <div
                          className="w-full bg-gradient-to-t from-cyan-500 to-cyan-400 rounded-t transition-all duration-300 hover:from-cyan-400 hover:to-cyan-300"
                          style={{ height: `${Math.max(height, 2)}%` }}
                        />
                      </div>
                      {item.hour % 4 === 0 && (
                        <span className="text-logo-gray/40 text-xs">{item.hour}h</span>
                      )}
                    </div>
                  )
                })}
              </div>
            ) : (
              <p className="text-logo-gray/40 text-center py-8">Nenhum dado disponivel</p>
            )}
          </div>
        </div>

        {/* Source Quality Table */}
        <div className="bg-bg-dark-secondary rounded-xl border border-white/5 overflow-hidden">
          <div className="p-6 border-b border-white/5">
            <h3 className="text-lg font-semibold text-logo-gray">Qualidade das Fontes de Dados</h3>
          </div>
          {data?.source_quality && data.source_quality.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-white/5">
                    <th className="px-6 py-4 text-left text-xs font-medium text-logo-gray/60 uppercase tracking-wider">
                      Fonte
                    </th>
                    <th className="px-6 py-4 text-left text-xs font-medium text-logo-gray/60 uppercase tracking-wider">
                      Tipo
                    </th>
                    <th className="px-6 py-4 text-right text-xs font-medium text-logo-gray/60 uppercase tracking-wider">
                      Chamadas
                    </th>
                    <th className="px-6 py-4 text-right text-xs font-medium text-logo-gray/60 uppercase tracking-wider">
                      Taxa de Sucesso
                    </th>
                    <th className="px-6 py-4 text-right text-xs font-medium text-logo-gray/60 uppercase tracking-wider">
                      Tempo Medio
                    </th>
                    <th className="px-6 py-4 text-right text-xs font-medium text-logo-gray/60 uppercase tracking-wider">
                      Cache Hit
                    </th>
                    <th className="px-6 py-4 text-right text-xs font-medium text-logo-gray/60 uppercase tracking-wider">
                      Custo Total
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5">
                  {data.source_quality.map((source) => (
                    <tr key={source.source_name} className="hover:bg-white/5 transition-colors">
                      <td className="px-6 py-4 text-sm text-logo-gray font-medium">
                        {source.source_name}
                      </td>
                      <td className="px-6 py-4 text-sm">
                        <span className={getSourceTypeColor(source.source_type)}>
                          {source.source_type}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-sm text-logo-gray/80 text-right">
                        {formatNumber(source.total_calls)}
                      </td>
                      <td className="px-6 py-4 text-right">
                        <span className={`text-sm font-medium ${source.success_rate >= 95 ? 'text-green-400' : source.success_rate >= 80 ? 'text-yellow-400' : 'text-red-400'}`}>
                          {formatPercentage(source.success_rate)}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-sm text-logo-gray/80 text-right">
                        {source.avg_response_time_ms.toFixed(0)}ms
                      </td>
                      <td className="px-6 py-4 text-sm text-logo-gray/80 text-right">
                        {formatPercentage(source.cache_hit_rate)}
                      </td>
                      <td className="px-6 py-4 text-sm text-logo-gray/80 text-right">
                        R$ {source.total_cost.toFixed(2)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="p-8 text-center">
              <p className="text-logo-gray/40">Nenhum dado de fontes disponivel</p>
            </div>
          )}
        </div>
      </main>
    </div>
  )
}
