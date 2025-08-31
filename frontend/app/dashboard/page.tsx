// frontend/app/dashboard/page.tsx - ALIGNED WITH BACKEND API
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
  Target,
  CheckCircle,
  AlertTriangle,
  Trophy,
  Activity
} from "lucide-react";

// ALIGNED: Import updated types
import { QueryResponse, ModelMetrics, UsageStats, DisplayModelMetrics, QueryRequest, ModelSelectionMode } from "@/types/api";

export default function Dashboard() {
  // Query UI state
  const [prompt, setPrompt] = useState("");
  const [mode, setMode] = useState<ModelSelectionMode>("balanced");
  const [useAdvanced, setUseAdvanced] = useState(true);
  const [maxModels, setMaxModels] = useState("4");
  const [budgetLimit, setBudgetLimit] = useState("");

  // Results state - using aligned types
  const [result, setResult] = useState<QueryResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Usage stats state
  const [usageStats, setUsageStats] = useState<UsageStats | null>(null);
  const [statsLoading, setStatsLoading] = useState(true);
  const [statsError, setStatsError] = useState<string | null>(null);

  // ALIGNED: Helper functions for data formatting
  const formatNumber = (num: number): string => {
    if (num >= 1_000_000) return `${(num / 1_000_000).toFixed(1)}M`;
    if (num >= 1_000) return `${(num / 1_000).toFixed(1)}K`;
    return num.toString();
  };

  const formatCurrency = (amount: number): string =>
    new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
      minimumFractionDigits: 2,
      maximumFractionDigits: 4,
    }).format(amount);

  const formatPercentage01 = (value01: number): string => {
    const bounded = Math.max(0, Math.min(1, value01));
    return `${(bounded * 100).toFixed(1)}%`;
  };

  const formatTimeMs = (ms: number): string => {
    if (ms >= 1000) return `${(ms / 1000).toFixed(1)}s`;
    return `${Math.round(ms)}ms`;
  };

  // ALIGNED: Convert ModelMetrics to DisplayModelMetrics for UI
  const convertToDisplayMetrics = (metrics: ModelMetrics[]): DisplayModelMetrics[] => {
    return metrics.map(metric => ({
      model: metric.model,
      score: Math.round(metric.confidence * 100), // Convert 0-1 to 0-100
      responseTimeMs: metric.response_time_ms,
      reliabilityPct: Math.round(metric.reliability_score * 100), // Convert 0-1 to 0-100
      cost: metric.cost,
      isWinner: metric.is_winner,
      error: metric.error
    }));
  };

  // Fetch usage statistics
  const fetchUsageStats = useCallback(async () => {
    try {
      setStatsError(null);
      const response = await fetch("/api/v1/usage?days=7");
      
      if (!response.ok) {
        throw new Error(`Failed to fetch usage statistics: ${response.status}`);
      }
      
      const data: UsageStats = await response.json();
      setUsageStats(data);
    } catch (err: any) {
      console.error("Error fetching usage stats:", err);
      setStatsError("Unable to load statistics");
      // Provide fallback data
      setUsageStats({
        total_requests: 0,
        total_tokens: 0,
        total_cost: 0,
        avg_response_time: 0,
        avg_confidence: 0,
        top_models: [],
        daily_usage: [],
        data_available: false,
        message: "Statistics not available"
      });
    } finally {
      setStatsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchUsageStats();
    const interval = setInterval(() => {
      if (!document.hidden) fetchUsageStats();
    }, 30_000);
    return () => clearInterval(interval);
  }, [fetchUsageStats]);

  // ALIGNED: Query submission using correct API format
  const handleSubmit = useCallback(async () => {
    if (!prompt.trim()) return;
    
    setError(null);
    setLoading(true);
    setResult(null);

    try {
      const requestBody: QueryRequest = {
        prompt: prompt.trim(),
        mode: mode,
        max_models: parseInt(maxModels),
        budget_limit: budgetLimit ? parseFloat(budgetLimit) : undefined,
        include_reasoning: useAdvanced,
      };

      const response = await fetch("/api/v1/query", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          // Remove hardcoded API key - let backend handle auth
        },
        body: JSON.stringify(requestBody),
      });

      if (!response.ok) {
        const errorData = await response.text();
        throw new Error(`API Error ${response.status}: ${errorData}`);
      }

      const data: QueryResponse = await response.json();
      console.log("✅ Aligned API response:", data);
      
      // ALIGNED: Data is now in correct format, no normalization needed
      setResult(data);
      
      // Refresh usage stats after successful query
      fetchUsageStats();
      
    } catch (err: any) {
      console.error("❌ Query failed:", err);
      setError(err.message || "An error occurred");
    } finally {
      setLoading(false);
    }
  }, [prompt, mode, maxModels, budgetLimit, useAdvanced, fetchUsageStats]);

  // ALIGNED: Get confidence color based on score
  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.8) return "text-green-500 bg-green-50 border-green-200";
    if (confidence >= 0.6) return "text-yellow-600 bg-yellow-50 border-yellow-200";
    return "text-red-500 bg-red-50 border-red-200";
  };

  const getConfidenceIcon = (confidence: number) => {
    if (confidence >= 0.8) return CheckCircle;
    if (confidence >= 0.6) return AlertTriangle;
    return AlertTriangle;
  };

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
              <Badge variant="outline" className="text-sm bg-green-50 text-green-700 border-green-200">
                API v2.0 Aligned
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
                  <p className="text-sm text-gray-600">Total Queries (7d)</p>
                  <p className="text-2xl font-bold">
                    {statsLoading ? "—" : usageStats?.data_available ? formatNumber(usageStats.total_requests) : "0"}
                  </p>
                </div>
                <BarChart3 className="h-8 w-8 text-blue-500" />
              </div>
              {statsError && <p className="mt-2 text-xs text-red-500">{statsError}</p>}
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-600">Total Cost (7d)</p>
                  <p className="text-2xl font-bold">
                    {statsLoading ? "—" : usageStats?.data_available ? formatCurrency(usageStats.total_cost) : "$0.00"}
                  </p>
                </div>
                <DollarSign className="h-8 w-8 text-green-500" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-600">Avg Confidence (7d)</p>
                  <p className="text-2xl font-bold">
                    {statsLoading ? "—" : usageStats?.data_available ? formatPercentage01(usageStats.avg_confidence) : "—"}
                  </p>
                </div>
                <Target className="h-8 w-8 text-purple-500" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-600">Avg Response Time</p>
                  <p className="text-2xl font-bold">
                    {statsLoading ? "—" : usageStats?.data_available ? `${usageStats.avg_response_time.toFixed(1)}s` : "—"}
                  </p>
                </div>
                <Clock className="h-8 w-8 text-orange-500" />
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

            <div className="space-y-2">
              <Label>Query Mode</Label>
              <div className="flex gap-2">
                {[
                  { value: "speed", label: "Speed", icon: Zap, color: "text-yellow-600" },
                  { value: "balanced", label: "Balanced", icon: Shield, color: "text-blue-600" },
                  { value: "quality", label: "Quality", icon: TrendingUp, color: "text-green-600" },
                ].map((m) => (
                  <Button
                    key={m.value}
                    variant={mode === m.value ? "default" : "outline"}
                    onClick={() => setMode(m.value as ModelSelectionMode)}
                    className="flex-1"
                  >
                    <m.icon className={`h-4 w-4 mr-2 ${m.color}`} />
                    {m.label}
                  </Button>
                ))}
              </div>
            </div>

            <div className="space-y-4 border-t pt-4">
              <div className="flex items-center justify-between">
                <div className="space-y-1">
                  <Label htmlFor="advanced">Advanced Options</Label>
                  <p className="text-sm text-gray-500">Fine-tune model selection and analysis</p>
                </div>
                <Switch id="advanced" checked={useAdvanced} onCheckedChange={setUseAdvanced} />
              </div>

              {useAdvanced && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pl-4">
                  <div className="space-y-2">
                    <Label htmlFor="max-models">Max Models</Label>
                    <Input
                      id="max-models"
                      type="number"
                      min={1}
                      max={5}
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

            <Button onClick={handleSubmit} disabled={loading || !prompt.trim()} className="w-full" size="lg">
              {loading ? (
                <>
                  <Activity className="h-4 w-4 mr-2 animate-spin" />
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
                <div className="flex items-center gap-2">
                  <AlertTriangle className="h-5 w-5" />
                  <span className="font-medium">Error:</span>
                  <span>{error}</span>
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Results Section */}
        {result && (
          <div className="space-y-6">
            {/* Best Answer Card */}
            <Card className="border-green-200 bg-green-50/20">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle className="flex items-center gap-2">
                    <Trophy className="h-5 w-5 text-yellow-500" />
                    Best Answer
                  </CardTitle>
                  <div className="flex items-center gap-2">
                    <Badge className={getConfidenceColor(result.confidence)}>
                      Confidence: {formatPercentage01(result.confidence)}
                    </Badge>
                    <Badge variant="outline">
                      {formatTimeMs(result.response_time_ms)}
                    </Badge>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <div className="prose max-w-none">
                  <p className="text-gray-800 leading-relaxed mb-4">{result.answer}</p>
                </div>

                {result.reasoning && useAdvanced && (
                  <div className="mt-4 p-4 bg-blue-50 rounded-lg border border-blue-200">
                    <h4 className="font-medium text-blue-900 mb-2">Analysis Reasoning</h4>
                    <pre className="text-sm text-blue-800 whitespace-pre-wrap">{result.reasoning}</pre>
                  </div>
                )}

                <div className="mt-4 flex items-center justify-between text-sm text-gray-600">
                  <div className="flex items-center gap-4">
                    <span>Winner: <strong className="text-green-600">{result.winner_model}</strong></span>
                    <span>Cost: <strong className="text-blue-600">{formatCurrency(result.total_cost)}</strong></span>
                    <span>Models: <strong>{result.models_succeeded.length}</strong></span>
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => navigator.clipboard.writeText(JSON.stringify(result, null, 2))}
                  >
                    <Code2 className="h-3 w-3 mr-2" />
                    Copy Raw
                  </Button>
                </div>
              </CardContent>
            </Card>

            {/* Model Comparison Overview */}
            {result.model_comparison && (
              <Card>
                <CardHeader>
                  <CardTitle>Performance Summary</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-2 md:grid-cols-5 gap-4 text-center">
                    <div>
                      <div className="text-2xl font-bold text-blue-600">{result.model_comparison.model_count}</div>
                      <div className="text-sm text-gray-500">Models</div>
                    </div>
                    <div>
                      <div className="text-2xl font-bold text-green-600">
                        {formatPercentage01(result.model_comparison.best_confidence)}
                      </div>
                      <div className="text-sm text-gray-500">Best Score</div>
                    </div>
                    <div>
                      <div className="text-2xl font-bold text-gray-600">
                        {formatTimeMs(result.model_comparison.avg_response_time)}
                      </div>
                      <div className="text-sm text-gray-500">Avg Time</div>
                    </div>
                    <div>
                      <div className="text-2xl font-bold text-yellow-600">
                        {formatCurrency(result.model_comparison.total_cost)}
                      </div>
                      <div className="text-sm text-gray-500">Total Cost</div>
                    </div>
                    <div>
                      <div className="text-2xl font-bold text-purple-600">
                        {formatPercentage01(result.model_comparison.performance_spread)}
                      </div>
                      <div className="text-sm text-gray-500">Spread</div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Individual Model Results */}
            {result.model_metrics.length > 0 && (
              <Card>
                <CardHeader>
                  <CardTitle>Individual Model Analysis</CardTitle>
                  <CardDescription>
                    Detailed performance breakdown of {result.model_metrics.length} models consulted
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    {result.model_metrics.map((metric, idx) => {
                      const ConfidenceIcon = getConfidenceIcon(metric.confidence);
                      
                      return (
                        <div key={`${metric.model}-${idx}`} className={`border rounded-lg p-4 ${
                          metric.is_winner ? 'border-yellow-300 bg-yellow-50/30' : 'border-gray-200'
                        }`}>
                          <div className="flex items-center justify-between mb-3">
                            <div className="flex items-center gap-2">
                              {metric.is_winner && <Trophy className="h-4 w-4 text-yellow-500" />}
                              <span className="font-medium text-gray-900">
                                #{metric.rank_position} {metric.model.split('/').pop()}
                              </span>
                            </div>
                            <div className="flex items-center gap-2">
                              <ConfidenceIcon className={`h-4 w-4 ${getConfidenceColor(metric.confidence).split(' ')[0]}`} />
                              <Badge className={getConfidenceColor(metric.confidence)}>
                                {formatPercentage01(metric.confidence)}
                              </Badge>
                            </div>
                          </div>

                          {/* Response Preview */}
                          <div className="mb-3 p-3 bg-gray-50 rounded border">
                            <p className="text-sm text-gray-700 line-clamp-3">
                              {metric.response.length > 200 
                                ? metric.response.substring(0, 200) + "..."
                                : metric.response
                              }
                            </p>
                          </div>

                          {/* Metrics Grid */}
                          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
                            <div>
                              <span className="text-gray-500">Time:</span>
                              <span className="ml-1 font-medium">{formatTimeMs(metric.response_time_ms)}</span>
                            </div>
                            <div>
                              <span className="text-gray-500">Cost:</span>
                              <span className="ml-1 font-medium">{formatCurrency(metric.cost)}</span>
                            </div>
                            <div>
                              <span className="text-gray-500">Reliability:</span>
                              <span className="ml-1 font-medium text-green-600">
                                {formatPercentage01(metric.reliability_score)}
                              </span>
                            </div>
                            <div>
                              <span className="text-gray-500">Risk:</span>
                              <span className="ml-1 font-medium text-red-600">
                                {formatPercentage01(metric.hallucination_risk)}
                              </span>
                            </div>
                          </div>

                          {/* Performance Bars */}
                          <div className="mt-3 space-y-2">
                            <div>
                              <div className="flex justify-between text-xs mb-1">
                                <span className="text-gray-500">Consistency</span>
                                <span>{formatPercentage01(metric.consistency_score)}</span>
                              </div>
                              <Progress value={metric.consistency_score * 100} className="h-2" />
                            </div>
                            <div>
                              <div className="flex justify-between text-xs mb-1">
                                <span className="text-gray-500">Citation Quality</span>
                                <span>{formatPercentage01(metric.citation_quality)}</span>
                              </div>
                              <Progress value={metric.citation_quality * 100} className="h-2" />
                            </div>
                          </div>

                          {/* Trait Scores */}
                          {Object.keys(metric.trait_scores).length > 0 && (
                            <div className="mt-3">
                              <div className="text-xs text-gray-500 mb-2">Additional Traits:</div>
                              <div className="flex flex-wrap gap-1">
                                {Object.entries(metric.trait_scores).map(([trait, score]) => (
                                  <Badge key={trait} variant="outline" className="text-xs">
                                    {trait}: {formatPercentage01(score)}
                                  </Badge>
                                ))}
                              </div>
                            </div>
                          )}

                          {metric.error && (
                            <div className="mt-3 p-2 bg-red-50 border border-red-200 rounded text-sm text-red-700">
                              <strong>Error:</strong> {metric.error}
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </CardContent>
              </Card>
            )}
          </div>
        )}

        {/* Model Usage Stats */}
        {usageStats?.data_available && usageStats.top_models?.length > 0 && (
          <Card>
            <CardHeader>
              <CardTitle>Model Usage (7d)</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {usageStats.top_models.map((model, i) => (
                  <div key={i} className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <span className="font-medium">{model.name}</span>
                      <span className="text-sm text-gray-500">{model.usage_percentage.toFixed(1)}% usage</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="w-20 h-2 bg-gray-200 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-blue-500 transition-all duration-300"
                          style={{ width: `${model.usage_percentage}%` }}
                        />
                      </div>
                      <span className="text-sm font-medium">{formatPercentage01(model.avg_score)}</span>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}

        {/* Empty state */}
        {!result && !loading && (
          <Card>
            <CardContent className="flex flex-col items-center justify-center py-12">
              <Brain className="h-12 w-12 text-gray-400 mb-4" />
              <p className="text-gray-500 text-center max-w-md">
                Enter your question above to see NextAGI's intelligent multi-model analysis. 
                Get the most accurate answer by consulting multiple AI models simultaneously.
              </p>
            </CardContent>
          </Card>
        )}
      </main>
    </div>
  );
}