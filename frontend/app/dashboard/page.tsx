// frontend/app/dashboard/page.tsx
"use client";

import { useState, useCallback, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { 
  Brain, 
  Sparkles, 
  Zap, 
  TrendingUp, 
  Shield, 
  Clock,
  DollarSign,
  BarChart3,
  Users,
  Code2,
  FileText,
  Target
} from "lucide-react";

interface QueryResult {
  request_id: string;
  answer: string;
  confidence: number;
  models_used: string[];
  winner_model: string;
  response_time_ms: number;
  estimated_cost: number;
  reasoning?: string;
  trust_metrics?: Record<string, number>;
}

interface ModelMetrics {
  model: string;
  score: number;
  responseTime: number;
  reliability: number;
}

export default function Dashboard() {
  const [prompt, setPrompt] = useState("");
  const [mode, setMode] = useState("balanced");
  const [useAdvanced, setUseAdvanced] = useState(true);
  const [maxModels, setMaxModels] = useState("4");
  const [budgetLimit, setBudgetLimit] = useState("");
  const [result, setResult] = useState<QueryResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [modelMetrics, setModelMetrics] = useState<ModelMetrics[]>([]);
  const [totalQueries, setTotalQueries] = useState(0);
  const [totalCost, setTotalCost] = useState(0);

  // Simulated stats - in production these would come from your API
  useEffect(() => {
    // Fetch user stats
    setTotalQueries(127);
    setTotalCost(3.47);
  }, []);

  const handleSubmit = useCallback(async () => {
    if (!prompt.trim()) return;
    
    setError(null);
    setLoading(true);
    
    try {
      const response = await fetch("/api/v1/query", {
        method: "POST",
        headers: { 
          "Content-Type": "application/json",
          "X-API-Key": "your-api-key-here" // In production, manage this securely
        },
        body: JSON.stringify({
          prompt,
          mode,
          max_models: parseInt(maxModels),
          budget_limit: budgetLimit ? parseFloat(budgetLimit) : undefined,
          include_reasoning: useAdvanced,
          output_format: "json",
          stream_response: false
        }),
      });

      if (!response.ok) {
        throw new Error(`API Error: ${response.status}`);
      }

      const data = await response.json();
      setResult(data);
      
      // Update metrics
      setTotalQueries(prev => prev + 1);
      setTotalCost(prev => prev + (data.estimated_cost || 0));
      
      // Simulated model metrics
      const metrics: ModelMetrics[] = data.models_used.map((model: string, idx: number) => ({
        model,
        score: 85 + Math.random() * 15,
        responseTime: 500 + Math.random() * 1500,
        reliability: 90 + Math.random() * 10
      }));
      setModelMetrics(metrics);
      
    } catch (err: any) {
      setError(err.message || "An error occurred");
    } finally {
      setLoading(false);
    }
  }, [prompt, mode, maxModels, budgetLimit, useAdvanced]);

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100">
      {/* Header */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between py-4">
            <div className="flex items-center space-x-3">
              <Brain className="h-8 w-8 text-blue-600" />
              <h1 className="text-2xl font-bold text-gray-900">NextAGI Dashboard</h1>
            </div>
            <div className="flex items-center space-x-4">
              <Badge variant="outline" className="text-sm">
                API v2.0
              </Badge>
              <Button variant="outline" size="sm">
                <FileText className="h-4 w-4 mr-2" />
                Docs
              </Button>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Stats Overview */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
          <Card>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-600">Total Queries</p>
                  <p className="text-2xl font-bold">{totalQueries}</p>
                </div>
                <BarChart3 className="h-8 w-8 text-blue-500" />
              </div>
            </CardContent>
          </Card>
          
          <Card>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-600">Total Cost</p>
                  <p className="text-2xl font-bold">${totalCost.toFixed(2)}</p>
                </div>
                <DollarSign className="h-8 w-8 text-green-500" />
              </div>
            </CardContent>
          </Card>
          
          <Card>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-600">Avg Confidence</p>
                  <p className="text-2xl font-bold">94.2%</p>
                </div>
                <Target className="h-8 w-8 text-purple-500" />
              </div>
            </CardContent>
          </Card>
          
          <Card>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-600">Active Models</p>
                  <p className="text-2xl font-bold">7</p>
                </div>
                <Users className="h-8 w-8 text-orange-500" />
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Query Interface */}
        <Card className="mb-8">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Sparkles className="h-5 w-5 text-blue-600" />
              Multi-Model Query Engine
            </CardTitle>
            <CardDescription>
              Route your query to multiple AI models and get the most accurate answer
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* Query Input */}
            <div className="space-y-2">
              <Label htmlFor="prompt">Your Question</Label>
              <Textarea
                id="prompt"
                placeholder="Ask anything... I'll consult multiple AI models to give you the best answer"
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                className="min-h-[120px] resize-none"
              />
            </div>

            {/* Mode Selection */}
            <div className="space-y-2">
              <Label>Query Mode</Label>
              <div className="flex gap-2">
                {[
                  { value: "speed", label: "Speed", icon: Zap, color: "text-yellow-600" },
                  { value: "balanced", label: "Balanced", icon: Shield, color: "text-blue-600" },
                  { value: "quality", label: "Quality", icon: TrendingUp, color: "text-green-600" }
                ].map((m) => (
                  <Button
                    key={m.value}
                    variant={mode === m.value ? "default" : "outline"}
                    onClick={() => setMode(m.value)}
                    className="flex-1"
                  >
                    <m.icon className={`h-4 w-4 mr-2 ${m.color}`} />
                    {m.label}
                  </Button>
                ))}
              </div>
            </div>

            {/* Advanced Options */}
            <div className="space-y-4 border-t pt-4">
              <div className="flex items-center justify-between">
                <div className="space-y-1">
                  <Label htmlFor="advanced">Advanced Options</Label>
                  <p className="text-sm text-gray-500">Fine-tune model selection and analysis</p>
                </div>
                <Switch
                  id="advanced"
                  checked={useAdvanced}
                  onCheckedChange={setUseAdvanced}
                />
              </div>

              {useAdvanced && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pl-4">
                  <div className="space-y-2">
                    <Label htmlFor="max-models">Max Models</Label>
                    <Input
                      id="max-models"
                      type="number"
                      min="1"
                      max="8"
                      value={maxModels}
                      onChange={(e) => setMaxModels(e.target.value)}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="budget">Budget Limit ($)</Label>
                    <Input
                      id="budget"
                      type="number"
                      step="0.01"
                      placeholder="Optional"
                      value={budgetLimit}
                      onChange={(e) => setBudgetLimit(e.target.value)}
                    />
                  </div>
                </div>
              )}
            </div>

            {/* Submit Button */}
            <Button 
              onClick={handleSubmit} 
              disabled={loading || !prompt.trim()}
              className="w-full"
              size="lg"
            >
              {loading ? (
                <>
                  <Clock className="h-4 w-4 mr-2 animate-spin" />
                  Analyzing with Multiple Models...
                </>
              ) : (
                <>
                  <Brain className="h-4 w-4 mr-2" />
                  Get Best Answer
                </>
              )}
            </Button>

            {error && (
              <div className="p-4 bg-red-50 border border-red-200 rounded-lg text-red-700">
                {error}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Results Section */}
        {result && (
          <div className="space-y-6">
            {/* Answer Card */}
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle>Best Answer</CardTitle>
                  <div className="flex items-center gap-2">
                    <Badge variant="secondary">
                      Confidence: {(result.confidence * 100).toFixed(1)}%
                    </Badge>
                    <Badge variant="outline">
                      {result.response_time_ms}ms
                    </Badge>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <div className="prose max-w-none">
                  <p className="text-gray-800 leading-relaxed">{result.answer}</p>
                </div>
                
                {result.reasoning && useAdvanced && (
                  <div className="mt-4 p-4 bg-blue-50 rounded-lg">
                    <h4 className="font-medium text-blue-900 mb-2">Analysis Reasoning</h4>
                    <p className="text-sm text-blue-800">{result.reasoning}</p>
                  </div>
                )}

                <div className="mt-4 flex items-center justify-between text-sm text-gray-600">
                  <div className="flex items-center gap-4">
                    <span>Winner: <strong>{result.winner_model}</strong></span>
                    <span>Cost: <strong>${result.estimated_cost.toFixed(4)}</strong></span>
                  </div>
                  <Button variant="outline" size="sm">
                    <Code2 className="h-3 w-3 mr-2" />
                    View Raw
                  </Button>
                </div>
              </CardContent>
            </Card>

            {/* Model Performance */}
            {modelMetrics.length > 0 && (
              <Card>
                <CardHeader>
                  <CardTitle>Model Performance Analysis</CardTitle>
                  <CardDescription>
                    Comparative analysis of {modelMetrics.length} models consulted
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    {modelMetrics.map((metric, idx) => (
                      <div key={idx} className="space-y-2">
                        <div className="flex items-center justify-between">
                          <span className="font-medium">{metric.model}</span>
                          <div className="flex items-center gap-4 text-sm">
                            <span className="text-gray-600">
                              Score: {metric.score.toFixed(1)}%
                            </span>
                            <span className="text-gray-600">
                              {metric.responseTime.toFixed(0)}ms
                            </span>
                          </div>
                        </div>
                        <Progress value={metric.score} className="h-2" />
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}
          </div>
        )}
      </main>
    </div>
  );
}