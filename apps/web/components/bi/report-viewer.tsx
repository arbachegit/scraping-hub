'use client';

import { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import {
  FileText,
  Plus,
  Loader2,
  ChevronDown,
  ChevronUp,
  Clock,
  BarChart3,
} from 'lucide-react';
import {
  getReportCatalog,
  generateReportApi,
  listEntityReports,
  getReportById,
} from '@/lib/api';
import type { ReportTemplate, GeneratedReport, ReportListItem } from '@/lib/api';

interface ReportViewerProps {
  entityType: string;
  entityId: string;
}

export function ReportViewer({ entityType, entityId }: ReportViewerProps) {
  const [selectedReportId, setSelectedReportId] = useState<string | null>(null);
  const [showCatalog, setShowCatalog] = useState(false);

  // Fetch generated reports
  const reportsQuery = useQuery({
    queryKey: ['entity-reports', entityType, entityId],
    queryFn: () => listEntityReports(entityType, entityId),
    enabled: !!entityId,
  });

  // Fetch catalog
  const catalogQuery = useQuery({
    queryKey: ['report-catalog'],
    queryFn: getReportCatalog,
    enabled: showCatalog,
    staleTime: 5 * 60 * 1000,
  });

  // Fetch selected report detail
  const reportDetailQuery = useQuery({
    queryKey: ['report-detail', selectedReportId],
    queryFn: () => getReportById(selectedReportId!),
    enabled: !!selectedReportId,
  });

  // Generate report
  const generateMutation = useMutation({
    mutationFn: (reportCode: string) => generateReportApi(reportCode, entityType, entityId),
    onSuccess: () => {
      reportsQuery.refetch();
      setShowCatalog(false);
    },
  });

  const reports = reportsQuery.data || [];
  const catalog = catalogQuery.data || [];

  return (
    <div className="rounded-xl border border-cyan-500/20 bg-[#0f1629]/60">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-800">
        <div className="flex items-center gap-2">
          <FileText className="h-4 w-4 text-cyan-400" />
          <h3 className="text-sm font-medium text-white">Relatórios ({reports.length})</h3>
        </div>
        <button
          className="flex items-center gap-1 px-2 py-1 rounded-lg text-xs text-cyan-400 hover:bg-cyan-500/10 transition-colors"
          onClick={() => setShowCatalog(!showCatalog)}
        >
          <Plus className="h-3.5 w-3.5" />
          Gerar
        </button>
      </div>

      {/* Catalog (generate new) */}
      {showCatalog && (
        <div className="px-4 py-3 border-b border-gray-800 bg-gray-800/20">
          <span className="text-xs text-gray-400 mb-2 block">Selecione o tipo de relatório:</span>
          {catalogQuery.isLoading ? (
            <Loader2 className="h-4 w-4 text-gray-400 animate-spin mx-auto" />
          ) : (
            <div className="grid grid-cols-2 gap-1.5">
              {catalog.map((template: ReportTemplate) => (
                <button
                  key={template.id}
                  className="text-left px-2 py-1.5 rounded-lg text-xs hover:bg-gray-700/50 transition-colors border border-gray-700/50 disabled:opacity-50"
                  onClick={() => generateMutation.mutate(template.codigo)}
                  disabled={generateMutation.isPending}
                >
                  <div className="font-medium text-gray-300 truncate">{template.nome}</div>
                  {template.descricao && (
                    <div className="text-gray-500 truncate text-[10px] mt-0.5">{template.descricao}</div>
                  )}
                </button>
              ))}
            </div>
          )}
          {generateMutation.isPending && (
            <div className="flex items-center gap-2 mt-2 text-xs text-cyan-400">
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
              Gerando relatório...
            </div>
          )}
        </div>
      )}

      {/* Reports list */}
      {reports.length === 0 ? (
        <div className="px-4 py-8 text-center text-sm text-gray-500">
          Nenhum relatório gerado. Clique em "Gerar" para criar.
        </div>
      ) : (
        <div className="max-h-[400px] overflow-y-auto">
          {reports.map((report: ReportListItem) => {
            const isSelected = selectedReportId === report.id;

            return (
              <div key={report.id} className="border-b border-gray-800/50 last:border-0">
                <button
                  className="w-full flex items-center gap-2 px-4 py-2.5 text-xs hover:bg-gray-800/30 transition-colors text-left"
                  onClick={() => setSelectedReportId(isSelected ? null : report.id)}
                >
                  <FileText className="h-3.5 w-3.5 text-gray-400 flex-shrink-0" />
                  <span className="text-gray-300 min-w-0 whitespace-nowrap overflow-hidden text-ellipsis flex-1">
                    {report.titulo || report.dim_relatorios?.codigo || 'Relatório'}
                  </span>
                  {report.score_geral != null && (
                    <span className="flex items-center gap-1 text-gray-500 flex-shrink-0">
                      <BarChart3 className="h-3 w-3" />
                      {Math.round(report.score_geral)}
                    </span>
                  )}
                  <span className="text-gray-600 flex-shrink-0 flex items-center gap-1">
                    <Clock className="h-3 w-3" />
                    {new Date(report.created_at).toLocaleDateString('pt-BR')}
                  </span>
                  {isSelected ? (
                    <ChevronUp className="h-3.5 w-3.5 text-gray-500 flex-shrink-0" />
                  ) : (
                    <ChevronDown className="h-3.5 w-3.5 text-gray-500 flex-shrink-0" />
                  )}
                </button>

                {/* Report detail */}
                {isSelected && (
                  <div className="px-4 pb-3 bg-gray-800/20">
                    {reportDetailQuery.isLoading ? (
                      <Loader2 className="h-4 w-4 text-gray-400 animate-spin mx-auto my-4" />
                    ) : reportDetailQuery.data ? (
                      <ReportSections report={reportDetailQuery.data} />
                    ) : null}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

function ReportSections({ report }: { report: GeneratedReport }) {
  const sections = report.sections || [];

  return (
    <div className="space-y-3 pt-2">
      {/* Metrics */}
      {report.metricas && Object.keys(report.metricas).length > 0 && (
        <div className="grid grid-cols-3 gap-2">
          {Object.entries(report.metricas as Record<string, unknown>).slice(0, 6).map(([key, value]) => (
            <div key={key} className="text-center">
              <div className="text-gray-500 text-[10px] truncate">{key.replace(/_/g, ' ')}</div>
              <div className="text-gray-300 text-xs font-mono tabular-nums font-medium">
                {typeof value === 'number' ? (value > 1 ? Math.round(value) : (value * 100).toFixed(0) + '%') : String(value)}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Sections */}
      {sections.map((section: { key: string; titulo: string; tipo: string; data: unknown }, i: number) => (
        <div key={i} className="border-t border-gray-700/50 pt-2">
          <h4 className="text-xs font-medium text-gray-400 mb-1">{section.titulo}</h4>
          <div className="text-xs text-gray-500">
            {section.tipo === 'lista' && Array.isArray(section.data) ? (
              <ul className="space-y-0.5">
                {(section.data as string[]).slice(0, 8).map((item, j) => (
                  <li key={j} className="text-gray-400">- {typeof item === 'string' ? item : JSON.stringify(item)}</li>
                ))}
              </ul>
            ) : section.tipo === 'tabela' && Array.isArray(section.data) ? (
              <div className="overflow-x-auto">
                {(section.data as Record<string, unknown>[]).slice(0, 5).map((row, j) => (
                  <div key={j} className="flex gap-3 py-0.5 text-gray-400">
                    {Object.entries(row).slice(0, 4).map(([k, v]) => (
                      <span key={k} className="min-w-0 truncate">
                        <span className="text-gray-600">{k}:</span> {String(v)}
                      </span>
                    ))}
                  </div>
                ))}
              </div>
            ) : section.tipo === 'score' ? (
              <div className="flex items-center gap-2">
                <div className="w-24 h-2 bg-gray-700 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-cyan-500 rounded-full"
                    style={{ width: `${typeof section.data === 'number' ? section.data : 0}%` }}
                  />
                </div>
                <span className="text-gray-400 font-mono tabular-nums">
                  {typeof section.data === 'number' ? Math.round(section.data) : String(section.data)}
                </span>
              </div>
            ) : (
              <pre className="text-[10px] text-gray-500 whitespace-pre-wrap max-h-[100px] overflow-y-auto">
                {typeof section.data === 'string' ? section.data : JSON.stringify(section.data, null, 2)}
              </pre>
            )}
          </div>
        </div>
      ))}

      {/* Score geral */}
      {report.score_geral != null && (
        <div className="flex items-center justify-between pt-2 border-t border-gray-700/50">
          <span className="text-xs text-gray-500">Score Geral</span>
          <span className="text-sm font-bold text-cyan-400 font-mono tabular-nums">
            {Math.round(report.score_geral)}/100
          </span>
        </div>
      )}
    </div>
  );
}
