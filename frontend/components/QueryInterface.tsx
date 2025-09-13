import { safePercentage } from '@/lib/safe-formatters';

// Modern, intuitive query interface
import { useState, useCallback } from 'react'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Badge } from '@/components/ui/badge'
import { Card } from '@/components/ui/card'

interface QueryResult {
  answer: string;
  confidence: number;
  models_used: string[];
  response_time_ms: number;
}

export default function QueryInterface() {
  const [query, setQuery] = useState('')
  const [result, setResult] = useState<QueryResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [mode, setMode] = useState('balanced')

  const handleQuery = useCallback(async () => {
    setLoading(true)
    try {
      const response = await fetch('/api/route', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          prompt: query,
          mode: mode,
          include_reasoning: true
        })
      })
      
      const data = await response.json()
      setResult(data)
    } catch (error) {
      console.error('Query failed:', error)
    } finally {
      setLoading(false)
    }
  }, [query, mode])

  return (
    <div className="max-w-4xl mx-auto p-6 space-y-6">
      <div className="space-y-4">
        <Textarea
          placeholder="Ask me anything and I'll query multiple AI models to give you the best answer..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          className="min-h-[120px]"
        />
        
        <div className="flex gap-2">
          {['speed', 'balanced', 'quality'].map((m) => (
            <Button
              key={m}
              variant={mode === m ? 'default' : 'outline'}
              onClick={() => setMode(m)}
              className="capitalize"
            >
              {m}
            </Button>
          ))}
        </div>
        
        <Button onClick={handleQuery} disabled={!query.trim() || loading}>
          {loading ? 'Analyzing...' : 'Get Best Answer'}
        </Button>
      </div>

      {result && (
        <Card className="p-6">
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-semibold">Best Answer</h3>
              <Badge variant="secondary">
                Confidence: {safePercentage(result.confidence, { expectsFraction: true })}%
              </Badge>
            </div>
            
            <div className="prose max-w-none">
              {result.answer}
            </div>
            
            <div className="text-sm text-gray-600">
              <p>Models consulted: {result.models_used.join(', ')}</p>
              <p>Response time: {result.response_time_ms}ms</p>
            </div>
          </div>
        </Card>
      )}
    </div>
  )
}