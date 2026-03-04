'use client'

import { motion } from 'framer-motion'
import { useWorkflow } from '@/context/WorkflowContext'
import { 
  FileText, GitBranch, Package, CheckCircle, AlertTriangle, XCircle, 
  Layers, Activity, Copy, Check 
} from 'lucide-react'
import { useState } from 'react'

export function ResultsPanel() {
  const { results, status } = useWorkflow()

  if (!results || status?.status !== 'completed') {
    return null
  }

  const depGraph = results.dependency_graph || {}
  const maturity = results.maturity_score || {}
  const complexity = results.complexity_profile || {}
  const risk = results.risk_profile || {}

  const doc = results.documentation || results.architecture_summary || ''

  return (
    <div className="flex h-full">
      {/* Main Documentation Area */}
      <div className="flex-1 p-4 overflow-hidden">
        {doc && (
          <DocumentationRenderer content={doc} />
        )}
      </div>

      {/* Right Sidebar - Quick Stats */}
      <div className="w-72 bg-white border-l border-border overflow-y-auto p-4 space-y-4">
        {/* Classification */}
        <div className="bg-gray-50 rounded-lg p-3">
          <div className="flex items-center gap-2 mb-1">
            <GitBranch className="w-3.5 h-3.5 text-primary" />
            <span className="text-xs font-medium text-gray-500">Classification</span>
          </div>
          <div className="text-lg font-bold text-primary">{results.classification}</div>
          <div className="text-xs text-gray-400">{results.primary_language}</div>
        </div>

        {/* Files */}
        <div className="bg-gray-50 rounded-lg p-3">
          <div className="flex items-center gap-2 mb-1">
            <Package className="w-3.5 h-3.5 text-primary" />
            <span className="text-xs font-medium text-gray-500">Files</span>
          </div>
          <div className="text-lg font-bold">{results.file_count}</div>
          <div className="text-xs text-gray-400">analyzed</div>
        </div>

        {/* Architecture */}
        <div className="bg-gray-50 rounded-lg p-3">
          <div className="flex items-center gap-2 mb-1">
            <Activity className="w-3.5 h-3.5 text-primary" />
            <span className="text-xs font-medium text-gray-500">Architecture</span>
          </div>
          <div className="text-lg font-bold">{results.architecture_score.toFixed(1)}</div>
          <div className="text-xs text-gray-400">/ 10</div>
        </div>

        {/* Maturity */}
        <div className="bg-gray-50 rounded-lg p-3">
          <div className="flex items-center gap-2 mb-1">
            <Layers className="w-3.5 h-3.5 text-primary" />
            <span className="text-xs font-medium text-gray-500">Maturity</span>
          </div>
          <div className="text-lg font-bold">{maturity.score?.toFixed(1) || 'N/A'}</div>
          <div className="text-xs text-gray-400">{maturity.verdict || ''}</div>
        </div>

        {/* Risk Profile */}
        <div className="bg-gray-50 rounded-lg p-3">
          <div className="flex items-center gap-2 mb-2">
            <AlertTriangle className="w-3.5 h-3.5 text-amber-500" />
            <span className="text-xs font-medium text-gray-500">Risk Profile</span>
          </div>
          <div className="grid grid-cols-2 gap-2">
            <RiskBadge label="Cost" value={risk.cost_risk} />
            <RiskBadge label="Latency" value={risk.latency_risk} />
            <RiskBadge label="Scalability" value={risk.scalability_risk} />
            <RiskBadge label="Complexity" value={risk.complexity_risk} />
          </div>
        </div>

        {/* Code Complexity */}
        <div className="bg-gray-50 rounded-lg p-3">
          <div className="flex items-center gap-2 mb-2">
            <Activity className="w-3.5 h-3.5 text-primary" />
            <span className="text-xs font-medium text-gray-500">Code Complexity</span>
          </div>
          <div className="grid grid-cols-3 gap-2 text-center">
            <div>
              <div className="text-xs text-gray-400">Avg</div>
              <div className="font-bold text-gray-800">{complexity.avg_complexity?.toFixed(1) || 'N/A'}</div>
            </div>
            <div>
              <div className="text-xs text-gray-400">Max</div>
              <div className="font-bold text-gray-800">{complexity.max_complexity || 'N/A'}</div>
            </div>
            <div>
              <div className="text-xs text-gray-400">Risk</div>
              <div className={`font-bold text-xs ${
                complexity.risk_level === 'critical' ? 'text-red-600' :
                complexity.risk_level === 'high' ? 'text-orange-500' :
                complexity.risk_level === 'moderate' ? 'text-amber-500' : 'text-green-500'
              }`}>
                {complexity.risk_level || 'N/A'}
              </div>
            </div>
          </div>
        </div>

        {/* Dependencies */}
        {depGraph.external_packages && depGraph.external_packages.length > 0 && (
          <div className="bg-gray-50 rounded-lg p-3">
            <div className="flex items-center gap-2 mb-2">
              <Package className="w-3.5 h-3.5 text-primary" />
              <span className="text-xs font-medium text-gray-500">Dependencies ({depGraph.external_packages.length})</span>
            </div>
            <div className="flex flex-wrap gap-1 max-h-32 overflow-y-auto">
              {depGraph.external_packages.slice(0, 20).map((pkg, i) => (
                <span key={i} className="bg-white text-gray-600 text-xs px-2 py-0.5 rounded border border-gray-200">
                  {pkg}
                </span>
              ))}
              {depGraph.external_packages.length > 20 && (
                <span className="text-xs text-gray-400">+{depGraph.external_packages.length - 20} more</span>
              )}
            </div>
          </div>
        )}

        {/* Dependency Issues */}
        {(depGraph.has_cycles || (depGraph.layer_violations && depGraph.layer_violations.length > 0)) && (
          <div className="bg-red-50 rounded-lg p-3 border border-red-200">
            <div className="flex items-center gap-2 mb-2">
              <XCircle className="w-3.5 h-3.5 text-red-500" />
              <span className="text-xs font-medium text-red-700">Issues</span>
            </div>
            {depGraph.has_cycles && (
              <div className="text-xs text-red-600">Circular dependencies</div>
            )}
            {depGraph.layer_violations && depGraph.layer_violations.length > 0 && (
              <div className="text-xs text-red-600">{depGraph.layer_violations.length} layer violations</div>
            )}
          </div>
        )}

        {/* Maturity Factors */}
        {maturity.factors && maturity.factors.length > 0 && (
          <div className="bg-gray-50 rounded-lg p-3">
            <div className="flex items-center gap-2 mb-2">
              <CheckCircle className="w-3.5 h-3.5 text-green-500" />
              <span className="text-xs font-medium text-gray-500">Maturity Factors</span>
            </div>
            <div className="space-y-1 max-h-24 overflow-y-auto">
              {maturity.factors.slice(0, 5).map((factor, i) => (
                <div key={i} className="text-xs text-gray-600 flex items-start gap-1">
                  <CheckCircle className="w-3 h-3 text-green-500 mt-0.5 flex-shrink-0" />
                  <span>{factor.replace(/[+()]/g, '').trim()}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

function DocumentationRenderer({ content }: { content: string }) {
  const [copied, setCopied] = useState(false)

  const copyToClipboard = () => {
    navigator.clipboard.writeText(content)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const renderContent = () => {
    const lines = content.split('\n')
    const elements: JSX.Element[] = []
    let currentList: string[] = []
    let listType: 'ul' | 'ol' | null = null

    const flushList = () => {
      if (currentList.length > 0) {
        if (listType === 'ul') {
          elements.push(
            <ul key={`ul-${elements.length}`} className="list-disc list-inside space-y-1 my-2">
              {currentList.map((item, i) => (
                <li key={i} className="text-gray-700">{formatInline(item)}</li>
              ))}
            </ul>
          )
        } else {
          elements.push(
            <ol key={`ol-${elements.length}`} className="list-decimal list-inside space-y-1 my-2">
              {currentList.map((item, i) => (
                <li key={i} className="text-gray-700">{formatInline(item)}</li>
              ))}
            </ol>
          )
        }
        currentList = []
        listType = null
      }
    }

    const formatInline = (text: string): JSX.Element => {
      const parts = text.split(/(\*\*[^*]+\*\*)/g)
      return (
        <>
          {parts.map((part, i) => {
            if (part.startsWith('**') && part.endsWith('**')) {
              return <strong key={i} className="font-bold text-gray-900">{part.slice(2, -2)}</strong>
            }
            return <span key={i}>{part}</span>
          })}
        </>
      )
    }

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i].trim()
      
      if (!line) {
        flushList()
        continue
      }

      if (line.startsWith('## ')) {
        flushList()
        elements.push(
          <h2 key={i} className="text-lg font-bold text-gray-900 mt-6 mb-3 pb-2 border-b border-gray-200">
            {line.slice(3)}
          </h2>
        )
      } else if (line.startsWith('### ')) {
        flushList()
        elements.push(
          <h3 key={i} className="text-md font-semibold text-gray-800 mt-4 mb-2">
            {line.slice(4)}
          </h3>
        )
      } else if (line.startsWith('# ')) {
        flushList()
        elements.push(
          <h1 key={i} className="text-xl font-bold text-gray-900 mt-6 mb-4">
            {line.slice(2)}
          </h1>
        )
      } else if (line.startsWith('- ') || line.startsWith('* ')) {
        if (listType !== 'ul') {
          flushList()
          listType = 'ul'
        }
        currentList.push(line.slice(2))
      }
      else if (/^\d+\.\s/.test(line)) {
        if (listType !== 'ol') {
          flushList()
          listType = 'ol'
        }
        currentList.push(line.replace(/^\d+\.\s/, ''))
      }
      else if (line.startsWith('> ')) {
        flushList()
        elements.push(
          <blockquote key={i} className="border-l-4 border-primary pl-4 my-3 text-gray-600 italic bg-gray-50 py-2 pr-2 rounded-r">
            {formatInline(line.slice(2))}
          </blockquote>
        )
      }
      else {
        flushList()
        elements.push(
          <p key={i} className="text-gray-700 my-2 leading-relaxed">
            {formatInline(line)}
          </p>
        )
      }
    }

    flushList()
    return elements
  }

  return (
    <div className="bg-white rounded-xl shadow-sm border border-border h-full flex flex-col">
      <div className="flex items-center justify-between px-4 py-3 bg-gray-50 border-b border-gray-200">
        <h3 className="font-semibold flex items-center gap-2 text-gray-800">
          <FileText className="w-4 h-4 text-primary" />
          Documentation
        </h3>
        <button
          onClick={copyToClipboard}
          className="flex items-center gap-1.5 text-xs text-gray-500 hover:text-gray-700 transition-colors"
        >
          {copied ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
          {copied ? 'Copied!' : 'Copy'}
        </button>
      </div>
      <div className="p-4 flex-1 overflow-y-auto">
        {renderContent()}
      </div>
    </div>
  )
}

function RiskBadge({ label, value }: { label: string; value: string }) {
  const colors: Record<string, string> = {
    low: 'bg-green-100 text-green-700',
    moderate: 'bg-yellow-100 text-yellow-700',
    high: 'bg-orange-100 text-orange-700',
    critical: 'bg-red-100 text-red-700',
  }
  const colorClass = colors[value] || 'bg-gray-100 text-gray-700'

  return (
    <div className="text-center">
      <div className="text-[10px] text-gray-400">{label}</div>
      <span className={`inline-block px-2 py-0.5 rounded text-xs font-semibold capitalize ${colorClass}`}>
        {value}
      </span>
    </div>
  )
}
