'use client'

interface Competitor {
  name: string
  description: string
  stamp: 'Forte' | 'Medio' | 'Fraco'
  stamp_color: 'green' | 'yellow' | 'red'
  justification: string
}

interface CompetitorStampProps {
  competitors: Competitor[]
  isLoading?: boolean
}

function StampBadge({ stamp, color }: { stamp: string; color: string }) {
  const colorClasses = {
    green: 'bg-green-500/20 text-green-400 border-green-500/30',
    yellow: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
    red: 'bg-red-500/20 text-red-400 border-red-500/30'
  }

  const icons = {
    Forte: (
      <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
        <path fillRule="evenodd" d="M2.166 4.999A11.954 11.954 0 0010 1.944 11.954 11.954 0 0017.834 5c.11.65.166 1.32.166 2.001 0 5.225-3.34 9.67-8 11.317C5.34 16.67 2 12.225 2 7c0-.682.057-1.35.166-2.001zm11.541 3.708a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
      </svg>
    ),
    Medio: (
      <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z" clipRule="evenodd" />
      </svg>
    ),
    Fraco: (
      <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
        <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
      </svg>
    )
  }

  return (
    <span className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-medium border ${colorClasses[color as keyof typeof colorClasses]}`}>
      {icons[stamp as keyof typeof icons]}
      {stamp}
    </span>
  )
}

export function CompetitorStamp({ competitors, isLoading = false }: CompetitorStampProps) {
  if (isLoading) {
    return (
      <div className="bg-bg-dark-secondary rounded-lg border border-white/5 p-6">
        <h3 className="text-lg font-semibold text-logo-gray mb-4">Concorrentes</h3>
        <div className="space-y-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="p-4 bg-bg-dark rounded-lg animate-pulse">
              <div className="flex items-center justify-between mb-2">
                <div className="h-5 w-32 bg-white/5 rounded" />
                <div className="h-6 w-20 bg-white/5 rounded-full" />
              </div>
              <div className="h-4 w-full bg-white/5 rounded mt-3" />
              <div className="h-4 w-3/4 bg-white/5 rounded mt-2" />
            </div>
          ))}
        </div>
      </div>
    )
  }

  if (!competitors || competitors.length === 0) {
    return (
      <div className="bg-bg-dark-secondary rounded-lg border border-white/5 p-6">
        <h3 className="text-lg font-semibold text-logo-gray mb-4">Concorrentes</h3>
        <p className="text-logo-gray/60 text-sm">Nenhum concorrente identificado</p>
      </div>
    )
  }

  return (
    <div className="bg-bg-dark-secondary rounded-lg border border-white/5 p-6">
      <h3 className="text-lg font-semibold text-logo-gray mb-4">Concorrentes</h3>
      <div className="space-y-4">
        {competitors.map((competitor, idx) => (
          <div
            key={idx}
            className="p-4 bg-bg-dark rounded-lg border border-white/5 hover:border-white/10 transition-colors"
          >
            <div className="flex items-start justify-between gap-4 mb-3">
              <h4 className="font-semibold text-logo-gray">{competitor.name}</h4>
              <StampBadge stamp={competitor.stamp} color={competitor.stamp_color} />
            </div>
            <p className="text-logo-gray/70 text-sm mb-3">{competitor.description}</p>
            <div className="pt-3 border-t border-white/5">
              <p className="text-logo-gray/50 text-xs">
                <span className="font-medium text-logo-gray/60">Justificativa:</span>{' '}
                {competitor.justification}
              </p>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
