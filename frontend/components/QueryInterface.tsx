'use client'
import { useState, useCallback } from 'react'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { Loader2, Zap, Target, DollarSign, Brain } from 'lucide-react'

interface QueryResult {
  request_id: string
  answer: string
  confidence: number
  models_used: string[]
  winner_model: string
  response_time_ms: number
  estimated_cost: number
  reasoning?: string
  trust_metrics?: {
    accuracy: number
    consistency: number
    reliability: number
  }
}

export default function EnhancedQueryInterface() {
  const [query, setQuery] = useState('')
  const [result, setResult] = useState<QueryResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [mode, setMode] = useState('balanced')
  const [maxModels, setMaxModels] = useState(4)

  const handleQuery = useCallback(async () => {
    if (!query.trim()) return
    
    setLoading(true)
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/query`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': process.env.NEXT_PUBLIC_API_KEY || 'demo-key'
        },
        body: JSON.stringify({
          prompt: query,
          mode: mode,
          max_models: maxModels,
          include_reasoning: true
        })
      })
      
      if (!response.ok) throw new Error('Query failed')
      
      const data = await response.json()
      setResult(data)
    } catch (error) {
      console.error('Query failed:', error)
      // Add proper error handling
    } finally {
      setLoading(false)
    }
  }, [query, mode, maxModels])

  const modes = [
    { id: 'speed', label: 'Speed', icon: Zap, desc: 'Fast results' },
    { id: 'balanced', label: 'Balanced', icon: Target, desc: 'Quality + Speed' },
    { id: 'quality', label: 'Quality', icon: Brain, desc: 'Maximum accuracy' },
    { id: 'cost', label: 'Cost', icon: DollarSign, desc: 'Budget optimized' }
  ]

  return (
    <div className="max-w-6xl mx-auto p-6 space-y-6">
      {/* Query Input Section */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Brain className="h-5 w-5 text-blue-500" />
            NextAGI Multi-Model Query
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <Textarea
            placeholder="Enter your query here... NextAGI will route it to optimal AI models and provide the most accurate response with confidence scoring."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="min-h-[120px] resize-none"
          />
          
          {/* Mode Selection */}
          <div className="space-y-2">
            <label className="text-sm font-medium">Priority Mode</label>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
              {modes.map((m) => {
                const Icon = m.icon
                return (
                  <Button
                    key={m.id}
                    variant={mode === m.id ? 'default' : 'outline'}
                    onClick={() => setMode(m.id)}
                    className="h-auto p-3 flex flex-col items-center gap-1"
                  >
                    <Icon className="h-4 w-4" />
                    <span className="text-xs">{m.label}</span>
                  </Button>
                )
              })}
            </div>
          </div>

          {/* Max Models */}
          <div className="space-y-2">
            <label className="text-sm font-medium">Models to Query: {maxModels}</label>
            <input
              type="range"
              min="2"
              max="8"
              value={maxModels}
              onChange={(e) => setMaxModels(parseInt(e.target.value))}
              className="w-full"
            />
          </div>
          
          <Button 
            onClick={handleQuery} 
            disabled={!query.trim() || loading}
            className="w-full h-12 text-base font-semibold"
          >
            {loading ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Analyzing with AI Models...
              </>
            ) : (
              'Analyze with NextAGI'
            )}
          </Button>
        </CardContent>
      </Card>

      {/* Results Section */}
      {result && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Main Response */}
          <div className="lg:col-span-2">
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle>AI Response</CardTitle>
                  <Badge variant="secondary" className="text-green-600">
                    {(result.confidence * 100).toFixed(1)}% Confidence
                  </Badge>
                </div>
              </CardHeader>
              <CardContent>
                <div className="prose max-w-none dark:prose-invert">
                  <div className="whitespace-pre-wrap">{result.answer}</div>
                </div>
                
                {result.reasoning && (
                  <details className="mt-4 p-3 bg-gray-50 dark:bg-gray-800 rounded">
                    <summary className="cursor-pointer font-medium">View Reasoning</summary>
                    <div className="mt-2 text-sm text-gray-600 dark:text-gray-300">
                      {result.reasoning}
                    </div>
                  </details>
                )}
              </CardContent>
            </Card>
          </div>

          {/* Metrics Panel */}
          <div className="space-y-4">
            {/* Trust Metrics */}
            {result.trust_metrics && (
              <Card>
                <CardHeader>
                  <CardTitle className="text-sm">Trust Metrics</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  {Object.entries(result.trust_metrics).map(([key, value]) => (
                    <div key={key}>
                      <div className="flex justify-between text-sm mb-1">
                        <span className="capitalize">{key}</span>
                        <span>{(value * 100).toFixed(1)}%</span>
                      </div>
                      <Progress value={value * 100} className="h-2" />
                    </div>
                  ))}
                </CardContent>
              </Card>
            )}

            {/* Performance Metrics */}
            <Card>
              <CardHeader>
                <CardTitle className="text-sm">Performance</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span>Response Time</span>
                  <span>{result.response_time_ms}ms</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span>Models Used</span>
                  <span>{result.models_used.length}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span>Winner Model</span>
                  <span className="text-blue-600">{result.winner_model}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span>Est. Cost</span>
                  <span>${result.estimated_cost.toFixed(4)}</span>
                </div>
              </CardContent>
            </Card>

            {/* Models Used */}
            <Card>
              <CardHeader>
                <CardTitle className="text-sm">Models Consulted</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-1">
                  {result.models_used.map((model, index) => (
                    <Badge 
                      key={index} 
                      variant={model === result.winner_model ? 'default' : 'outline'}
                      className="mr-1 mb-1"
                    >
                      {model}
                    </Badge>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      )}
    </div>
  )
}