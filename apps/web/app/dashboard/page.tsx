'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import {
  LayoutDashboard,
  Building2,
  Users,
  FileText,
  Settings,
  LogOut,
  TrendingUp,
  Activity,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { AtlasChat } from '@/components/atlas/atlas-chat';

interface Stats {
  totalCompanies: number;
  totalPeople: number;
  pendingAnalysis: number;
  completedToday: number;
}

export default function DashboardPage() {
  const router = useRouter();
  const [stats, setStats] = useState<Stats>({
    totalCompanies: 0,
    totalPeople: 0,
    pendingAnalysis: 0,
    completedToday: 0,
  });

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (!token) {
      router.push('/');
      return;
    }

    // Fetch dashboard stats (optional - uses placeholders if unavailable)
    fetch('/api/companies/stats', {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((res) => {
        if (!res.ok) return null;
        return res.json();
      })
      .then((data) => {
        if (data) setStats(data);
      })
      .catch(() => {
        // Stats endpoint not available - use default values
      });
  }, [router]);

  function handleLogout() {
    localStorage.removeItem('token');
    router.push('/');
  }

  return (
    <div className="min-h-screen bg-grid bg-glow">
      {/* Sidebar */}
      <aside className="fixed left-0 top-0 h-full w-64 border-r border-cyan-500/20 bg-[#0f1629]/95 backdrop-blur-xl">
        <div className="p-6 border-b border-cyan-500/20">
          <div className="flex items-center gap-3">
            <img src="/iconsai-logo.png" alt="Iconsai" className="h-10 w-auto" />
            <div>
              <h1 className="font-bold text-gradient">Scraping Hub</h1>
              <p className="text-xs text-muted-foreground">Business Intelligence</p>
            </div>
          </div>
        </div>

        <nav className="p-4 space-y-1">
          <NavItem icon={LayoutDashboard} label="Dashboard" active />
          <NavItem icon={Building2} label="Empresas" />
          <NavItem icon={Users} label="Pessoas" />
          <NavItem icon={FileText} label="Relatorios" />
          <NavItem icon={Settings} label="Configuracoes" />
        </nav>

        <div className="absolute bottom-0 left-0 right-0 p-4 border-t border-cyan-500/20">
          <Button
            variant="ghost"
            className="w-full justify-start gap-2 text-red-400 hover:text-red-300 hover:bg-red-500/10"
            onClick={handleLogout}
          >
            <LogOut className="h-4 w-4" />
            Sair
          </Button>
        </div>
      </aside>

      {/* Main Content */}
      <main className="ml-64 p-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-foreground">Dashboard</h1>
          <p className="text-muted-foreground">Visao geral do sistema de scraping</p>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <StatCard
            title="Empresas"
            value={stats.totalCompanies}
            icon={Building2}
            trend="+12%"
          />
          <StatCard
            title="Pessoas"
            value={stats.totalPeople}
            icon={Users}
            trend="+8%"
          />
          <StatCard
            title="Pendentes"
            value={stats.pendingAnalysis}
            icon={Activity}
            trend="-5%"
          />
          <StatCard
            title="Hoje"
            value={stats.completedToday}
            icon={TrendingUp}
            trend="+25%"
          />
        </div>

        {/* Quick Actions */}
        <Card>
          <CardHeader>
            <CardTitle>Acoes Rapidas</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <Button variant="outline" className="h-auto py-4 flex-col gap-2">
                <Building2 className="h-6 w-6" />
                <span>Nova Busca de Empresa</span>
              </Button>
              <Button variant="outline" className="h-auto py-4 flex-col gap-2">
                <Users className="h-6 w-6" />
                <span>Enriquecer Socios</span>
              </Button>
              <Button variant="outline" className="h-auto py-4 flex-col gap-2">
                <FileText className="h-6 w-6" />
                <span>Gerar Relatorio</span>
              </Button>
            </div>
          </CardContent>
        </Card>
      </main>

      {/* Atlas Chat */}
      <AtlasChat />
    </div>
  );
}

function NavItem({
  icon: Icon,
  label,
  active = false,
}: {
  icon: typeof LayoutDashboard;
  label: string;
  active?: boolean;
}) {
  return (
    <button
      className={`flex w-full items-center gap-3 rounded-xl px-4 py-3 text-sm font-medium transition-all ${
        active
          ? 'bg-cyan-500/15 text-cyan-400 border border-cyan-500/30'
          : 'text-muted-foreground hover:bg-white/5 hover:text-foreground'
      }`}
    >
      <Icon className="h-5 w-5" />
      {label}
    </button>
  );
}

function StatCard({
  title,
  value,
  icon: Icon,
  trend,
}: {
  title: string;
  value: number;
  icon: typeof Building2;
  trend: string;
}) {
  const isPositive = trend.startsWith('+');

  return (
    <Card>
      <CardContent className="pt-6">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm text-muted-foreground">{title}</p>
            <p className="text-3xl font-bold text-foreground mt-1">
              {value.toLocaleString('pt-BR')}
            </p>
          </div>
          <div className="flex h-12 w-12 items-center justify-center rounded-full bg-cyan-500/10">
            <Icon className="h-6 w-6 text-cyan-400" />
          </div>
        </div>
        <div className="mt-4 flex items-center gap-1">
          <span
            className={`text-sm font-medium ${isPositive ? 'text-green-400' : 'text-red-400'}`}
          >
            {trend}
          </span>
          <span className="text-xs text-muted-foreground">vs mes anterior</span>
        </div>
      </CardContent>
    </Card>
  );
}
