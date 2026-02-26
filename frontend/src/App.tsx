import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import Editor from '@monaco-editor/react'
import axios from 'axios'

type AgentStatus = 'idle' | 'analyzing' | 'planning' | 'running'

interface LogEntry {
  id: number
  message: string
  timestamp: string
}

interface FileNode {
  name: string
  type: 'file' | 'folder'
  children?: FileNode[]
}

interface AnalysisResult {
  project_description: {
    purpose: string
    key_features: string[]
    tech_stack: string[]
  }
  documentation: string
  maturity_score: number
  risk_profile: string
  file_tree: FileNode[]
}

function App() {
  const [repoUrl, setRepoUrl] = useState('')
  const [status, setStatus] = useState<AgentStatus>('idle')
  const [currentStep, setCurrentStep] = useState(0)
  const [totalSteps, setTotalSteps] = useState(5)
  const [logs, setLogs] = useState<LogEntry[]>([])
  const [result, setResult] = useState<AnalysisResult | null>(null)
  const [selectedFile, setSelectedFile] = useState<string | null>(null)
  const [fileContent, setFileContent] = useState<string>('')

  const addLog = (message: string) => {
    const newLog: LogEntry = {
      id: Date.now(),
      message,
      timestamp: new Date().toLocaleTimeString()
    }
    setLogs(prev => [...prev.slice(-4), newLog])
  }

  const simulateAnalysis = async () => {
    if (!repoUrl) return
    
    setStatus('analyzing')
    setResult(null)
    setSelectedFile(null)
    setLogs([])
    
    const steps = [
      'Cloning repository...',
      'Analyzing structure...',
      'Building dependency graph...',
      'Detecting architecture patterns...',
      'Generating documentation...'
    ]
    
    for (let i = 0; i < steps.length; i++) {
      setCurrentStep(i + 1)
      addLog(steps[i])
      await new Promise(r => setTimeout(r, 800))
    }
    
    // Simulate API call
    try {
      const response = await axios.post('http://localhost:8000/workflow/start', {
        repo_url: repoUrl
      }, {
        headers: { 'Content-Type': 'application/json' }
      })
      
      // For demo, use mock data
      setResult({
        project_description: {
          purpose: 'Clean FastAPI backend for student performance analysis via MCP protocol.',
          key_features: ['GET / - API info', 'GET /health - Health check', 'POST /query - Query single student'],
          tech_stack: ['FastAPI', 'GROQ', 'MongoDB']
        },
        documentation: `# Executive Summary\n\nContainerized system. stack: FastAPI, Groq.\n\n## Architectural Maturity\n\n**Score: 7.0 / 10.0**`,
        maturity_score: 7.0,
        risk_profile: 'Moderate cost risk due to external LLM calls',
        file_tree: [
          {
            name: 'src',
            type: 'folder',
            children: [
              { name: 'main.py', type: 'file' },
              { name: 'agent.py', type: 'file' },
              { name: 'mcp_server.py', type: 'file' }
            ]
          },
          {
            name: 'tests',
            type: 'folder',
            children: [
              { name: 'test_api.py', type: 'file' }
            ]
          }
        ]
      })
      
      addLog('Analysis complete!')
    } catch (error) {
      // Use mock data if API fails
      setResult({
        project_description: {
          purpose: 'Clean FastAPI backend for student performance analysis via MCP protocol.',
          key_features: ['GET / - API info', 'GET /health - Health check', 'POST /query - Query single student'],
          tech_stack: ['FastAPI', 'GROQ', 'MongoDB']
        },
        documentation: `# Executive Summary\n\nContainerized system. stack: FastAPI, Groq.\n\n## Architectural Maturity\n\n**Score: 7.0 / 10.0**`,
        maturity_score: 7.0,
        risk_profile: 'Moderate cost risk due to external LLM calls',
        file_tree: [
          {
            name: 'src',
            type: 'folder',
            children: [
              { name: 'main.py', type: 'file' },
              { name: 'agent.py', type: 'file' },
              { name: 'mcp_server.py', type: 'file' }
            ]
          },
          {
            name: 'tests',
            type: 'folder',
            children: [
              { name: 'test_api.py', type: 'file' }
            ]
          }
        ]
      })
      addLog('Analysis complete!')
    }
    
    setStatus('idle')
  }

  const getStatusColor = () => {
    switch (status) {
      case 'analyzing': return '#3B82F6'
      case 'planning': return '#F59E0B'
      case 'running': return '#10B981'
      default: return '#6B7280'
    }
  }

  const renderFileTree = (nodes: FileNode[], level = 0) => {
    return nodes.map((node, idx) => (
      <div key={idx} style={{ paddingLeft: level * 16 }}>
        <motion.div
          initial={{ opacity: 0, x: -10 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: idx * 0.05 }}
          className="flex items-center gap-2 py-1 cursor-pointer hover:text-blue-400"
          onClick={() => {
            if (node.type === 'file') {
              setSelectedFile(node.name)
              setFileContent(`// ${node.name}\n// Sample content for demonstration\n\nfunction example() {\n  return "Hello World";\n}`)
            }
          }}
        >
          <span className="text-lg">{node.type === 'folder' ? '📁' : '📄'}</span>
          <span className="text-sm">{node.name}</span>
        </motion.div>
        {node.children && renderFileTree(node.children, level + 1)}
      </div>
    ))
  }

  return (
    <div className="flex h-screen w-screen bg-[#0F172A]">
      {/* Left Panel - Agent Bar */}
      <div className="w-72 bg-[#0B1220] border-r border-[#1E293B] flex flex-col">
        {/* Top */}
        <div className="p-4 border-b border-[#1E293B]">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center">
              <span className="text-white font-bold text-lg">A</span>
            </div>
            <div>
              <h1 className="text-white font-semibold">APRIS</h1>
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 rounded-full bg-green-500"></div>
                <span className="text-xs text-gray-400">Online</span>
              </div>
            </div>
          </div>
        </div>
        
        {/* Agent Status */}
        <div className="p-4 border-b border-[#1E293B]">
          <div className="bg-[#111827] rounded-lg p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-gray-400 text-sm">Status</span>
              <div className="flex items-center gap-2">
                {status !== 'idle' && (
                  <motion.div
                    animate={{ rotate: 360 }}
                    transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
                    className="w-3 h-3 border-2 border-blue-500 border-t-transparent rounded-full"
                  />
                )}
                <span className="text-sm capitalize" style={{ color: getStatusColor() }}>
                  {status === 'idle' ? 'Idle' : status === 'analyzing' ? 'Analyzing' : 'Working'}
                </span>
              </div>
            </div>
            {status !== 'idle' && (
              <div className="mt-3">
                <div className="flex justify-between text-xs text-gray-500 mb-1">
                  <span>Progress</span>
                  <span>Step {currentStep} of {totalSteps}</span>
                </div>
                <div className="h-1 bg-[#1E293B] rounded-full overflow-hidden">
                  <motion.div
                    className="h-full bg-blue-500"
                    initial={{ width: 0 }}
                    animate={{ width: `${(currentStep / totalSteps) * 100}%` }}
                  />
                </div>
              </div>
            )}
          </div>
        </div>
        
        {/* Logs */}
        <div className="flex-1 p-4 overflow-hidden">
          <h3 className="text-gray-400 text-xs uppercase tracking-wider mb-3">Activity Log</h3>
          <div className="space-y-2">
            <AnimatePresence>
              {logs.map((log) => (
                <motion.div
                  key={log.id}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0 }}
                  className="text-xs p-2 bg-[#111827] rounded"
                >
                  <span className="text-gray-500">[{log.timestamp}]</span>
                  <span className="text-gray-300 ml-2">{log.message}</span>
                </motion.div>
              ))}
            </AnimatePresence>
          </div>
        </div>
        
        {/* Bottom Actions */}
        <div className="p-4 border-t border-[#1E293B]">
          <button
            disabled={status !== 'idle'}
            className={`w-full py-2 rounded-lg text-sm font-medium ${
              status === 'idle'
                ? 'bg-red-500/20 text-red-400 hover:bg-red-500/30'
                : 'bg-gray-700 text-gray-500 cursor-not-allowed'
            }`}
            onClick={() => {
              setStatus('idle')
              setLogs([])
            }}
          >
            Stop
          </button>
        </div>
      </div>
      
      {/* Right Panel - Main Area */}
      <div className="flex-1 flex flex-col bg-[#0F172A]">
        {/* Input Area */}
        <div className="p-6 border-b border-[#1E293B]">
          <div className="max-w-2xl mx-auto">
            <div className="flex gap-3">
              <input
                type="text"
                value={repoUrl}
                onChange={(e) => setRepoUrl(e.target.value)}
                placeholder="Paste repository link here..."
                className="flex-1 px-4 py-3 bg-[#111827] border border-[#1E293B] rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-blue-500 transition-colors"
                onKeyDown={(e) => e.key === 'Enter' && simulateAnalysis()}
              />
              <button
                onClick={simulateAnalysis}
                disabled={!repoUrl || status !== 'idle'}
                className={`px-6 py-3 rounded-lg font-medium transition-all ${
                  repoUrl && status === 'idle'
                    ? 'bg-blue-500 hover:bg-blue-600 text-white'
                    : 'bg-gray-700 text-gray-500 cursor-not-allowed'
                }`}
              >
                Analyze
              </button>
            </div>
          </div>
        </div>
        
        {/* Content Area */}
        <div className="flex-1 overflow-hidden">
          {!result ? (
            /* Loading State */
            <div className="h-full flex items-center justify-center">
              <AnimatePresence>
                {status !== 'idle' && (
                  <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    className="text-center"
                  >
                    <motion.div
                      animate={{ rotate: 360 }}
                      transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
                      className="w-12 h-12 border-2 border-blue-500 border-t-transparent rounded-full mx-auto mb-4"
                    />
                    <p className="text-gray-400">Analyzing repository structure...</p>
                  </motion.div>
                )}
              </AnimatePresence>
              {status === 'idle' && (
                <div className="text-center text-gray-500">
                  <p className="text-4xl mb-4">🔍</p>
                  <p>Enter a GitHub repository URL to begin analysis</p>
                </div>
              )}
            </div>
          ) : (
            /* Results */
            <div className="h-full flex">
              {/* File Tree */}
              <div className="w-64 border-r border-[#1E293B] p-4 overflow-auto">
                <h3 className="text-gray-400 text-xs uppercase tracking-wider mb-4">File Structure</h3>
                {renderFileTree(result.file_tree)}
              </div>
              
              {/* Code Preview / Results */}
              <div className="flex-1 flex flex-col overflow-hidden">
                <AnimatePresence mode="wait">
                  {selectedFile ? (
                    <motion.div
                      key="editor"
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      exit={{ opacity: 0 }}
                      className="flex-1"
                    >
                      <Editor
                        height="100%"
                        language="typescript"
                        theme="vs-dark"
                        value={fileContent}
                        options={{
                          minimap: { enabled: false },
                          fontSize: 13,
                          lineNumbers: 'on',
                          scrollBeyondLastLine: false,
                          readOnly: true
                        }}
                      />
                    </motion.div>
                  ) : (
                    <motion.div
                      key="results"
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      exit={{ opacity: 0 }}
                      className="flex-1 p-6 overflow-auto"
                    >
                      {/* Summary Cards */}
                      <div className="grid grid-cols-3 gap-4 mb-6">
                        <div className="bg-[#111827] rounded-lg p-4">
                          <div className="text-gray-400 text-sm mb-1">Maturity Score</div>
                          <div className="text-3xl font-bold text-blue-400">{result.maturity_score}<span className="text-lg text-gray-500">/10</span></div>
                        </div>
                        <div className="bg-[#111827] rounded-lg p-4">
                          <div className="text-gray-400 text-sm mb-1">Status</div>
                          <div className="text-xl font-semibold text-green-400">Complete</div>
                        </div>
                        <div className="bg-[#111827] rounded-lg p-4">
                          <div className="text-gray-400 text-sm mb-1">Risk Level</div>
                          <div className="text-xl font-semibold text-yellow-400">Moderate</div>
                        </div>
                      </div>
                      
                      {/* Purpose */}
                      <div className="bg-[#111827] rounded-lg p-6 mb-6">
                        <h3 className="text-gray-400 text-xs uppercase tracking-wider mb-3">Project Purpose</h3>
                        <p className="text-white">{result.project_description.purpose}</p>
                      </div>
                      
                      {/* Features */}
                      <div className="bg-[#111827] rounded-lg p-6 mb-6">
                        <h3 className="text-gray-400 text-xs uppercase tracking-wider mb-3">Key Features</h3>
                        <ul className="space-y-2">
                          {result.project_description.key_features.map((feature, idx) => (
                            <li key={idx} className="text-gray-300 flex items-center gap-2">
                              <span className="w-1.5 h-1.5 bg-blue-500 rounded-full"></span>
                              {feature}
                            </li>
                          ))}
                        </ul>
                      </div>
                      
                      {/* Tech Stack */}
                      <div className="bg-[#111827] rounded-lg p-6">
                        <h3 className="text-gray-400 text-xs uppercase tracking-wider mb-3">Tech Stack</h3>
                        <div className="flex gap-2 flex-wrap">
                          {result.project_description.tech_stack.map((tech, idx) => (
                            <span key={idx} className="px-3 py-1 bg-blue-500/20 text-blue-400 rounded-full text-sm">
                              {tech}
                            </span>
                          ))}
                        </div>
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default App
