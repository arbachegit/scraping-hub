'use client'

import { useState } from 'react'

interface SwotItem {
  point: string
  score: number
  source_blocks: string[]
}

interface TowsStrategies {
  so: string[]
  wo: string[]
  st: string[]
  wt: string[]
}

interface SwotData {
  strengths: SwotItem[]
  weaknesses: SwotItem[]
  opportunities: SwotItem[]
  threats: SwotItem[]
  tows_strategies: TowsStrategies
  error?: string
}

interface SwotMatrixProps {
  swot: SwotData
  isLoading?: boolean
}

function ScoreBadge({ score }: { score: number }) {
  const getColor = () => {
    if (score >= 4) return 'bg-green-500/20 text-green-400'
    if (score >= 3) return 'bg-yellow-500/20 text-yellow-400'
    return 'bg-red-500/20 text-red-400'
  }

  return (
    <span className={`px-2 py-0.5 rounded text-xs font-mono ${getColor()}`}>
      {score}/5
    </span>
  )
}

function SwotQuadrant({
  title,
  items,
  color,
  icon
}: {
  title: string
  items: SwotItem[]
  color: string
  icon: React.ReactNode
}) {
  const colorClasses: Record<string, { bg: string; border: string; text: string; iconBg: string }> = {
    green: {
      bg: 'bg-green-500/5',
      border: 'border-green-500/20',
      text: 'text-green-400',
      iconBg: 'bg-green-500/20'
    },
    red: {
      bg: 'bg-red-500/5',
      border: 'border-red-500/20',
      text: 'text-red-400',
      iconBg: 'bg-red-500/20'
    },
    blue: {
      bg: 'bg-blue-500/5',
      border: 'border-blue-500/20',
      text: 'text-blue-400',
      iconBg: 'bg-blue-500/20'
    },
    orange: {
      bg: 'bg-orange-500/5',
      border: 'border-orange-500/20',
      text: 'text-orange-400',
      iconBg: 'bg-orange-500/20'
    }
  }

  const classes = colorClasses[color]

  return (
    <div className={`p-4 rounded-lg border ${classes.bg} ${classes.border}`}>
      <div className="flex items-center gap-2 mb-3">
        <div className={`w-8 h-8 rounded-lg ${classes.iconBg} flex items-center justify-center ${classes.text}`}>
          {icon}
        </div>
        <h4 className={`font-semibold ${classes.text}`}>{title}</h4>
      </div>
      <ul className="space-y-2">
        {items.map((item, idx) => (
          <li key={idx} className="flex items-start gap-2">
            <ScoreBadge score={item.score} />
            <span className="text-logo-gray/80 text-sm flex-1">{item.point}</span>
          </li>
        ))}
        {items.length === 0 && (
          <li className="text-logo-gray/40 text-sm italic">Nenhum item identificado</li>
        )}
      </ul>
    </div>
  )
}

export function SwotMatrix({ swot, isLoading = false }: SwotMatrixProps) {
  const [showTows, setShowTows] = useState(false)

  if (isLoading) {
    return (
      <div className="bg-bg-dark-secondary rounded-lg border border-white/5 p-6">
        <h3 className="text-lg font-semibold text-logo-gray mb-4">SWOT Contemporaneo</h3>
        <div className="grid grid-cols-2 gap-4">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="p-4 bg-white/5 rounded-lg animate-pulse h-48" />
          ))}
        </div>
      </div>
    )
  }

  if (!swot || swot.error) {
    return (
      <div className="bg-bg-dark-secondary rounded-lg border border-white/5 p-6">
        <h3 className="text-lg font-semibold text-logo-gray mb-4">SWOT Contemporaneo</h3>
        <p className="text-logo-gray/60 text-sm">Erro ao gerar analise SWOT</p>
      </div>
    )
  }

  return (
    <div className="bg-bg-dark-secondary rounded-lg border border-white/5 p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-logo-gray">SWOT Contemporaneo</h3>
        <button
          onClick={() => setShowTows(!showTows)}
          className="text-sm text-cyan-400 hover:text-cyan-300 transition-colors"
        >
          {showTows ? 'Ver Matriz SWOT' : 'Ver Estrategias TOWS'}
        </button>
      </div>

      {!showTows ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Forcas */}
          <SwotQuadrant
            title="Forcas"
            items={swot.strengths || []}
            color="green"
            icon={
              <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M3.172 5.172a4 4 0 015.656 0L10 6.343l1.172-1.171a4 4 0 115.656 5.656L10 17.657l-6.828-6.829a4 4 0 010-5.656z" clipRule="evenodd" />
              </svg>
            }
          />

          {/* Fraquezas */}
          <SwotQuadrant
            title="Fraquezas"
            items={swot.weaknesses || []}
            color="red"
            icon={
              <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
              </svg>
            }
          />

          {/* Oportunidades */}
          <SwotQuadrant
            title="Oportunidades"
            items={swot.opportunities || []}
            color="blue"
            icon={
              <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-8.707l-3-3a1 1 0 00-1.414 0l-3 3a1 1 0 001.414 1.414L9 9.414V13a1 1 0 102 0V9.414l1.293 1.293a1 1 0 001.414-1.414z" clipRule="evenodd" />
              </svg>
            }
          />

          {/* Ameacas */}
          <SwotQuadrant
            title="Ameacas"
            items={swot.threats || []}
            color="orange"
            icon={
              <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M11.3 1.046A1 1 0 0112 2v5h4a1 1 0 01.82 1.573l-7 10A1 1 0 018 18v-5H4a1 1 0 01-.82-1.573l7-10a1 1 0 011.12-.38z" clipRule="evenodd" />
              </svg>
            }
          />
        </div>
      ) : (
        <div className="space-y-4">
          {/* Estrategias TOWS */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* SO */}
            <div className="p-4 bg-green-500/5 rounded-lg border border-green-500/20">
              <h4 className="font-semibold text-green-400 mb-2 text-sm">SO (Forca + Oportunidade)</h4>
              <ul className="space-y-2">
                {(swot.tows_strategies?.so || []).map((strategy, idx) => (
                  <li key={idx} className="text-logo-gray/80 text-sm">- {strategy}</li>
                ))}
              </ul>
            </div>

            {/* WO */}
            <div className="p-4 bg-blue-500/5 rounded-lg border border-blue-500/20">
              <h4 className="font-semibold text-blue-400 mb-2 text-sm">WO (Fraqueza + Oportunidade)</h4>
              <ul className="space-y-2">
                {(swot.tows_strategies?.wo || []).map((strategy, idx) => (
                  <li key={idx} className="text-logo-gray/80 text-sm">- {strategy}</li>
                ))}
              </ul>
            </div>

            {/* ST */}
            <div className="p-4 bg-yellow-500/5 rounded-lg border border-yellow-500/20">
              <h4 className="font-semibold text-yellow-400 mb-2 text-sm">ST (Forca + Ameaca)</h4>
              <ul className="space-y-2">
                {(swot.tows_strategies?.st || []).map((strategy, idx) => (
                  <li key={idx} className="text-logo-gray/80 text-sm">- {strategy}</li>
                ))}
              </ul>
            </div>

            {/* WT */}
            <div className="p-4 bg-red-500/5 rounded-lg border border-red-500/20">
              <h4 className="font-semibold text-red-400 mb-2 text-sm">WT (Fraqueza + Ameaca)</h4>
              <ul className="space-y-2">
                {(swot.tows_strategies?.wt || []).map((strategy, idx) => (
                  <li key={idx} className="text-logo-gray/80 text-sm">- {strategy}</li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
