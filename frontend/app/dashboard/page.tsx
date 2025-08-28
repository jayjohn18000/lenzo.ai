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
  Target,
} from "lucide-react";

interface QueryResult {
  request_id: string;
  answer: string;
  confidence: number; // 0..1
  models_used: string[];
  winner_model: string;
  response_time_ms: number;
  estimated_cost: number;
  reasoning?: string;
  trust_metrics?: Record<string, number>; // per-model score 0..1 or 0..100
  // Optional per-model extras if your API returns them:
  per_model_latency_ms?: Record<string, number>;
  per_model_reliability?: Record<string, number>; // 0..1
  [key: string]: any; // allow unknown extras without TS errors
}

interface UsageStats {
  total_requests: number;
  total_tokens: number;
  total_cost: number;
  avg_response_time: number; // in seconds (as in your updated file)
  avg_confidence: number; // 0..1
  top_models: Array<{
    name: string;
    usage_percentage: number; // 0..100
    avg_score: number; // 0..1
  }>;
  daily_usage: Array<{
    date: string;
    requests: number;
    cost: number;
  }>;
  data_available: boolean;
  message?: string;
}

interface ModelMetrics {
  model: string;
  score?: number; // 0..100
  responseTimeMs?: number;
  reliabilityPct?: number; // 0..100
}

