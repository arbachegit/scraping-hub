'use client';

import { Suspense, useState, type FormEvent } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Image from 'next/image';
import { KeyRound, Loader2, MapPin, CreditCard } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
  CardFooter,
} from '@/components/ui/card';
import { setPassword, lookupCep } from '@/lib/api';

export default function SetPasswordPage() {
  return (
    <Suspense>
      <SetPasswordContent />
    </Suspense>
  );
}

function SetPasswordContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const token = searchParams.get('token') || '';

  // Profile fields
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

  // Password fields
  const [password, setPasswordValue] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');

  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

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

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError('');

    if (!token) {
      setError('Token nao encontrado. Verifique o link recebido por email.');
      return;
    }

    // Validate CPF
    const cpfDigits = cpf.replace(/\D/g, '');
    if (cpfDigits.length !== 11) {
      setError('CPF deve ter 11 digitos.');
      return;
    }

    // Validate CEP
    const cepDigits = cep.replace(/\D/g, '');
    if (cepDigits.length !== 8) {
      setError('CEP deve ter 8 digitos.');
      return;
    }

    // Validate address fields
    if (!logradouro || !numero || !bairro || !cidade || !uf) {
      setError('Preencha todos os campos obrigatorios do endereco.');
      return;
    }
    if (!/^[A-Z]{2}$/.test(uf)) {
      setError('UF deve ter 2 letras maiusculas (ex: SP, RJ).');
      return;
    }

    // Validate password
    if (password !== confirmPassword) {
      setError('As senhas nao coincidem.');
      return;
    }

    if (password.length < 8) {
      setError('A senha deve ter no minimo 8 caracteres.');
      return;
    }

    if (!/[A-Z]/.test(password)) {
      setError('A senha deve conter pelo menos 1 letra maiuscula.');
      return;
    }

    if (!/[0-9]/.test(password)) {
      setError('A senha deve conter pelo menos 1 numero.');
      return;
    }

    setLoading(true);
    try {
      const result = await setPassword({
        token,
        password,
        cpf,
        cep,
        logradouro,
        numero,
        complemento: complemento || undefined,
        bairro,
        cidade,
        uf,
      });
      if (result.email) {
        router.push(`/verify?email=${encodeURIComponent(result.email)}`);
      } else {
        router.push('/verify');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erro ao definir senha');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-4 bg-grid bg-glow relative overflow-hidden">
      <div className="absolute top-1/4 left-1/4 w-64 h-64 bg-cyan-500/10 rounded-full blur-[100px]" />
      <div className="absolute bottom-1/4 right-1/4 w-64 h-64 bg-blue-500/10 rounded-full blur-[100px]" />

      <Card className="w-full max-w-lg relative z-10">
        <CardHeader className="text-center">
          <div className="flex flex-col items-center">
            <Image src="/iconsai-logo.png" alt="Iconsai" width={180} height={64} className="h-16 w-auto mb-4" />
            <CardTitle>Configurar sua Conta</CardTitle>
            <CardDescription>Preencha seus dados e defina sua senha para acessar o sistema</CardDescription>
          </div>
        </CardHeader>

        <CardContent>
          {error && (
            <div className="mb-4 p-3 rounded-lg bg-red-500/10 border border-red-500/30 text-red-400 text-sm">
              {error}
            </div>
          )}

          {!token && (
            <div className="mb-4 p-3 rounded-lg bg-amber-500/10 border border-amber-500/30 text-amber-400 text-sm">
              Link invalido ou expirado. Solicite um novo convite ao administrador.
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Section: CPF */}
            <div className="space-y-2">
              <label className="text-sm font-medium text-foreground">
                CPF <span className="text-red-400">*</span>
              </label>
              <div className="relative">
                <CreditCard className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-cyan-500/50" />
                <Input
                  value={cpf}
                  onChange={(e) => handleCpfChange(e.target.value)}
                  placeholder="000.000.000-00"
                  maxLength={14}
                  className="pl-11"
                  required
                />
              </div>
            </div>

            {/* Section: Address */}
            <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider pt-1">Endereco</p>

            {/* CEP */}
            <div className="space-y-1">
              <label className="text-sm font-medium text-foreground">
                CEP <span className="text-red-400">*</span>
              </label>
              <div className="relative">
                <MapPin className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-cyan-500/50" />
                <Input
                  value={cep}
                  onChange={(e) => handleCepChange(e.target.value)}
                  placeholder="00000-000"
                  maxLength={9}
                  className="pl-11"
                  required
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
              <label className="text-sm font-medium text-foreground">
                Logradouro <span className="text-red-400">*</span>
              </label>
              <Input
                value={logradouro}
                onChange={(e) => setLogradouro(e.target.value)}
                placeholder="Rua, Avenida, etc."
                required
              />
            </div>

            {/* Numero + Complemento */}
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <label className="text-sm font-medium text-foreground">
                  Numero <span className="text-red-400">*</span>
                </label>
                <Input
                  value={numero}
                  onChange={(e) => setNumero(e.target.value)}
                  placeholder="123"
                  required
                />
              </div>
              <div className="space-y-1">
                <label className="text-sm font-medium text-foreground">
                  Complemento
                </label>
                <Input
                  value={complemento}
                  onChange={(e) => setComplemento(e.target.value)}
                  placeholder="Apto, Sala, etc."
                />
              </div>
            </div>

            {/* Bairro */}
            <div className="space-y-1">
              <label className="text-sm font-medium text-foreground">
                Bairro <span className="text-red-400">*</span>
              </label>
              <Input
                value={bairro}
                onChange={(e) => setBairro(e.target.value)}
                placeholder="Bairro"
                required
              />
            </div>

            {/* Cidade + UF */}
            <div className="grid grid-cols-3 gap-3">
              <div className="col-span-2 space-y-1">
                <label className="text-sm font-medium text-foreground">
                  Cidade <span className="text-red-400">*</span>
                </label>
                <Input
                  value={cidade}
                  onChange={(e) => setCidade(e.target.value)}
                  placeholder="Cidade"
                  required
                />
              </div>
              <div className="space-y-1">
                <label className="text-sm font-medium text-foreground">
                  UF <span className="text-red-400">*</span>
                </label>
                <Input
                  value={uf}
                  onChange={(e) => setUf(e.target.value.toUpperCase())}
                  placeholder="SP"
                  maxLength={2}
                  className="uppercase"
                  required
                />
              </div>
            </div>

            {/* Section: Password */}
            <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider pt-1">Senha de Acesso</p>

            <div className="space-y-2">
              <label className="text-sm font-medium text-foreground">
                Nova Senha <span className="text-red-400">*</span>
              </label>
              <div className="relative">
                <KeyRound className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-cyan-500/50" />
                <Input
                  type="password"
                  placeholder="Minimo 8 caracteres"
                  value={password}
                  onChange={(e) => setPasswordValue(e.target.value)}
                  className="pl-11"
                  required
                  minLength={8}
                />
              </div>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium text-foreground">
                Confirmar Senha <span className="text-red-400">*</span>
              </label>
              <div className="relative">
                <KeyRound className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-cyan-500/50" />
                <Input
                  type="password"
                  placeholder="Repita a senha"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  className="pl-11"
                  required
                  minLength={8}
                />
              </div>
            </div>

            <p className="text-xs text-muted-foreground">
              A senha deve conter pelo menos 1 letra maiuscula e 1 numero.
            </p>

            <Button type="submit" className="w-full" disabled={loading || !token}>
              {loading ? (
                <>
                  <Loader2 className="h-5 w-5 animate-spin" />
                  Salvando...
                </>
              ) : (
                'Configurar Conta'
              )}
            </Button>
          </form>
        </CardContent>

        <CardFooter className="flex-col text-center text-xs text-muted-foreground">
          <p>Business Intelligence Brasil</p>
          <p className="text-muted-foreground/60">Iconsai - Todos os direitos reservados</p>
        </CardFooter>
      </Card>
    </div>
  );
}
