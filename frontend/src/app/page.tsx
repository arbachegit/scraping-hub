'use client'

import Image from 'next/image'
import { useState } from 'react'
import { useRouter } from 'next/navigation'

export default function LoginPage() {
  const router = useRouter()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      const res = await fetch('/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      })

      const data = await res.json()

      if (!res.ok) {
        setError(data.detail || 'Credenciais invalidas')
        return
      }

      // Salvar token e redirecionar
      localStorage.setItem('token', data.access_token)
      router.push('/admin')
    } catch {
      setError('Erro ao conectar com o servidor')
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="min-h-screen bg-bg-dark flex flex-col items-center justify-center px-4">
      {/* Logo Iconsai */}
      <div className="flex justify-center mb-8">
        <Image
          src="/images/iconsai-logo.png"
          alt="Iconsai"
          width={280}
          height={80}
          priority
          className="h-16 w-auto"
        />
      </div>

      {/* Card de Login */}
      <div className="w-full max-w-md">
        <div className="bg-bg-dark-secondary rounded-2xl p-8 shadow-xl border border-white/5">
          <h1 className="text-2xl font-bold text-logo-gray text-center mb-2">
            Bem-vindo
          </h1>
          <p className="text-logo-gray/60 text-center mb-8">
            Faca login para acessar o painel
          </p>

          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Email */}
            <div>
              <label htmlFor="email" className="block text-sm font-medium text-logo-gray mb-2">
                Email
              </label>
              <input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                placeholder="seu@email.com"
                className="w-full px-4 py-3 bg-bg-dark border border-white/10 rounded-lg text-logo-gray placeholder-logo-gray/40 focus:outline-none focus:ring-2 focus:ring-logo-red/50 focus:border-logo-red transition-colors"
              />
            </div>

            {/* Senha */}
            <div>
              <label htmlFor="password" className="block text-sm font-medium text-logo-gray mb-2">
                Senha
              </label>
              <input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                placeholder="••••••••"
                className="w-full px-4 py-3 bg-bg-dark border border-white/10 rounded-lg text-logo-gray placeholder-logo-gray/40 focus:outline-none focus:ring-2 focus:ring-logo-red/50 focus:border-logo-red transition-colors"
              />
            </div>

            {/* Erro */}
            {error && (
              <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-lg">
                <p className="text-red-400 text-sm text-center">{error}</p>
              </div>
            )}

            {/* Botao */}
            <button
              type="submit"
              disabled={loading}
              className="w-full py-3 px-4 bg-logo-red hover:bg-logo-red/90 disabled:bg-logo-red/50 text-white font-semibold rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-logo-red/50 focus:ring-offset-2 focus:ring-offset-bg-dark"
            >
              {loading ? (
                <span className="flex items-center justify-center gap-2">
                  <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                  </svg>
                  Entrando...
                </span>
              ) : (
                'Entrar'
              )}
            </button>
          </form>
        </div>

        {/* Footer */}
        <p className="mt-6 text-center text-logo-gray/40 text-sm">
          Iconsai - Inteligencia Empresarial
        </p>
      </div>
    </main>
  )
}
