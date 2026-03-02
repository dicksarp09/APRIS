'use client'

import React, { createContext, useContext, useState, useCallback, useRef } from 'react'
import { 
  startWorkflow, 
  getWorkflowStatus, 
  getWorkflowResults,
  getWorkflowAudit,
  approveWorkflow,
  WorkflowStatus,
  WorkflowResults 
} from '@/lib/api'

interface LogEntry {
  node: string
  message: string
  status: 'info' | 'running' | 'success' | 'error' | 'warning'
}

interface WorkflowState {
  workflowId: string | null
  status: WorkflowStatus | null
  results: WorkflowResults | null
  logs: LogEntry[]
  isAnalyzing: boolean
  error: string | null
}

interface WorkflowContextType extends WorkflowState {
  startAnalysis: (repoUrl: string, analysisMode?: string) => Promise<void>
  checkStatus: () => Promise<void>
  approve: (notes?: string) => Promise<void>
  reset: () => void
}

const WorkflowContext = createContext<WorkflowContextType | null>(null)

export function WorkflowProvider({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<WorkflowState>({
    workflowId: null,
    status: null,
    results: null,
    logs: [],
    isAnalyzing: false,
    error: null,
  })

  const pollTimerRef = useRef<NodeJS.Timeout | null>(null)

  const pollStatus = useCallback(async (workflowId: string) => {
    try {
      const status = await getWorkflowStatus(workflowId)
      setState(prev => ({ ...prev, status }))
      
      if (status.status === 'in_progress' || status.status === 'started' || status.status === 'pending') {
        setState(prev => ({
          ...prev,
          logs: [...prev.logs, { 
            node: status.current_step || 'system', 
            message: `Executing: ${status.current_step || 'processing'}`, 
            status: 'running' 
          }]
        }))
        
        pollTimerRef.current = setTimeout(() => pollStatus(workflowId), 3000)
        return
      }
      
      if (status.status === 'completed') {
        try {
          const results = await getWorkflowResults(workflowId)
          const audit = await getWorkflowAudit(workflowId)
          setState(prev => ({ 
            ...prev, 
            results, 
            isAnalyzing: false,
            logs: [...prev.logs, { node: 'system', message: 'Analysis complete!', status: 'success' }]
          }))
        } catch {
          setState(prev => ({ 
            ...prev, 
            isAnalyzing: false,
            logs: [...prev.logs, { node: 'system', message: 'Analysis complete (results unavailable)', status: 'success' }]
          }))
        }
        return
      }
      
      if (status.status === 'failed') {
        setState(prev => ({ 
          ...prev, 
          isAnalyzing: false,
          error: 'Workflow failed',
          logs: [...prev.logs, { node: 'system', message: 'Workflow failed', status: 'error' }]
        }))
        return
      }
      
      if (status.status === 'awaiting_approval') {
        setState(prev => ({
          ...prev,
          isAnalyzing: false,
          logs: [...prev.logs, { node: 'system', message: 'Awaiting approval', status: 'warning' }]
        }))
        return
      }
      
    } catch (error) {
      console.error('Poll error:', error)
      pollTimerRef.current = setTimeout(() => pollStatus(workflowId), 5000)
    }
  }, [])

  const startAnalysis = useCallback(async (repoUrl: string, analysisMode: string = 'shallow') => {
    if (pollTimerRef.current) {
      clearTimeout(pollTimerRef.current)
    }
    
    setState(prev => ({ ...prev, isAnalyzing: true, error: null, logs: [], results: null, status: null }))
    
    try {
      const { workflow_id, status: workflowStatus } = await startWorkflow(repoUrl, 'anonymous', analysisMode, 20)
      setState(prev => ({ 
        ...prev, 
        workflowId: workflow_id,
        logs: [{ node: 'system', message: `Workflow started: ${workflowStatus} (${analysisMode} mode)`, status: 'info' }]
      }))
      
      pollStatus(workflow_id)
      
    } catch (error) {
      setState(prev => ({ 
        ...prev, 
        isAnalyzing: false, 
        error: error instanceof Error ? error.message : 'Unknown error',
        logs: [...prev.logs, { node: 'system', message: error instanceof Error ? error.message : 'Failed to start', status: 'error' }]
      }))
    }
  }, [pollStatus])

  const checkStatus = useCallback(async () => {
    if (!state.workflowId) return
    await pollStatus(state.workflowId)
  }, [state.workflowId, pollStatus])

  const approve = useCallback(async (notes: string = '') => {
    if (!state.workflowId) return
    
    setState(prev => ({ ...prev, isAnalyzing: true }))
    
    try {
      await approveWorkflow(state.workflowId, notes)
      pollStatus(state.workflowId)
    } catch (error) {
      setState(prev => ({ 
        ...prev, 
        isAnalyzing: false, 
        error: error instanceof Error ? error.message : 'Failed to approve'
      }))
    }
  }, [state.workflowId, pollStatus])

  const reset = useCallback(() => {
    if (pollTimerRef.current) {
      clearTimeout(pollTimerRef.current)
    }
    setState({
      workflowId: null,
      status: null,
      results: null,
      logs: [],
      isAnalyzing: false,
      error: null,
    })
  }, [])

  return (
    <WorkflowContext.Provider value={{ ...state, startAnalysis, checkStatus, approve, reset }}>
      {children}
    </WorkflowContext.Provider>
  )
}

export function useWorkflow() {
  const context = useContext(WorkflowContext)
  if (!context) {
    throw new Error('useWorkflow must be used within WorkflowProvider')
  }
  return context
}
