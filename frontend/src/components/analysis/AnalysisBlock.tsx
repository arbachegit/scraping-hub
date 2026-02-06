'use client'

import { useState } from 'react'
import ReactMarkdown from 'react-markdown'

interface AnalysisBlockProps {
  number: number
  title: string
  content: string
  highlights?: string[]
  confidence?: number
  isLoading?: boolean
}

export function AnalysisBlock({
  number,
  title,
  content,
  highlights = [],
  confidence,
  isLoading = false
}: AnalysisBlockProps) {
  const [isExpanded, setIsExpanded] = useState(true)

  if (isLoading) {
    return (
      <div className="bg-bg-dark-secondary rounded-lg border border-white/5 overflow-hidden">
        <div className="p-4 border-b border-white/5 flex items-center gap-3">
          <div className="w-8 h-8 rounded-full bg-cyan-500/20 flex items-center justify-center">
            <span className="text-cyan-400 font-bold text-sm">{number}</span>
          </div>
          <div className="h-5 w-48 bg-white/5 rounded animate-pulse" />
        </div>
        <div className="p-6 space-y-3">
          <div className="h-4 w-full bg-white/5 rounded animate-pulse" />
          <div className="h-4 w-5/6 bg-white/5 rounded animate-pulse" />
          <div className="h-4 w-4/6 bg-white/5 rounded animate-pulse" />
        </div>
      </div>
    )
  }

  return (
    <div className="bg-bg-dark-secondary rounded-lg border border-white/5 overflow-hidden transition-all">
      {/* Header */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full p-4 border-b border-white/5 flex items-center justify-between hover:bg-white/[0.02] transition-colors"
      >
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-full bg-cyan-500/20 flex items-center justify-center">
            <span className="text-cyan-400 font-bold text-sm">{number}</span>
          </div>
          <h3 className="text-logo-gray font-semibold">{title}</h3>
          {confidence && (
            <span className="text-xs text-logo-gray/40 ml-2">
              {Math.round(confidence * 100)}% confianca
            </span>
          )}
        </div>
        <svg
          className={`w-5 h-5 text-logo-gray/40 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {/* Content */}
      {isExpanded && (
        <div className="p-6">
          {/* Highlights */}
          {highlights.length > 0 && (
            <div className="mb-4 flex flex-wrap gap-2">
              {highlights.map((highlight, idx) => (
                <span
                  key={idx}
                  className="px-3 py-1 bg-cyan-500/10 text-cyan-400 text-xs rounded-full"
                >
                  {highlight}
                </span>
              ))}
            </div>
          )}

          {/* Markdown Content */}
          <div className="prose prose-invert prose-sm max-w-none markdown-content">
            <ReactMarkdown
              components={{
                h1: ({ children }) => (
                  <h1 className="text-xl font-bold text-logo-gray mb-4 pb-2 border-b border-white/10">{children}</h1>
                ),
                h2: ({ children }) => (
                  <h2 className="text-lg font-semibold text-cyan-400 mt-8 mb-4 pb-2 border-b border-cyan-500/20">{children}</h2>
                ),
                h3: ({ children }) => (
                  <h3 className="text-base font-semibold text-logo-gray mt-6 mb-3">{children}</h3>
                ),
                p: ({ children }) => (
                  <p className="text-logo-gray/85 mb-4 leading-relaxed text-[15px]">{children}</p>
                ),
                ul: ({ children }) => (
                  <ul className="list-disc ml-5 text-logo-gray/80 mb-4 space-y-2">{children}</ul>
                ),
                ol: ({ children }) => (
                  <ol className="list-decimal ml-5 text-logo-gray/80 mb-4 space-y-2">{children}</ol>
                ),
                li: ({ children }) => (
                  <li className="text-logo-gray/80 text-[15px] leading-relaxed">{children}</li>
                ),
                strong: ({ children }) => (
                  <strong className="text-logo-gray font-semibold">{children}</strong>
                ),
                em: ({ children }) => (
                  <em className="text-logo-gray/70 italic">{children}</em>
                ),
                a: ({ href, children }) => (
                  <a href={href} className="text-cyan-400 hover:underline" target="_blank" rel="noopener noreferrer">
                    {children}
                  </a>
                ),
                blockquote: ({ children }) => (
                  <blockquote className="border-l-4 border-cyan-500/50 pl-4 my-4 italic text-logo-gray/60 bg-cyan-500/5 py-2 rounded-r">
                    {children}
                  </blockquote>
                ),
                hr: () => <hr className="my-6 border-white/10" />,
              }}
            >
              {content}
            </ReactMarkdown>
          </div>
        </div>
      )}
    </div>
  )
}
