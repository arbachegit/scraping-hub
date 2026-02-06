'use client'

interface HypothesisObjective {
  inferred: string
  evidence: string[]
}

interface OKRObjective {
  objective: string
  key_results: string[]
}

interface SuggestedOKR {
  objectives: OKRObjective[]
}

interface SynthesisSectionProps {
  hypothesis?: HypothesisObjective
  okrs?: SuggestedOKR
  isLoading?: boolean
}

export function SynthesisSection({ hypothesis, okrs, isLoading = false }: SynthesisSectionProps) {
  if (isLoading) {
    return (
      <div className="bg-bg-dark-secondary rounded-lg border border-white/5 p-6">
        <h3 className="text-lg font-semibold text-logo-gray mb-4">Hipotese e OKRs</h3>
        <div className="space-y-4 animate-pulse">
          <div className="h-20 bg-white/5 rounded" />
          <div className="h-32 bg-white/5 rounded" />
        </div>
      </div>
    )
  }

  return (
    <div className="bg-bg-dark-secondary rounded-lg border border-white/5 p-6">
      <h3 className="text-lg font-semibold text-logo-gray mb-6">Sintese Estrategica</h3>

      {/* Hipotese de Objetivo */}
      {hypothesis && (
        <div className="mb-6">
          <h4 className="text-sm font-medium text-cyan-400 mb-3 flex items-center gap-2">
            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
            </svg>
            Hipotese de Objetivo
          </h4>
          <div className="p-4 bg-cyan-500/5 rounded-lg border border-cyan-500/20">
            <p className="text-logo-gray/90 mb-3">{hypothesis.inferred}</p>
            {hypothesis.evidence && hypothesis.evidence.length > 0 && (
              <div className="pt-3 border-t border-cyan-500/10">
                <p className="text-xs text-logo-gray/50 mb-2">Evidencias:</p>
                <ul className="space-y-1">
                  {hypothesis.evidence.map((ev, idx) => (
                    <li key={idx} className="text-xs text-logo-gray/60 flex items-start gap-2">
                      <span className="text-cyan-400">-</span>
                      {ev}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>
      )}

      {/* OKRs Sugeridos */}
      {okrs && okrs.objectives && okrs.objectives.length > 0 && (
        <div>
          <h4 className="text-sm font-medium text-green-400 mb-3 flex items-center gap-2">
            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
            </svg>
            OKRs Sugeridos
          </h4>
          <div className="space-y-4">
            {okrs.objectives.map((obj, idx) => (
              <div key={idx} className="p-4 bg-green-500/5 rounded-lg border border-green-500/20">
                <h5 className="font-medium text-logo-gray mb-3">
                  <span className="text-green-400 font-bold mr-2">O{idx + 1}:</span>
                  {obj.objective}
                </h5>
                <ul className="space-y-2 ml-4">
                  {obj.key_results.map((kr, krIdx) => (
                    <li key={krIdx} className="text-sm text-logo-gray/70 flex items-start gap-2">
                      <span className="text-green-400/60 font-mono text-xs">KR{krIdx + 1}</span>
                      {kr}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>
      )}

      {!hypothesis && !okrs && (
        <p className="text-logo-gray/60 text-sm">Sintese nao disponivel</p>
      )}
    </div>
  )
}
