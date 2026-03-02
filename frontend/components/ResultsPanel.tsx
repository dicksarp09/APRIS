'use client'

import { motion } from 'framer-motion'
import { useWorkflow } from '@/context/WorkflowContext'
import { FileText, GitBranch, Package, CheckCircle, AlertTriangle, XCircle, Layers, Activity } from 'lucide-react'

export function ResultsPanel() {
  const { results, status } = useWorkflow()

  if (!results || status?.status !== 'completed') {
    return null
  }

  const depGraph = results.dependency_graph || {}
  const maturity = results.maturity_score || {}
  const complexity = results.complexity_profile || {}
  const risk = results.risk_profile || {}

  return (
    <div className="p-4 space-y-4">
      {/* Header Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div className="bg-white rounded-lg p-4 shadow-sm">
          <div className="flex items-center gap-2 mb-1">
            <GitBranch className="w-4 h-4 text-primary" />
            <span className="text-xs text-text-muted">Classification</span>
          </div>
          <div className="text-lg font-bold text-primary">{results.classification}</div>
          <div className="text-xs text-text-muted">{results.primary_language}</div>
        </div>

        <div className="bg-white rounded-lg p-4 shadow-sm">
          <div className="flex items-center gap-2 mb-1">
            <Package className="w-4 h-4 text-primary" />
            <span className="text-xs text-text-muted">Files</span>
          </div>
          <div className="text-lg font-bold">{results.file_count}</div>
          <div className="text-xs text-text-muted">analyzed</div>
        </div>

        <div className="bg-white rounded-lg p-4 shadow-sm">
          <div className="flex items-center gap-2 mb-1">
            <Activity className="w-4 h-4 text-primary" />
            <span className="text-xs text-text-muted">Architecture</span>
          </div>
          <div className="text-lg font-bold">{results.architecture_score.toFixed(1)}</div>
          <div className="text-xs text-text-muted">/ 10</div>
        </div>

        <div className="bg-white rounded-lg p-4 shadow-sm">
          <div className="flex items-center gap-2 mb-1">
            <Layers className="w-4 h-4 text-primary" />
            <span className="text-xs text-text-muted">Maturity</span>
          </div>
          <div className="text-lg font-bold">{maturity.score?.toFixed(1) || 'N/A'}</div>
          <div className="text-xs text-text-muted">{maturity.verdict || ''}</div>
        </div>
      </div>

      {/* Risk Profile */}
      <div className="bg-white rounded-lg p-4 shadow-sm">
        <h3 className="font-medium mb-3 flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 text-warning" />
          Risk Profile
        </h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <RiskBadge label="Cost" value={risk.cost_risk} />
          <RiskBadge label="Latency" value={risk.latency_risk} />
          <RiskBadge label="Scalability" value={risk.scalability_risk} />
          <RiskBadge label="Complexity" value={risk.complexity_risk} />
        </div>
      </div>

      {/* Complexity */}
      <div className="bg-white rounded-lg p-4 shadow-sm">
        <h3 className="font-medium mb-3 flex items-center gap-2">
          <Activity className="w-4 h-4 text-primary" />
          Code Complexity
        </h3>
        <div className="grid grid-cols-3 gap-3">
          <div className="bg-surface p-3 rounded">
            <div className="text-xs text-text-muted">Average</div>
            <div className="text-xl font-bold">{complexity.avg_complexity?.toFixed(1) || 'N/A'}</div>
          </div>
          <div className="bg-surface p-3 rounded">
            <div className="text-xs text-text-muted">Maximum</div>
            <div className="text-xl font-bold">{complexity.max_complexity || 'N/A'}</div>
          </div>
          <div className="bg-surface p-3 rounded">
            <div className="text-xs text-text-muted">Risk Level</div>
            <div className={`text-xl font-bold ${
              complexity.risk_level === 'critical' ? 'text-red-500' :
              complexity.risk_level === 'high' ? 'text-orange-500' :
              complexity.risk_level === 'moderate' ? 'text-warning' : 'text-success'
            }`}>
              {complexity.risk_level || 'N/A'}
            </div>
          </div>
        </div>
      </div>

      {/* Dependencies */}
      {depGraph.external_packages && depGraph.external_packages.length > 0 && (
        <div className="bg-white rounded-lg p-4 shadow-sm">
          <h3 className="font-medium mb-3 flex items-center gap-2">
            <Package className="w-4 h-4 text-primary" />
            Dependencies ({depGraph.external_packages.length})
          </h3>
          <div className="flex flex-wrap gap-1">
            {depGraph.external_packages.slice(0, 20).map((pkg, i) => (
              <span key={i} className="bg-surface text-xs px-2 py-1 rounded">
                {pkg}
              </span>
            ))}
            {depGraph.external_packages.length > 20 && (
              <span className="text-xs text-text-muted">+{depGraph.external_packages.length - 20} more</span>
            )}
          </div>
        </div>
      )}

      {/* Dependency Issues */}
      {(depGraph.has_cycles || (depGraph.layer_violations && depGraph.layer_violations.length > 0)) && (
        <div className="bg-white rounded-lg p-4 shadow-sm">
          <h3 className="font-medium mb-3 flex items-center gap-2">
            <XCircle className="w-4 h-4 text-red-500" />
            Dependency Issues
          </h3>
          <div className="space-y-2">
            {depGraph.has_cycles && (
              <div className="flex items-center gap-2 text-red-500 text-sm">
                <XCircle className="w-4 h-4" />
                Circular dependencies detected
              </div>
            )}
            {depGraph.layer_violations && depGraph.layer_violations.length > 0 && (
              <div className="text-sm">
                <div className="text-warning font-medium mb-1">{depGraph.layer_violations.length} Layer Violations</div>
                {depGraph.layer_violations.slice(0, 3).map((v, i) => (
                  <div key={i} className="text-xs text-text-muted ml-2">
                    {v.source_layer} → {v.target_layer}: {v.violation}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Documentation */}
      <div className="bg-white rounded-lg p-4 shadow-sm">
        <h3 className="font-medium mb-3 flex items-center gap-2">
          <FileText className="w-4 h-4 text-primary" />
          Documentation
        </h3>
        <div className="prose prose-sm max-h-80 overflow-y-auto text-sm text-text-muted whitespace-pre-wrap">
          {results.documentation || results.architecture_summary || 'No documentation generated'}
        </div>
      </div>

      {/* Maturity Factors */}
      {maturity.factors && maturity.factors.length > 0 && (
        <div className="bg-white rounded-lg p-4 shadow-sm">
          <h3 className="font-medium mb-3 flex items-center gap-2">
            <CheckCircle className="w-4 h-4 text-success" />
            Maturity Factors
          </h3>
          <div className="space-y-1">
            {maturity.factors.map((factor, i) => (
              <div key={i} className="text-sm text-text-muted flex items-center gap-2">
                <CheckCircle className="w-3 h-3 text-success" />
                {factor}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

function RiskBadge({ label, value }: { label: string; value: string }) {
  const colors = {
    low: 'bg-green-100 text-green-700',
    moderate: 'bg-yellow-100 text-yellow-700',
    high: 'bg-orange-100 text-orange-700',
    critical: 'bg-red-100 text-red-700',
  }
  const colorClass = colors[value as keyof typeof colors] || 'bg-gray-100 text-gray-700'

  return (
    <div className="text-center">
      <div className="text-xs text-text-muted mb-1">{label}</div>
      <span className={`inline-block px-2 py-1 rounded text-xs font-medium capitalize ${colorClass}`}>
        {value}
      </span>
    </div>
  )
}
