'use client'

import { motion } from 'framer-motion'
import { Loader2, CheckCircle2, XCircle, AlertTriangle, Clock, Zap, DollarSign, Brain } from 'lucide-react'
import { useWorkflow } from '@/context/WorkflowContext'

export function StatusCard() {
  const { status, isAnalyzing, error } = useWorkflow()
  
  const getStatusIcon = () => {
    if (isAnalyzing) {
      return <Loader2 className="w-5 h-5 text-primary animate-spin" />
    }
    if (error) {
      return <XCircle className="w-5 h-5 text-red-500" />
    }
    if (status?.status === 'completed') {
      return <CheckCircle2 className="w-5 h-5 text-success" />
    }
    if (status?.status === 'awaiting_approval') {
      return <AlertTriangle className="w-5 h-5 text-warning" />
    }
    if (status?.status === 'failed') {
      return <XCircle className="w-5 h-5 text-red-500" />
    }
    return <Clock className="w-5 h-5 text-text-muted" />
  }
  
  const getStatusText = () => {
    if (isAnalyzing) return 'Analyzing repository...'
    if (error) return 'Error occurred'
    if (status?.status === 'completed') return 'Analysis complete'
    if (status?.status === 'awaiting_approval') return 'Awaiting approval'
    if (status?.status === 'failed') return 'Analysis failed'
    return 'Ready'
  }

  const getProgress = () => {
    if (!status) return 0
    const stepMap: Record<string, number> = {
      'pending': 0,
      'started': 5,
      'CloneRepo': 10,
      'ProfileRepo': 20,
      'ClassifyRepo': 30,
      'SafetyScan': 40,
      'ParseFiles': 50,
      'SummarizeFiles': 60,
      'ContentAnalysis': 70,
      'BuildDependencyGraph': 80,
      'ArchitectureSynthesis': 90,
      'DocumentationGeneration': 95,
    }
    return stepMap[status.status] || stepMap[status.current_step] || 0
  }

  const budget = status?.budget_used

  return (
    <div className="bg-white rounded-lg p-4 shadow-sm">
      <div className="flex items-center gap-3 mb-3">
        {getStatusIcon()}
        <span className="text-sm font-medium">{getStatusText()}</span>
      </div>
      
      {status && (
        <div className="space-y-2">
          <div className="flex justify-between text-xs text-text-muted">
            <span>Progress</span>
            <span>{getProgress()}%</span>
          </div>
          <div className="h-1.5 bg-surface rounded-full overflow-hidden">
            <motion.div 
              className="h-full bg-primary rounded-full"
              initial={{ width: 0 }}
              animate={{ width: `${getProgress()}%` }}
              transition={{ duration: 0.3 }}
            />
          </div>
          
          {currentStepLabel(status.current_step) && (
            <div className="text-xs text-primary mt-2">
              {currentStepLabel(status.current_step)}
            </div>
          )}
          
          {budget && (
            <div className="grid grid-cols-3 gap-2 mt-3">
              <div className="bg-surface p-2 rounded">
                <div className="flex items-center gap-1 text-text-muted">
                  <Brain className="w-3 h-3" />
                  <span className="text-[10px]">LLM</span>
                </div>
                <div className="font-medium text-sm">
                  {budget.llm_calls_used}/{budget.max_llm_calls}
                </div>
              </div>
              <div className="bg-surface p-2 rounded">
                <div className="flex items-center gap-1 text-text-muted">
                  <Zap className="w-3 h-3" />
                  <span className="text-[10px]">Tokens</span>
                </div>
                <div className="font-medium text-sm">
                  {budget.tokens_used.toLocaleString()}/{budget.max_tokens.toLocaleString()}
                </div>
              </div>
              <div className="bg-surface p-2 rounded">
                <div className="flex items-center gap-1 text-text-muted">
                  <DollarSign className="w-3 h-3" />
                  <span className="text-[10px]">Refl.</span>
                </div>
                <div className="font-medium text-sm">
                  {status.reflection_count}/{budget.max_reflections}
                </div>
              </div>
            </div>
          )}
          
          {status.confidence > 0 && (
            <div className="text-xs text-text-muted mt-2">
              Confidence: {(status.confidence * 100).toFixed(0)}%
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function currentStepLabel(step: string): string {
  const labels: Record<string, string> = {
    'CloneRepo': 'Cloning repository',
    'ProfileRepo': 'Profiling repository',
    'ClassifyRepo': 'Classifying repository',
    'SafetyScan': 'Scanning for safety',
    'ParseFiles': 'Parsing files',
    'SummarizeFiles': 'Summarizing files',
    'ContentAnalysis': 'Analyzing content',
    'BuildDependencyGraph': 'Building dependency graph',
    'ArchitectureSynthesis': 'Synthesizing architecture',
    'DocumentationGeneration': 'Generating documentation',
  }
  return labels[step] || ''
}
