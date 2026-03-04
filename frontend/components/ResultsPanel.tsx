'use client'

import { motion } from 'framer-motion'
import { useWorkflow } from '@/context/WorkflowContext'
import { 
  FileText, GitBranch, Package, CheckCircle, AlertTriangle, XCircle, 
  Layers, Activity, ChevronDown, ChevronRight, Copy, Check 
} from 'lucide-react'
import { useState } from 'react'

export function ResultsPanel() {
  const { results, status } = useWorkflow()
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set(['overview', 'features', 'tech', 'risk', 'complexity', 'files']))

  if (!results || status?.status !== 'completed') {
    return null
  }

  const depGraph = results.dependency_graph || {}
  const maturity = results.maturity_score || {}
  const complexity = results.complexity_profile || {}
  const risk = results.risk_profile || {}

  const toggleSection = (section: string) => {
    setExpandedSections(prev => {
      const next = new Set(prev)
      if (next.has(section)) {
        next.delete(section)
      } else {
        next.add(section)
      }
      return next
    })
  }

  const doc = results.documentation || results.architecture_summary || ''

  return (
    <div className="p-4 space-y-4">
      {/* Header Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div className="bg-white rounded-xl p-4 shadow-sm border border-border">
          <div className="flex items-center gap-2 mb-1">
            <GitBranch className="w-4 h-4 text-primary" />
            <span className="text-xs font-medium text-gray-500">Classification</span>
          </div>
          <div className="text-xl font-bold text-primary">{results.classification}</div>
          <div className="text-xs text-gray-400">{results.primary_language}</div>
        </div>

        <div className="bg-white rounded-xl p-4 shadow-sm border border-border">
          <div className="flex items-center gap-2 mb-1">
            <Package className="w-4 h-4 text-primary" />
            <span className="text-xs font-medium text-gray-500">Files</span>
          </div>
          <div className="text-xl font-bold">{results.file_count}</div>
          <div className="text-xs text-gray-400">analyzed</div>
        </div>

        <div className="bg-white rounded-xl p-4 shadow-sm border border-border">
          <div className="flex items-center gap-2 mb-1">
            <Activity className="w-4 h-4 text-primary" />
            <span className="text-xs font-medium text-gray-500">Architecture</span>
          </div>
          <div className="text-xl font-bold">{results.architecture_score.toFixed(1)}</div>
          <div className="text-xs text-gray-400">/ 10</div>
        </div>

        <div className="bg-white rounded-xl p-4 shadow-sm border border-border">
          <div className="flex items-center gap-2 mb-1">
            <Layers className="w-4 h-4 text-primary" />
            <span className="text-xs font-medium text-gray-500">Maturity</span>
          </div>
          <div className="text-xl font-bold">{maturity.score?.toFixed(1) || 'N/A'}</div>
          <div className="text-xs text-gray-400">{maturity.verdict || ''}</div>
        </div>
      </div>

      {/* Risk Profile */}
      <div className="bg-white rounded-xl p-4 shadow-sm border border-border">
        <h3 className="font-semibold mb-3 flex items-center gap-2 text-gray-800">
          <AlertTriangle className="w-4 h-4 text-amber-500" />
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
      <div className="bg-white rounded-xl p-4 shadow-sm border border-border">
        <h3 className="font-semibold mb-3 flex items-center gap-2 text-gray-800">
          <Activity className="w-4 h-4 text-primary" />
          Code Complexity
        </h3>
        <div className="grid grid-cols-3 gap-3">
          <div className="bg-gray-3 rounded-lg-50 p">
            <div className="text-xs font-medium text-gray-500">Average</div>
            <div className="text-2xl font-bold text-gray-800">{complexity.avg_complexity?.toFixed(1) || 'N/A'}</div>
          </div>
          <div className="bg-gray-50 p-3 rounded-lg">
            <div className="text-xs font-medium text-gray-500">Maximum</div>
            <div className="text-2xl font-bold text-gray-800">{complexity.max_complexity || 'N/A'}</div>
          </div>
          <div className="bg-gray-50 p-3 rounded-lg">
            <div className="text-xs font-medium text-gray-500">Risk Level</div>
            <div className={`text-2xl font-bold ${
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
        <div className="bg-white rounded-xl p-4 shadow-sm border border-border">
          <h3 className="font-semibold mb-3 flex items-center gap-2 text-gray-800">
            <Package className="w-4 h-4 text-primary" />
            Dependencies ({depGraph.external_packages.length})
          </h3>
          <div className="flex flex-wrap gap-2">
            {depGraph.external_packages.slice(0, 20).map((pkg, i) => (
              <span key={i} className="bg-gray-100 text-gray-700 text-xs px-3 py-1.5 rounded-full font-medium">
                {pkg}
              </span>
            ))}
            {depGraph.external_packages.length > 20 && (
              <span className="text-xs text-gray-500">+{depGraph.external_packages.length - 20} more</span>
            )}
          </div>
        </div>
      )}

      {/* Documentation - Rendered Properly */}
      {doc && (
        <DocumentationRenderer content={doc} />
      )}

      {/* Maturity Factors */}
      {maturity.factors && maturity.factors.length > 0 && (
        <div className="bg-white rounded-xl p-4 shadow-sm border border-border">
          <h3 className="font-semibold mb-3 flex items-center gap-2 text-gray-800">
            <CheckCircle className="w-4 h-4 text-green-500" />
            Maturity Factors
          </h3>
          <div className="space-y-2">
            {maturity.factors.map((factor, i) => (
              <div key={i} className="flex items-start gap-2 text-sm text-gray-600">
                <CheckCircle className="w-4 h-4 text-green-500 mt-0.5 flex-shrink-0" />
                <span>{factor.replace(/[+()]/g, '').trim()}</span>
              </div>
            ))}
          </div>
        </div>
      )}
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
      // Bold **text**
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

      // Headers
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
      } 
      // List items
      else if (line.startsWith('- ') || line.startsWith('* ')) {
        flushList()
        if (listType !== 'ul') {
          flushList()
          listType = 'ul'
        }
        currentList.push(line.slice(2))
      }
      else if (/^\d+\.\s/.test(line)) {
        flushList()
        if (listType !== 'ol') {
          flushList()
          listType = 'ol'
        }
        currentList.push(line.replace(/^\d+\.\s/, ''))
      }
      // Blockquotes (>)
      else if (line.startsWith('> ')) {
        flushList()
        elements.push(
          <blockquote key={i} className="border-l-4 border-primary pl-4 my-3 text-gray-600 italic bg-gray-50 py-2 pr-2 rounded-r">
            {formatInline(line.slice(2))}
          </blockquote>
        )
      }
      // Regular paragraph
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
    <div className="bg-white rounded-xl shadow-sm border border-border overflow-hidden">
      <div className="flex items-center justify-between px-4 py-3 bg-gray-50 border-b border-gray-200">
        <h3 className="font-semibold flex items-center gap-2 text-gray-800">
          <FileText className="w-4 h-4 text-primary" />
          Full Documentation
        </h3>
        <button
          onClick={copyToClipboard}
          className="flex items-center gap-1.5 text-xs text-gray-500 hover:text-gray-700 transition-colors"
        >
          {copied ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
          {copied ? 'Copied!' : 'Copy'}
        </button>
      </div>
      <div className="p-4 max-h-[500px] overflow-y-auto">
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
    <div className="text-center p-2 bg-gray-50 rounded-lg">
      <div className="text-xs font-medium text-gray-500 mb-1">{label}</div>
      <span className={`inline-block px-3 py-1 rounded-full text-xs font-semibold capitalize ${colorClass}`}>
        {value}
      </span>
    </div>
  )
}
