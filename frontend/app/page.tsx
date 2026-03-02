'use client'

import { useState, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Search, GitBranch, Loader2, AlertCircle, CheckCircle, XCircle, LogOut } from 'lucide-react'
import { WorkflowProvider, useWorkflow } from '@/context/WorkflowContext'
import { StatusCard } from '@/components/StatusCard'
import { ResultsPanel } from '@/components/ResultsPanel'

function HomeContent() {
  const [repoUrl, setRepoUrl] = useState('')
  const { isAnalyzing, error, startAnalysis, status, approve, logs, reset } = useWorkflow()

  const handleAnalyze = useCallback(() => {
    if (!repoUrl) return
    startAnalysis(repoUrl)
  }, [repoUrl, startAnalysis])

  const handleApprove = useCallback(() => {
    approve('Approved via UI')
  }, [approve])

  const getLogStatusColor = (logStatus: string) => {
    switch (logStatus) {
      case 'success': return 'text-green-600'
      case 'error': return 'text-red-500'
      case 'warning': return 'text-yellow-600'
      case 'running': return 'text-blue-500'
      default: return 'text-text-muted'
    }
  }

  return (
    <div className="flex h-screen bg-white">
      {/* Left Sidebar */}
      <aside className="w-[280px] bg-surface-sidebar flex flex-col border-r border-border">
        {/* Top Section */}
        <div className="p-4 border-b border-border">
          <div className="flex items-center gap-2 mb-3">
            <div className="w-8 h-8 bg-primary rounded-lg flex items-center justify-center">
              <GitBranch className="w-5 h-5 text-white" />
            </div>
            <span className="text-lg font-bold text-text-primary">APRIS</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 bg-success rounded-full animate-pulse"></span>
            <span className="text-sm text-text-muted">Online</span>
          </div>
        </div>

        {/* Status Card */}
        <div className="p-4 border-b border-border">
          <StatusCard />
        </div>

        {/* Approval Button */}
        {status?.status === 'awaiting_approval' && (
          <div className="p-4 border-b border-border">
            <button
              onClick={handleApprove}
              disabled={isAnalyzing}
              className="w-full bg-success hover:bg-green-600 disabled:bg-gray-400 text-white font-medium py-2 px-4 rounded-lg flex items-center justify-center gap-2"
            >
              <CheckCircle className="w-4 h-4" />
              Approve to Continue
            </button>
          </div>
        )}

        {/* Mini Log Feed */}
        <div className="flex-1 p-4 overflow-hidden">
          <div className="text-xs font-medium text-text-muted mb-2 uppercase tracking-wider">Agent Log</div>
          <div className="bg-white rounded-lg p-3 h-[180px] overflow-y-auto">
            <AnimatePresence>
              {logs.slice(-6).map((log, index) => (
                <motion.div
                  key={`${log.node}-${index}`}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: index * 0.05 }}
                  className={`text-xs py-1 border-b border-border last:border-0 ${getLogStatusColor(log.status)}`}
                >
                  {log.message}
                </motion.div>
              ))}
              {logs.length === 0 && (
                <div className="text-xs text-text-muted italic">Waiting for input...</div>
              )}
            </AnimatePresence>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="p-4 border-t border-border flex gap-2">
          <button 
            onClick={reset}
            className="flex-1 bg-red-500 hover:bg-red-600 text-white text-sm font-medium py-2 px-3 rounded-lg transition-colors flex items-center justify-center gap-2"
          >
            <LogOut className="w-4 h-4" />
            Reset
          </button>
          <button
            onClick={handleAnalyze}
            disabled={!repoUrl || isAnalyzing}
            className="flex-1 bg-primary hover:bg-blue-600 disabled:bg-blue-300 text-white text-sm font-medium py-2 px-3 rounded-lg transition-colors flex items-center justify-center gap-2"
          >
            {isAnalyzing ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
            {isAnalyzing ? 'Analyzing...' : 'Analyze'}
          </button>
        </div>
      </aside>

      {/* Main Panel */}
      <main className="flex-1 flex flex-col">
        {/* URL Input */}
        <div className="p-4 border-b border-border">
          <div className="flex gap-3 max-w-4xl">
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-text-muted" />
              <input
                type="text"
                value={repoUrl}
                onChange={(e) => setRepoUrl(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleAnalyze()}
                placeholder="Enter GitHub repository URL (e.g., https://github.com/facebook/react)"
                className="w-full pl-10 pr-4 py-3 bg-surface border border-border rounded-lg text-sm text-text-primary placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
              />
            </div>
            <button
              onClick={handleAnalyze}
              disabled={!repoUrl || isAnalyzing}
              className="bg-primary hover:bg-blue-600 disabled:bg-blue-300 text-white font-medium py-3 px-6 rounded-lg transition-colors flex items-center gap-2"
            >
              <Search className="w-4 h-4" />
              Analyze
            </button>
          </div>
          {error && (
            <motion.div 
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              className="mt-2 flex items-center gap-2 text-sm text-red-500"
            >
              <AlertCircle className="w-4 h-4" />
              {error}
            </motion.div>
          )}
        </div>

        {/* Results */}
        <div className="flex-1 overflow-auto bg-surface">
          <AnimatePresence mode="wait">
            {status?.status === 'completed' ? (
              <motion.div
                key="results"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
              >
                <ResultsPanel />
              </motion.div>
            ) : status?.status === 'failed' ? (
              <motion.div 
                key="error"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="flex flex-col items-center justify-center h-full p-8"
              >
                <XCircle className="w-16 h-16 text-red-500 mb-4" />
                <p className="text-lg font-medium text-text-primary">Analysis Failed</p>
                <p className="text-sm text-text-muted mt-1">Please try again or check the repository URL</p>
              </motion.div>
            ) : isAnalyzing ? (
              <motion.div 
                key="loading"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="flex flex-col items-center justify-center h-full p-8"
              >
                <motion.div
                  animate={{ rotate: 360 }}
                  transition={{ repeat: Infinity, duration: 1.5, ease: "linear" }}
                  className="w-12 h-12 border-4 border-primary border-t-transparent rounded-full mb-4"
                />
                <p className="text-lg font-medium text-text-primary">Agent working...</p>
                <p className="text-sm text-text-muted mt-1">Analyzing repository structure</p>
              </motion.div>
            ) : (
              <motion.div 
                key="empty"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="flex flex-col items-center justify-center h-full p-8"
              >
                <GitBranch className="w-16 h-16 text-border mb-4" />
                <p className="text-lg font-medium text-text-primary">Enter a GitHub repository URL</p>
                <p className="text-sm text-text-muted mt-1">APRIS will analyze the repository and generate documentation</p>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </main>
    </div>
  )
}

export default function Home() {
  return (
    <WorkflowProvider>
      <HomeContent />
    </WorkflowProvider>
  )
}
