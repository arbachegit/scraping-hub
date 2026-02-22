'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import {
  Building2,
  Users,
  Flag,
  Newspaper,
  LogOut,
  Shield,
  Vote,
} from 'lucide-react';
import { getUser, getHealth, getStats } from '@/lib/api';
import { AtlasChat } from '@/components/atlas/atlas-chat';
import { CompanyModal } from '@/components/modals/company-modal';
import { CnaeModal } from '@/components/modals/cnae-modal';
import { RegimeModal } from '@/components/modals/regime-modal';
import { PeopleModal } from '@/components/modals/people-modal';
import { NewsModal } from '@/components/modals/news-modal';
import {
  EmpresasListingModal,
  PessoasListingModal,
  NoticiasListingModal,
} from '@/components/modals/listing-modal';

export default function DashboardPage() {
  const router = useRouter();
  const [userName, setUserName] = useState('');
  const [userRole, setUserRole] = useState('');
  const [version, setVersion] = useState('v1.14.2026');

  // Modal states
  const [companyModalOpen, setCompanyModalOpen] = useState(false);
  const [cnaeModalOpen, setCnaeModalOpen] = useState(false);
  const [regimeModalOpen, setRegimeModalOpen] = useState(false);
  const [peopleModalOpen, setPeopleModalOpen] = useState(false);
  const [newsModalOpen, setNewsModalOpen] = useState(false);
  const [empresasListingOpen, setEmpresasListingOpen] = useState(false);
  const [pessoasListingOpen, setPessoasListingOpen] = useState(false);
  const [noticiasListingOpen, setNoticiasListingOpen] = useState(false);

  // Selected values from picker modals
  const [selectedCnae, setSelectedCnae] = useState<string>('');
  const [selectedRegime, setSelectedRegime] = useState<string>('');

  // Auth check
  useEffect(() => {
    const token = localStorage.getItem('token');
    if (!token) {
      router.push('/');
      return;
    }
  }, [router]);

  // Load user info
  const userQuery = useQuery({
    queryKey: ['user'],
    queryFn: getUser,
    retry: false,
  });

  useEffect(() => {
    if (userQuery.data) {
      setUserName(userQuery.data.name || userQuery.data.email);
      setUserRole(userQuery.data.role);
    }
    if (userQuery.isError) {
      handleLogout();
    }
  }, [userQuery.data, userQuery.isError]);

  // Load version
  const healthQuery = useQuery({
    queryKey: ['health'],
    queryFn: getHealth,
  });

  useEffect(() => {
    if (healthQuery.data?.version) {
      setVersion('v' + healthQuery.data.version);
    }
  }, [healthQuery.data]);

  // Load stats
  const statsQuery = useQuery({
    queryKey: ['stats'],
    queryFn: getStats,
    refetchInterval: 60000, // Refresh every minute
  });

  function handleLogout() {
    localStorage.removeItem('token');
    localStorage.removeItem('tokenType');
    router.push('/');
  }

  function handleCnaeSelect(codigo: string) {
    setSelectedCnae(codigo);
  }

  function handleRegimeSelect(codigo: string) {
    setSelectedRegime(codigo);
  }

  function openPoliticosFromCard() {
    // Atlas agent stub - will be implemented
    console.log('Atlas: Politicos module clicked');
  }

  return (
    <div className="min-h-screen bg-[#0a0e1a]">
      {/* Header */}
      <header className="sticky top-0 z-40 bg-[#0f1629]/80 backdrop-blur-xl border-b border-cyan-500/10">
        <div className="flex items-center justify-between px-8 py-4">
          <div className="flex items-center gap-4">
            <picture>
              <source srcSet="/iconsai-logo.webp" type="image/webp" />
              <img src="/iconsai-logo.png" alt="Iconsai" className="h-10 w-auto" />
            </picture>
            <h1 className="text-xl font-bold bg-gradient-to-r from-cyan-400 via-blue-400 to-purple-400 bg-clip-text text-transparent">
              Scraping Hub
            </h1>
            <span className="px-2 py-1 text-xs text-slate-400 bg-slate-400/10 border border-slate-400/20 rounded">
              {version}
            </span>
          </div>
          <div className="flex items-center gap-4">
            {userRole === 'super_admin' && (
              <a
                href="/admin"
                className="inline-flex items-center gap-2 h-12 px-4 bg-cyan-500/15 border-2 border-cyan-500 text-cyan-400 rounded-xl text-sm font-semibold hover:bg-cyan-500 hover:text-white transition-colors"
              >
                <Shield className="h-4 w-4" />
                <span>Gerenciar Usuarios</span>
              </a>
            )}
            <span className="inline-flex items-center justify-center h-12 px-4 bg-slate-400/15 border-2 border-slate-400 rounded-xl text-slate-200 text-sm font-medium">
              {userName || '-'}
            </span>
            <button
              onClick={handleLogout}
              className="inline-flex items-center gap-2 h-12 px-4 bg-red-500/15 border-2 border-red-500 text-red-400 rounded-xl text-sm font-medium hover:bg-red-500 hover:text-white transition-colors"
            >
              <LogOut className="h-4 w-4" />
              Sair
            </button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-5xl mx-auto px-8 py-8">
        <h2 className="text-2xl font-bold text-slate-300 mb-4">Modulos de Inteligencia</h2>

        {/* Stats Badges */}
        <div className="flex flex-wrap gap-3 mb-8">
          <StatBadge
            icon={Building2}
            label="Empresas"
            value={statsQuery.data?.stats.empresas ?? 0}
            color="red"
          />
          <StatBadge
            icon={Users}
            label="Pessoas"
            value={statsQuery.data?.stats.pessoas ?? 0}
            color="orange"
          />
          <StatBadge
            icon={Flag}
            label="Politicos"
            value={statsQuery.data?.stats.politicos ?? 0}
            color="blue"
          />
          <StatBadge
            icon={Vote}
            label="Mandatos"
            value={statsQuery.data?.stats.mandatos ?? 0}
            color="purple"
          />
          <StatBadge
            icon={Newspaper}
            label="Noticias"
            value={statsQuery.data?.stats.noticias ?? 0}
            color="green"
          />
        </div>

        {/* Module Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Empresas */}
          <ModuleCard
            icon={Building2}
            iconColor="red"
            title="Empresas"
            description="Busque por CNPJ via BrasilAPI + Serper. Dados oficiais da Receita Federal."
            onClick={() => setCompanyModalOpen(true)}
          />

          {/* Pessoas */}
          <ModuleCard
            icon={Users}
            iconColor="orange"
            title="Pessoas"
            description="Pesquise perfis profissionais e analise talentos."
            onClick={() => setPeopleModalOpen(true)}
          />

          {/* Politicos */}
          <ModuleCard
            icon={Flag}
            iconColor="blue"
            title="Politicos"
            description="Perfis de politicos e percepcao publica."
            badge="Ativo"
            onClick={openPoliticosFromCard}
          />

          {/* Noticias */}
          <ModuleCard
            icon={Newspaper}
            iconColor="green"
            title="Noticias"
            description="Monitore noticias e cenario economico."
            onClick={() => setNewsModalOpen(true)}
          />
        </div>
      </main>

      {/* Atlas Chat */}
      <AtlasChat />

      {/* Modals */}
      <CompanyModal
        isOpen={companyModalOpen}
        onClose={() => setCompanyModalOpen(false)}
        onOpenCnaeModal={() => setCnaeModalOpen(true)}
        onOpenRegimeModal={() => setRegimeModalOpen(true)}
        onOpenListingModal={() => setEmpresasListingOpen(true)}
        userName={userName}
        selectedCnae={selectedCnae}
        selectedRegime={selectedRegime}
      />

      <CnaeModal
        isOpen={cnaeModalOpen}
        onClose={() => setCnaeModalOpen(false)}
        onSelect={handleCnaeSelect}
      />

      <RegimeModal
        isOpen={regimeModalOpen}
        onClose={() => setRegimeModalOpen(false)}
        onSelect={handleRegimeSelect}
      />

      <PeopleModal
        isOpen={peopleModalOpen}
        onClose={() => setPeopleModalOpen(false)}
        onOpenListingModal={() => setPessoasListingOpen(true)}
      />

      <NewsModal
        isOpen={newsModalOpen}
        onClose={() => setNewsModalOpen(false)}
        onOpenListingModal={() => setNoticiasListingOpen(true)}
      />

      <EmpresasListingModal
        isOpen={empresasListingOpen}
        onClose={() => setEmpresasListingOpen(false)}
      />

      <PessoasListingModal
        isOpen={pessoasListingOpen}
        onClose={() => setPessoasListingOpen(false)}
      />

      <NoticiasListingModal
        isOpen={noticiasListingOpen}
        onClose={() => setNoticiasListingOpen(false)}
      />
    </div>
  );
}

