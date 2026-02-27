'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { MapPin, CreditCard, Loader2, CheckCircle2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { isAuthenticated } from '@/lib/auth';
import { completeProfile, lookupCep, getUser } from '@/lib/api';

export default function ProfileCompletePage() {
  const router = useRouter();

  const [cpf, setCpf] = useState('');
  const [cep, setCep] = useState('');
  const [logradouro, setLogradouro] = useState('');
  const [numero, setNumero] = useState('');
  const [complemento, setComplemento] = useState('');
  const [bairro, setBairro] = useState('');
  const [cidade, setCidade] = useState('');
  const [uf, setUf] = useState('');

  const [cepLoading, setCepLoading] = useState(false);
  const [cepError, setCepError] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);

  // Auth check
  useEffect(() => {
    if (!isAuthenticated()) {
      router.push('/');
      return;
    }
    // Check if profile is already complete
    getUser().then((user) => {
      if (user.profile_complete) {
        router.push('/dashboard');
      }
    }).catch(() => {
      router.push('/');
    });
  }, [router]);

  // CPF mask: 000.000.000-00
  function handleCpfChange(value: string) {
    const digits = value.replace(/\D/g, '').slice(0, 11);
    let masked = digits;
    if (digits.length > 3) masked = digits.slice(0, 3) + '.' + digits.slice(3);
    if (digits.length > 6) masked = masked.slice(0, 7) + '.' + digits.slice(6);
    if (digits.length > 9) masked = masked.slice(0, 11) + '-' + digits.slice(9);
    setCpf(masked);
  }

  // CEP mask: 00000-000
  function handleCepChange(value: string) {
    const digits = value.replace(/\D/g, '').slice(0, 8);
    let masked = digits;
    if (digits.length > 5) masked = digits.slice(0, 5) + '-' + digits.slice(5);
    setCep(masked);
    setCepError('');

    // Auto-lookup when 8 digits entered
    if (digits.length === 8) {
      fetchCep(digits);
    }
  }

  async function fetchCep(cleanCep: string) {
    setCepLoading(true);
    setCepError('');
    try {
      const data = await lookupCep(cleanCep);
      setLogradouro(data.street || '');
      setBairro(data.neighborhood || '');
      setCidade(data.city || '');
      setUf(data.state || '');
    } catch {
      setCepError('CEP nao encontrado. Preencha manualmente.');
    } finally {
      setCepLoading(false);
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError('');

    // Validate
    const cpfDigits = cpf.replace(/\D/g, '');
    if (cpfDigits.length !== 11) {
      setError('CPF deve ter 11 digitos.');
      return;
    }
    const cepDigits = cep.replace(/\D/g, '');
    if (cepDigits.length !== 8) {
      setError('CEP deve ter 8 digitos.');
      return;
    }
    if (!logradouro || !numero || !bairro || !cidade || !uf) {
      setError('Preencha todos os campos obrigatorios.');
      return;
    }
    if (!/^[A-Z]{2}$/.test(uf)) {
      setError('UF deve ter 2 letras maiusculas (ex: SP, RJ).');
      return;
    }

    setSubmitting(true);
    try {
      await completeProfile({
        cpf,
        cep,
        logradouro,
        numero,
        complemento: complemento || undefined,
        bairro,
        cidade,
        uf,
      });
      setSuccess(true);
      setTimeout(() => router.push('/dashboard'), 1500);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Erro ao salvar perfil';
      setError(message);
    } finally {
      setSubmitting(false);
    }
  }

  if (success) {
    return (
      <div className="min-h-screen bg-[#0a0e1a] flex items-center justify-center p-4">
        <Card className="w-full max-w-md bg-[#0f1629]/80 border-green-500/30">
          <CardContent className="flex flex-col items-center gap-4 py-12">
            <CheckCircle2 className="h-12 w-12 text-green-400" />
            <p className="text-green-400 font-medium">Perfil completado com sucesso!</p>
            <p className="text-slate-400 text-sm">Redirecionando para o dashboard...</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#0a0e1a] flex items-center justify-center p-4">
      <Card className="w-full max-w-lg bg-[#0f1629]/80 border-white/10">
        <CardHeader className="text-center">
          <CardTitle className="text-xl font-bold text-slate-100">
            Complete seu Perfil
          </CardTitle>
          <CardDescription className="text-slate-400">
            Para continuar, preencha seu CPF e endereco.
          </CardDescription>
        </CardHeader>

        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            {/* CEP - First field, triggers auto-fill */}
            <div className="space-y-1">
              <label className="text-xs font-medium text-slate-300">
                CEP <span className="text-red-400">*</span>
              </label>
              <div className="relative">
                <MapPin className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-500" />
                <Input
                  value={cep}
                  onChange={(e) => handleCepChange(e.target.value)}
                  placeholder="00000-000"
                  maxLength={9}
                  className="pl-10 h-10"
                />
                {cepLoading && (
                  <Loader2 className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-cyan-400 animate-spin" />
                )}
              </div>
              {cepError && (
                <p className="text-xs text-yellow-400">{cepError}</p>
              )}
            </div>

            {/* Logradouro */}
            <div className="space-y-1">
              <label className="text-xs font-medium text-slate-300">
                Logradouro <span className="text-red-400">*</span>
              </label>
              <Input
                value={logradouro}
                onChange={(e) => setLogradouro(e.target.value)}
                placeholder="Rua, Avenida, etc."
                className="h-10"
              />
            </div>

            {/* Numero + Complemento */}
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <label className="text-xs font-medium text-slate-300">
                  Numero <span className="text-red-400">*</span>
                </label>
                <Input
                  value={numero}
                  onChange={(e) => setNumero(e.target.value)}
                  placeholder="123"
                  className="h-10"
                />
              </div>
              <div className="space-y-1">
                <label className="text-xs font-medium text-slate-300">
                  Complemento
                </label>
                <Input
                  value={complemento}
                  onChange={(e) => setComplemento(e.target.value)}
                  placeholder="Apto, Sala, etc."
                  className="h-10"
                />
              </div>
            </div>

            {/* Bairro */}
            <div className="space-y-1">
              <label className="text-xs font-medium text-slate-300">
                Bairro <span className="text-red-400">*</span>
              </label>
              <Input
                value={bairro}
                onChange={(e) => setBairro(e.target.value)}
                placeholder="Bairro"
                className="h-10"
              />
            </div>

            {/* Cidade + UF */}
            <div className="grid grid-cols-3 gap-3">
              <div className="col-span-2 space-y-1">
                <label className="text-xs font-medium text-slate-300">
                  Cidade <span className="text-red-400">*</span>
                </label>
                <Input
                  value={cidade}
                  onChange={(e) => setCidade(e.target.value)}
                  placeholder="Cidade"
                  className="h-10"
                />
              </div>
              <div className="space-y-1">
                <label className="text-xs font-medium text-slate-300">
                  UF <span className="text-red-400">*</span>
                </label>
                <Input
                  value={uf}
                  onChange={(e) => setUf(e.target.value.toUpperCase())}
                  placeholder="SP"
                  maxLength={2}
                  className="h-10 uppercase"
                />
              </div>
            </div>

            {/* CPF */}
            <div className="space-y-1">
              <label className="text-xs font-medium text-slate-300">
                CPF <span className="text-red-400">*</span>
              </label>
              <div className="relative">
                <CreditCard className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-500" />
                <Input
                  value={cpf}
                  onChange={(e) => handleCpfChange(e.target.value)}
                  placeholder="000.000.000-00"
                  maxLength={14}
                  className="pl-10 h-10"
                />
              </div>
            </div>

            {/* Error */}
            {error && (
              <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-3">
                <p className="text-red-400 text-sm">{error}</p>
              </div>
            )}

            {/* Submit */}
            <Button
              type="submit"
              disabled={submitting}
              className="w-full h-11 bg-cyan-500 hover:bg-cyan-600 text-white font-medium"
            >
              {submitting ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin mr-2" />
                  Salvando...
                </>
              ) : (
                'Salvar e Continuar'
              )}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
