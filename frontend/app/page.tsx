'use client'

import { useState, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { 
  Search, 
  Folder, 
  FileCode, 
  FileText, 
  File, 
  Database,
  GitBranch,
  CheckCircle2,
  XCircle,
  RotateCcw,
  Loader2,
  ChevronRight,
  ChevronDown,
  AlertCircle
} from 'lucide-react'
import { Highlight, themes } from 'prism-react-renderer'

interface LogEntry {
  id: number
  message: string
}

interface FileNode {
  name: string
  path: string
  type: 'file' | 'folder'
  children?: FileNode[]
  content?: string
}

export default function Home() {
  const [repoUrl, setRepoUrl] = useState('')
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [logs, setLogs] = useState<LogEntry[]>([])
  const [currentStep, setCurrentStep] = useState(0)
  const [files, setFiles] = useState<FileNode[]>([])
  const [selectedFile, setSelectedFile] = useState<string | null>(null)
  const [fileContent, setFileContent] = useState<string>('')
  const [error, setError] = useState<string | null>(null)
  const [expandedFolders, setExpandedFolders] = useState<Set<string>>(new Set())

  const addLog = useCallback((message: string) => {
    setLogs(prev => [...prev, { id: Date.now(), message }])
  }, [])

  const simulateAnalysis = useCallback(async () => {
    if (!repoUrl) return
    
    setIsAnalyzing(true)
    setError(null)
    setFiles([])
    setSelectedFile(null)
    setFileContent('')
    setLogs([])
    setCurrentStep(0)
    setExpandedFolders(new Set())

    const steps = [
      { step: 1, msg: 'Validating repository URL...' },
      { step: 1, msg: 'INFO: Checking repository accessibility' },
      { step: 1, msg: 'SUCCESS: Repository is accessible' },
      { step: 2, msg: 'Cloning repository to sandbox...' },
      { step: 2, msg: 'INFO: Analyzing repository structure' },
      { step: 2, msg: 'Found 47 files in repository' },
      { step: 3, msg: 'Classifying repository type...' },
      { step: 3, msg: 'DETECTED: JavaScript/TypeScript Project' },
      { step: 4, msg: 'Analyzing file dependencies...' },
      { step: 4, msg: 'INFO: Processing configuration files' },
      { step: 4, msg: 'Found 12 dependency declarations' },
      { step: 5, msg: 'Generating documentation...' },
      { step: 5, msg: 'SUCCESS: Analysis complete' },
    ]

    for (const { step, msg } of steps) {
      await new Promise(resolve => setTimeout(resolve, 600 + Math.random() * 400))
      setCurrentStep(step)
      addLog(msg)
    }

    const mockFiles: FileNode[] = [
      {
        name: 'src',
        path: 'src',
        type: 'folder',
        children: [
          { name: 'components', path: 'src/components', type: 'folder', children: [
            { name: 'Button.tsx', path: 'src/components/Button.tsx', type: 'file', content: "import React from 'react';\n\ninterface ButtonProps {\n  children: React.ReactNode;\n  onClick?: () => void;\n  variant?: 'primary' | 'secondary';\n}\n\nexport const Button: React.FC<ButtonProps> = ({ \n  children, \n  onClick, \n  variant = 'primary' \n}) => {\n  return (\n    <button \n      className={`btn btn-${variant}`}\n      onClick={onClick}\n    >\n      {children}\n    </button>\n  );\n};" },
            { name: 'Card.tsx', path: 'src/components/Card.tsx', type: 'file', content: "import React from 'react';\n\nexport const Card: React.FC<{ children: React.ReactNode }> = ({ children }) => {\n  return (\n    <div className=\"card\">\n      {children}\n    </div>\n  );\n};" },
            { name: 'Input.tsx', path: 'src/components/Input.tsx', type: 'file', content: "import React, { forwardRef } from 'react';\n\ninterface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {}\n\nexport const Input = forwardRef<HTMLInputElement, InputProps>(\n  ({ className, ...props }, ref) => {\n    return (\n      <input \n        ref={ref}\n        className={`input ${className || ''}`}\n        {...props} \n      />\n    );\n  }\n);\n\nInput.displayName = 'Input';" },
          ]},
          { name: 'hooks', path: 'src/hooks', type: 'folder', children: [
            { name: 'useAuth.ts', path: 'src/hooks/useAuth.ts', type: 'file', content: "import { useState, useEffect } from 'react';\n\nexport function useAuth() {\n  const [user, setUser] = useState(null);\n  const [loading, setLoading] = useState(true);\n\n  useEffect(() => {\n    checkAuth();\n  }, []);\n\n  async function checkAuth() {\n    setLoading(true);\n    try {\n      const response = await fetch('/api/auth');\n      if (response.ok) {\n        const data = await response.json();\n        setUser(data.user);\n      }\n    } finally {\n      setLoading(false);\n    }\n  }\n\n  return { user, loading };\n}" },
          ]},
          { name: 'utils', path: 'src/utils', type: 'folder', children: [
            { name: 'api.ts', path: 'src/utils/api.ts', type: 'file', content: "const API_BASE = process.env.NEXT_PUBLIC_API_URL;\n\nexport async function fetchJSON(url: string, options?: RequestInit) {\n  const response = await fetch(url, {\n    ...options,\n    headers: {\n      'Content-Type': 'application/json',\n      ...options?.headers,\n    },\n  });\n\n  if (!response.ok) {\n    throw new Error(`HTTP ${response.status}`);\n  }\n\n  return response.json();\n}" },
          ]},
          { name: 'App.tsx', path: 'src/App.tsx', type: 'file', content: "import React from 'react';\nimport { Button } from './components/Button';\nimport { Card } from './components/Card';\nimport { Input } from './components/Input';\n\nexport default function App() {\n  return (\n    <div className=\"app\">\n      <Card>\n        <h1>Welcome to My App</h1>\n        <Input placeholder=\"Enter your name\" />\n        <Button>Submit</Button>\n      </Card>\n    </div>\n  );\n}" },
          { name: 'index.tsx', path: 'src/index.tsx', type: 'file', content: "import React from 'react';\nimport ReactDOM from 'react-dom/client';\nimport App from './App';\n\nconst root = ReactDOM.createRoot(\n  document.getElementById('root') as HTMLElement\n);\n\nroot.render(\n  <React.StrictMode>\n    <App />\n  </React.StrictMode>\n);" },
        ],
      },
      {
        name: 'config',
        path: 'config',
        type: 'folder',
        children: [
          { name: 'config.json', path: 'config/config.json', type: 'file', content: "{\n  \"name\": \"my-project\",\n  \"version\": \"1.0.0\",\n  \"dependencies\": {\n    \"react\": \"^18.2.0\",\n    \"typescript\": \"^5.0.0\"\n  }\n}" },
          { name: 'tsconfig.json', path: 'config/tsconfig.json', type: 'file', content: "{\n  \"compilerOptions\": {\n    \"target\": \"ES2020\",\n    \"lib\": [\"dom\", \"dom.iterable\", \"esnext\"],\n    \"module\": \"esnext\",\n    \"jsx\": \"react-jsx\"\n  }\n}" },
        ],
      },
      {
        name: 'tests',
        path: 'tests',
        type: 'folder',
        children: [
          { name: 'App.test.tsx', path: 'tests/App.test.tsx', type: 'file', content: "import { render, screen } from '@testing-library/react';\nimport App from '../src/App';\n\ntest('renders app', () => {\n  render(<App />);\n  expect(screen.getByText('Welcome')).toBeTruthy();\n});" },
        ],
      },
      { name: 'package.json', path: 'package.json', type: 'file', content: "{\n  \"name\": \"my-project\",\n  \"version\": \"1.0.0\",\n  \"scripts\": {\n    \"dev\": \"next dev\",\n    \"build\": \"next build\"\n  },\n  \"dependencies\": {\n    \"react\": \"^18.2.0\"\n  }\n}" },
      { name: 'README.md', path: 'README.md', type: 'file', content: "# My Project\n\nThis is a sample repository for testing APRIS.\n\n## Installation\n\n```bash\nnpm install\n```\n\n## Usage\n\n```bash\nnpm run dev\n```" },
      { name: '.gitignore', path: '.gitignore', type: 'file', content: "node_modules\ndist\n.next\n.env\n*.log" },
    ]

    setFiles(mockFiles)
    setExpandedFolders(new Set(['src', 'src/components', 'src/hooks', 'src/utils', 'config', 'tests']))
    setIsAnalyzing(false)
  }, [repoUrl, addLog])

  const toggleFolder = (path: string) => {
    setExpandedFolders(prev => {
      const next = new Set(prev)
      if (next.has(path)) {
        next.delete(path)
      } else {
        next.add(path)
      }
      return next
    })
  }

  const selectFile = (file: FileNode) => {
    if (file.type === 'file' && file.content) {
      setSelectedFile(file.path)
      setFileContent(file.content)
    }
  }

  const flattenFiles = (nodes: FileNode[]): FileNode[] => {
    let result: FileNode[] = []
    for (const node of nodes) {
      result.push(node)
      if (node.type === 'folder' && node.children && expandedFolders.has(node.path)) {
        result = result.concat(flattenFiles(node.children))
      }
    }
    return result
  }

  const flatFiles = flattenFiles(files)

  const getFileIcon = (file: FileNode) => {
    if (file.type === 'folder') {
      return expandedFolders.has(file.path) 
        ? <Folder className="w-4 h-4 text-yellow-500" fill="currentColor" /> 
        : <Folder className="w-4 h-4 text-yellow-500" />
    }
    const ext = file.name.split('.').pop()?.toLowerCase()
    switch (ext) {
      case 'tsx':
      case 'jsx':
      case 'ts':
      case 'js':
        return <FileCode className="w-4 h-4 text-blue-500" />
      case 'json':
        return <Database className="w-4 h-4 text-green-500" />
      case 'md':
        return <FileText className="w-4 h-4 text-gray-500" />
      default:
        return <File className="w-4 h-4 text-gray-400" />
    }
  }

  const getLanguage = (filename: string): string => {
    const ext = filename.split('.').pop()?.toLowerCase()
    switch (ext) {
      case 'tsx': return 'tsx'
      case 'jsx': return 'jsx'
      case 'ts': return 'typescript'
      case 'js': return 'javascript'
      case 'json': return 'json'
      case 'md': return 'markdown'
      default: return 'text'
    }
  }

  return (
    <div className="flex h-screen bg-white">
      {/* Left Sidebar - Agent Bar */}
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

        {/* Agent Status Card */}
        <div className="p-4 border-b border-border">
          <div className="bg-white rounded-lg p-4 shadow-sm">
            <div className="flex items-center gap-3 mb-3">
              {isAnalyzing ? (
                <motion.div 
                  animate={{ rotate: 360 }}
                  transition={{ repeat: Infinity, duration: 1, ease: "linear" }}
                  className="w-5 h-5"
                >
                  <Loader2 className="w-5 h-5 text-primary" />
                </motion.div>
              ) : (
                <div className="w-5 h-5 flex items-center justify-center">
                  <CheckCircle2 className="w-5 h-5 text-success" />
                </div>
              )}
              <span className="text-sm font-medium text-text-primary">
                {isAnalyzing ? 'Analyzing repository...' : 'Ready'}
              </span>
            </div>
            {isAnalyzing && (
              <motion.div 
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="text-xs text-text-muted"
              >
                Step {currentStep} of 5
                <div className="mt-2 h-1.5 bg-surface rounded-full overflow-hidden">
                  <motion.div 
                    className="h-full bg-primary rounded-full"
                    initial={{ width: 0 }}
                    animate={{ width: `${(currentStep / 5) * 100}%` }}
                    transition={{ duration: 0.3 }}
                  />
                </div>
              </motion.div>
            )}
          </div>
        </div>

        {/* Mini Log Feed */}
        <div className="flex-1 p-4 overflow-hidden">
          <div className="text-xs font-medium text-text-muted mb-2 uppercase tracking-wider">Agent Log</div>
          <div className="bg-white rounded-lg p-3 h-[200px] overflow-y-auto">
            <AnimatePresence>
              {logs.slice(-4).map((log, index) => (
                <motion.div
                  key={log.id}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: index * 0.1 }}
                  className="text-xs text-text-muted py-1 border-b border-border last:border-0"
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
          <button className="flex-1 bg-red-500 hover:bg-red-600 text-white text-sm font-medium py-2 px-3 rounded-lg transition-colors flex items-center justify-center gap-2">
            <XCircle className="w-4 h-4" />
            Stop
          </button>
          <button 
            onClick={simulateAnalysis}
            disabled={!repoUrl || isAnalyzing}
            className="flex-1 bg-primary hover:bg-blue-600 disabled:bg-blue-300 text-white text-sm font-medium py-2 px-3 rounded-lg transition-colors flex items-center justify-center gap-2"
          >
            <RotateCcw className="w-4 h-4" />
            Retry
          </button>
        </div>
      </aside>

      {/* Main Panel */}
      <main className="flex-1 flex flex-col">
        {/* URL Input Bar */}
        <div className="p-4 border-b border-border">
          <div className="flex gap-3 max-w-4xl">
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-text-muted" />
              <input
                type="text"
                value={repoUrl}
                onChange={(e) => setRepoUrl(e.target.value)}
                placeholder="Enter GitHub repository URL (e.g., https://github.com/facebook/react)"
                className="w-full pl-10 pr-4 py-3 bg-surface border border-border rounded-lg text-sm text-text-primary placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
              />
            </div>
            <button
              onClick={simulateAnalysis}
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

        {/* Content Area */}
        <div className="flex-1 flex overflow-hidden">
          {/* File Tree */}
          <div className="w-[320px] border-r border-border overflow-y-auto bg-white">
            <AnimatePresence>
              {isAnalyzing ? (
                <motion.div 
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  className="flex flex-col items-center justify-center h-full p-8"
                >
                  <motion.div
                    animate={{ rotate: 360 }}
                    transition={{ repeat: Infinity, duration: 1.5, ease: "linear" }}
                    className="w-10 h-10 border-2 border-primary border-t-transparent rounded-full mb-4"
                  />
                  <p className="text-sm text-text-muted">Agent working...</p>
                  <p className="text-xs text-text-muted mt-1">Analyzing repository structure</p>
                </motion.div>
              ) : files.length > 0 ? (
                <motion.div 
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="p-2"
                >
                  <div className="text-xs font-medium text-text-muted px-2 py-1 mb-1">Project Files</div>
                  {flatFiles.map((file, index) => {
                    const depth = file.path.split('/').length - 1
                    const isFolder = file.type === 'folder'
                    const isExpanded = expandedFolders.has(file.path)
                    
                    return (
                      <motion.div
                        key={file.path}
                        initial={{ opacity: 0, x: -20 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: index * 0.02 }}
                        className={`flex items-center gap-1 py-1 px-2 rounded cursor-pointer hover:bg-surface ${
                          selectedFile === file.path ? 'bg-blue-50' : ''
                        }`}
                        style={{ paddingLeft: `${depth * 16 + 8}px` }}
                        onClick={() => isFolder ? toggleFolder(file.path) : selectFile(file)}
                      >
                        {isFolder ? (
                          isExpanded ? (
                            <ChevronDown className="w-3 h-3 text-text-muted" />
                          ) : (
                            <ChevronRight className="w-3 h-3 text-text-muted" />
                          )
                        ) : (
                          <span className="w-3" />
                        )}
                        {getFileIcon(file)}
                        <span className={`text-sm truncate ${selectedFile === file.path ? 'text-primary font-medium' : 'text-text-primary'}`}>
                          {file.name}
                        </span>
                      </motion.div>
                    )
                  })}
                </motion.div>
              ) : (
                <div className="flex flex-col items-center justify-center h-full p-8 text-center">
                  <GitBranch className="w-12 h-12 text-border mb-3" />
                  <p className="text-sm text-text-muted">Enter a GitHub repository URL to analyze</p>
                </div>
              )}
            </AnimatePresence>
          </div>

          {/* Code Preview */}
          <div className="flex-1 overflow-hidden bg-[#1E1E1E]">
            <AnimatePresence mode="wait">
              {selectedFile && fileContent ? (
                <motion.div
                  key={selectedFile}
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  className="h-full overflow-auto"
                >
                  <div className="sticky top-0 bg-[#2D2D2D] px-4 py-2 border-b border-[#404040] flex items-center gap-2">
                    <FileCode className="w-4 h-4 text-text-muted" />
                    <span className="text-sm text-[#CCCCCC]">{selectedFile}</span>
                  </div>
                  <Highlight
                    theme={themes.vsDark}
                    code={fileContent}
                    language={getLanguage(selectedFile)}
                  >
                    {({ className, style, tokens, getLineProps, getTokenProps }) => (
                      <pre className={`${className} p-4 text-sm`} style={{ ...style, background: 'transparent' }}>
                        {tokens.map((line, i) => (
                          <div key={i} {...getLineProps({ line })}>
                            <span className="inline-block w-8 text-[#6B7280] select-none text-right mr-4">{i + 1}</span>
                            {line.map((token, key) => (
                              <span key={key} {...getTokenProps({ token })} />
                            ))}
                          </div>
                        ))}
                      </pre>
                    )}
                  </Highlight>
                </motion.div>
              ) : (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  className="flex flex-col items-center justify-center h-full"
                >
                  <FileCode className="w-16 h-16 text-[#404040] mb-4" />
                  <p className="text-[#6B7280]">Select a file to preview</p>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>
      </main>
    </div>
  )
}