function ModuleCard({
  icon: Icon,
  iconColor,
  title,
  description,
  badge,
  onClick,
}: {
  icon: typeof Building2;
  iconColor: 'red' | 'orange' | 'blue' | 'green' | 'cyan' | 'purple';
  title: string;
  description: string;
  badge?: string;
  onClick: () => void;
}) {
  const iconColorMap = {
    red: 'bg-red-500/10 text-red-400',
    orange: 'bg-orange-500/10 text-orange-400',
    blue: 'bg-blue-500/10 text-blue-400',
    green: 'bg-green-500/10 text-green-400',
    cyan: 'bg-cyan-500/10 text-cyan-400',
    purple: 'bg-purple-500/10 text-purple-400',
  };

  return (
    <div
      onClick={onClick}
      className="bg-[#0f1629]/80 border border-white/5 rounded-2xl p-6 cursor-pointer transition-all duration-300 hover:border-cyan-500/30 hover:-translate-y-0.5 hover:shadow-lg hover:shadow-cyan-500/10"
    >
      <div className="flex items-center gap-4 mb-4">
        <div
          className={`w-12 h-12 rounded-xl flex items-center justify-center ${iconColorMap[iconColor]}`}
        >
          <Icon className="w-6 h-6" />
        </div>
        <h3 className="text-lg font-semibold text-slate-300">{title}</h3>
      </div>
      <p className="text-slate-400/80 text-sm leading-relaxed">{description}</p>
      {badge && (
        <span className="inline-block mt-3 px-2 py-1 text-xs bg-green-500/10 border border-green-500/30 text-green-400 rounded">
          {badge}
        </span>
      )}
    </div>
  );
}

