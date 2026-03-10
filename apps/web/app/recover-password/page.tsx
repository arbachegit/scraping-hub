'use client';

import { useState, type FormEvent } from 'react';
import Image from 'next/image';
import Link from 'next/link';
import { Mail, Loader2, ArrowLeft } from 'lucide-react';
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
import { recoverPassword } from '@/lib/api';

export default function RecoverPasswordPage() {
  const [email, setEmail] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [sent, setSent] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      await recoverPassword(email);
      setSent(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erro ao solicitar recuperacao');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-4 bg-grid bg-glow relative overflow-hidden">
      <div className="absolute top-1/4 left-1/4 w-64 h-64 bg-cyan-500/10 rounded-full blur-[100px]" />
      <div className="absolute bottom-1/4 right-1/4 w-64 h-64 bg-blue-500/10 rounded-full blur-[100px]" />

      <Card className="w-full max-w-md relative z-10">
        <CardHeader className="text-center">
          <div className="flex flex-col items-center">
            <Image src="/iconsai-logo.png" alt="Iconsai" width={180} height={64} className="h-16 w-auto mb-4" />
            <CardTitle>Recuperar Senha</CardTitle>
            <CardDescription>
              {sent
                ? 'Verifique seu email'
                : 'Informe seu email para receber um link de recuperacao'}
            </CardDescription>
          </div>
        </CardHeader>

        <CardContent>
          {sent ? (
            <div className="space-y-4">
              <div className="p-3 rounded-lg bg-green-500/10 border border-green-500/30 text-green-400 text-sm text-center">
                Se o email estiver cadastrado, enviaremos instrucoes por email e SMS.
              </div>
              <p className="text-xs text-muted-foreground text-center">
                Verifique seu email (incluindo spam) e SMS. O link expira em 1 hora.
              </p>
              <Link href="/" className="block">
                <Button variant="outline" className="w-full gap-1.5">
                  <ArrowLeft className="h-4 w-4" />
                  Voltar ao Login
                </Button>
              </Link>
            </div>
          ) : (
            <>
              {error && (
                <div className="mb-4 p-3 rounded-lg bg-red-500/10 border border-red-500/30 text-red-400 text-sm">
                  {error}
                </div>
              )}

              <form onSubmit={handleSubmit} className="space-y-4">
                <div className="space-y-2">
                  <label className="text-sm font-medium text-foreground">Email</label>
                  <div className="relative">
                    <Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-cyan-500/50" />
                    <Input
                      type="email"
                      placeholder="seu@email.com"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      className="pl-11"
                      required
                    />
                  </div>
                </div>

                <Button type="submit" className="w-full" disabled={loading}>
                  {loading ? (
                    <>
                      <Loader2 className="h-5 w-5 animate-spin" />
                      Enviando...
                    </>
                  ) : (
                    'Enviar Link de Recuperacao'
                  )}
                </Button>
              </form>

              <div className="flex justify-center pt-4">
                <Link href="/" className="text-sm text-cyan-400 hover:text-cyan-300 transition-colors">
                  Voltar ao Login
                </Link>
              </div>
            </>
          )}
        </CardContent>

        <CardFooter className="flex-col text-center text-xs text-muted-foreground">
          <p>Business Intelligence Brasil</p>
          <p className="text-muted-foreground/60">Iconsai - Todos os direitos reservados</p>
        </CardFooter>
      </Card>
    </div>
  );
}
