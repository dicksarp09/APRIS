const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export interface WorkflowStatus {
  workflow_id: string
  status: 'pending' | 'started' | 'in_progress' | 'completed' | 'failed' | 'awaiting_approval'
  current_step: string
  confidence: number
  budget_used: {
    total_budget: number
    spent: number
    node_costs: Record<string, number>
    max_tokens: number
    tokens_used: number
    max_llm_calls: number
    llm_calls_used: number
    max_reflections: number
  }
  reflection_count: number
}

export interface WorkflowResults {
  architecture_summary: string
  documentation: string
  dependency_graph: {
    internal_modules: Record<string, string[]>
    external_packages: string[]
    services: Record<string, string[]>
    density?: number
    has_cycles?: boolean
    layer_violations?: Array<{
      source: string
      target: string
      source_layer: string
      target_layer: string
      violation: string
    }>
  }
  classification: string
  file_count: number
  confidence: number
  primary_language: string
  architecture_score: number
  maturity_score: {
    score: number
    max_score: number
    confidence: number
    factors: string[]
    verdict: string
  }
  complexity_profile: {
    avg_complexity: number
    max_complexity: number
    risk_level: string
  }
  risk_profile: {
    cost_risk: string
    latency_risk: string
    scalability_risk: string
    complexity_risk: string
    overall_risk: number
  }
}

export interface AuditLogEntry {
  node_name: string
  timestamp: string
  status: 'success' | 'failure'
  confidence: number
  error_type?: string
}

export async function startWorkflow(repoUrl: string, userId: string = 'anonymous'): Promise<{ workflow_id: string; status: string }> {
  const response = await fetch(`${API_BASE}/workflow/start`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-User-Id': userId,
    },
    body: JSON.stringify({
      repo_url: repoUrl,
      mode: 'deterministic',
    }),
  })
  
  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Failed to start workflow')
  }
  
  return response.json()
}

export async function getWorkflowStatus(workflowId: string, userId: string = 'anonymous'): Promise<WorkflowStatus> {
  const response = await fetch(`${API_BASE}/workflow/${workflowId}/status`, {
    headers: {
      'X-User-Id': userId,
    },
  })
  
  if (!response.ok) {
    throw new Error('Failed to get workflow status')
  }
  
  return response.json()
}

export async function getWorkflowResults(workflowId: string, userId: string = 'anonymous'): Promise<WorkflowResults> {
  const response = await fetch(`${API_BASE}/workflow/${workflowId}/results`, {
    headers: {
      'X-User-Id': userId,
    },
  })
  
  if (!response.ok) {
    throw new Error('Failed to get workflow results')
  }
  
  return response.json()
}

export async function getWorkflowAudit(workflowId: string, userId: string = 'anonymous'): Promise<{ workflow_id: string; audit_log: AuditLogEntry[] }> {
  const response = await fetch(`${API_BASE}/workflow/${workflowId}/audit`, {
    headers: {
      'X-User-Id': userId,
    },
  })
  
  if (!response.ok) {
    throw new Error('Failed to get audit log')
  }
  
  return response.json()
}

export async function approveWorkflow(workflowId: string, notes: string = '', userId: string = 'anonymous'): Promise<{ success: boolean; status: string }> {
  const response = await fetch(`${API_BASE}/workflow/${workflowId}/approve`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-User-Id': userId,
    },
    body: JSON.stringify({ notes }),
  })
  
  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Failed to approve workflow')
  }
  
  return response.json()
}

export async function listIncompleteWorkflows(userId: string = 'anonymous'): Promise<{ workflows: string[] }> {
  const response = await fetch(`${API_BASE}/workflow`, {
    headers: {
      'X-User-Id': userId,
    },
  })
  
  if (!response.ok) {
    throw new Error('Failed to list workflows')
  }
  
  return response.json()
}