function StatBadge({
  icon: Icon,
  label,
  value,
  color,
}: {
  icon: typeof Building2;
  label: string;
  value: number;
  color: 'red' | 'orange' | 'blue' | 'green' | 'cyan' | 'purple';
}) {
  const colorMap = {
    red: 'bg-red-500/10 border-red-500/30 text-red-400',
    orange: 'bg-orange-500/10 border-orange-500/30 text-orange-400',
    blue: 'bg-blue-500/10 border-blue-500/30 text-blue-400',
    green: 'bg-green-500/10 border-green-500/30 text-green-400',
    cyan: 'bg-cyan-500/10 border-cyan-500/30 text-cyan-400',
    purple: 'bg-purple-500/10 border-purple-500/30 text-purple-400',
  };

  const iconColorMap = {
    red: 'text-red-400',
    orange: 'text-orange-400',
    blue: 'text-blue-400',
    green: 'text-green-400',
    cyan: 'text-cyan-400',
    purple: 'text-purple-400',
  };

  const formatNumber = (num: number): string => {
    if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
    if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
    return num.toLocaleString('pt-BR');
  };

  return (
    <div
      className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-full border ${colorMap[color]}`}
    >
      <Icon className={`w-4 h-4 ${iconColorMap[color]}`} />
      <span className="text-sm font-medium tabular-nums">{formatNumber(value)}</span>
      <span className="text-xs opacity-70">{label}</span>
    </div>
  );
}