export default function Dashboard() {
  // ----- Query UI state -----
  const [prompt, setPrompt] = useState("");
  const [mode, setMode] = useState<"speed" | "balanced" | "quality">("balanced");
  const [useAdvanced, setUseAdvanced] = useState(true);
  const [maxModels, setMaxModels] = useState("4");
  const [budgetLimit, setBudgetLimit] = useState("");

  // ----- Live results state -----
  const [result, setResult] = useState<QueryResult | null>(null);
  const [modelMetrics, setModelMetrics] = useState<ModelMetrics[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // ----- Live usage stats (replaces mock totals) -----
  const [usageStats, setUsageStats] = useState<UsageStats | null>(null);
  const [statsLoading, setStatsLoading] = useState(true);
  const [statsError, setStatsError] = useState<string | null>(null);

  // ===== Helpers =====
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
      maximumFractionDigits: 2,
    }).format(amount);

  const formatPercentage01 = (value01: number): string => {
    // value provided 0..1
    const bounded = Math.max(0, Math.min(1, value01));
    return `${(bounded * 100).toFixed(1)}%`;
  };

  // ===== Usage stats (real data) =====
  const fetchUsageStats = useCallback(async () => {
    try {
      setStatsError(null);
      const response = await fetch("/api/v1/usage?days=7", {
        headers: {
          // If you must pass an API key from the client, you can use NEXT_PUBLIC_*
          // Ideally, proxy this via a Next.js route to keep secrets server-side.
          "X-API-Key": process.env.NEXT_PUBLIC_API_KEY || "",
        },
      });
      if (!response.ok) throw new Error("Failed to fetch usage statistics");
      const data: UsageStats = await response.json();
      setUsageStats(data);
    } catch (err: any) {
      console.error("Error fetching usage stats:", err);
      setStatsError("Unable to load statistics");
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

  // ===== Query submission (real data) =====
  const handleSubmit = useCallback(async () => {
    if (!prompt.trim()) return;
    setError(null);
    setLoading(true);

    try {
      const response = await fetch("/api/v1/query", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-API-Key": process.env.NEXT_PUBLIC_API_KEY || "",
        },
        body: JSON.stringify({
          prompt,
          mode,
          max_models: parseInt(maxModels),
          budget_limit: budgetLimit ? parseFloat(budgetLimit) : undefined,
          include_reasoning: useAdvanced,
          output_format: "json",
          stream_response: false,
        }),
      });

      if (!response.ok) {
        throw new Error(`API Error: ${response.status}`);
      }

      const data: QueryResult = await response.json();
      setResult(data);

      // Derive per-model metrics from real fields if present
      const perModelScores = data.trust_metrics || {};
      const perModelLatency = data.per_model_latency_ms || {};
      const perModelReliability = data.per_model_reliability || {};

      const metrics: ModelMetrics[] = (data.models_used || []).map((model) => ({
        model,
        // Accept either 0..1 or 0..100 for trust_metrics; normalize to 0..100
        score:
          typeof perModelScores[model] === "number"
            ? (perModelScores[model]! <= 1 ? perModelScores[model]! * 100 : perModelScores[model]!)
            : undefined,
        responseTimeMs: typeof perModelLatency[model] === "number" ? perModelLatency[model] : undefined,
        reliabilityPct:
          typeof perModelReliability[model] === "number"
            ? (perModelReliability[model]! <= 1
                ? perModelReliability[model]! * 100
                : perModelReliability[model]!)
            : undefined,
      }));

      // Only keep rows with at least one useful value
      setModelMetrics(metrics.filter(m => m.score != null || m.responseTimeMs != null || m.reliabilityPct != null));

      // Optionally refresh usage stats after a successful query
      fetchUsageStats();
    } catch (err: any) {
      setError(err.message || "An error occurred");
    } finally {
      setLoading(false);
    }
  }, [prompt, mode, maxModels, budgetLimit, useAdvanced, fetchUsageStats]);

  // ===== UI =====
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
              <Badge variant="outline" className="text-sm">API v2.0</Badge>
              <Button variant="outline" size="sm">
                <FileText className="h-4 w-4 mr-2" />
                Docs
              </Button>
            </div>
          </div>
        </div>
      </header>

      {/* Main */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Stats Overview (now driven by real usageStats) */}
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
                  <p className="text-sm text-gray-600">Avg Response</p>
                  <p className="text-2xl font-bold">
                    {statsLoading
                      ? "—"
                      : usageStats?.data_available
                        ? `${usageStats.avg_response_time.toFixed(1)}s`
                        : "—"}
                  </p>
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
                  { value: "quality", label: "Quality", icon: TrendingUp, color: "text-green-600" },
                ].map((m) => (
                  <Button
                    key={m.value}
                    variant={mode === m.value ? "default" : "outline"}
                    onClick={() => setMode(m.value as typeof mode)}
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
                      max={8}
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

            {/* Submit */}
            <Button onClick={handleSubmit} disabled={loading || !prompt.trim()} className="w-full" size="lg">
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

            {error && <div className="p-4 bg-red-50 border border-red-200 rounded-lg text-red-700">{error}</div>}
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
                      Confidence: {(Math.max(0, Math.min(1, result.confidence)) * 100).toFixed(1)}%
                    </Badge>
                    <Badge variant="outline">{Math.round(result.response_time_ms)}ms</Badge>
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
                    <span>
                      Winner: <strong>{result.winner_model}</strong>
                    </span>
                    <span>
                      Cost: <strong>{formatCurrency(result.estimated_cost ?? 0)}</strong>
                    </span>
                  </div>
                  <Button variant="outline" size="sm" onClick={() => navigator.clipboard.writeText(JSON.stringify(result, null, 2))}>
                    <Code2 className="h-3 w-3 mr-2" />
                    Copy Raw
                  </Button>
                </div>
              </CardContent>
            </Card>

            {/* Model Performance */}
            {modelMetrics.length > 0 && (
              <Card>
                <CardHeader>
                  <CardTitle>Model Performance Analysis</CardTitle>
                  <CardDescription>Comparative analysis of {modelMetrics.length} models consulted</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    {modelMetrics.map((metric, idx) => (
                      <div key={idx} className="space-y-2">
                        <div className="flex items-center justify-between">
                          <span className="font-medium">{metric.model}</span>
                          <div className="flex items-center gap-4 text-sm">
                            {metric.score != null && (
                              <span className="text-gray-600">Score: {metric.score.toFixed(1)}%</span>
                            )}
                            {metric.responseTimeMs != null && (
                              <span className="text-gray-600">{Math.round(metric.responseTimeMs)}ms</span>
                            )}
                            {metric.reliabilityPct != null && (
                              <span className="text-gray-600">Reliability: {metric.reliabilityPct.toFixed(1)}%</span>
                            )}
                          </div>
                        </div>
                        <Progress value={metric.score ?? 0} className="h-2" />
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Model Usage (from usage stats if helpful) */}
            {usageStats?.data_available && usageStats.top_models?.length > 0 && (
              <Card>
                <CardHeader>
                  <CardTitle>Model Usage (7d)</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    {usageStats.top_models.map((m, i) => (
                      <div key={i} className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          <span className="font-medium">{m.name}</span>
                          <span className="text-sm text-gray-500">
                            {m.usage_percentage.toFixed(1)}% usage
                          </span>
                        </div>
                        <div className="text-sm">
                          <span className="text-gray-500">Avg Score: </span>
                          <span className="font-medium">{formatPercentage01(m.avg_score)}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}
          </div>
        )}

        {/* Empty state if no queries yet, but stats are loaded and available */}
        {!result && usageStats?.data_available === false && (
          <Card>
            <CardContent className="flex flex-col items-center justify-center h-48">
              <p className="text-gray-500 text-center">
                {usageStats.message ||
                  "No usage data available yet. Run your first query to see results and statistics here."}
              </p>
            </CardContent>
          </Card>
        )}
      </main>
    </div>
  );
}
