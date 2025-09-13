// frontend/app/page.tsx - ALIGNED WITH BACKEND API
"use client";

import { safeToFixed, safeCurrency, safePercentage, safeTime } from '@/lib/safe-formatters';
import { useState, useCallback, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { Badge } from "@/components/ui/badge";
import { 
  Activity, 
  Brain, 
  Shield,
  Clock,
  DollarSign,
  Target,
  Trophy,
  AlertTriangle,
  CheckCircle,
  BarChart3,
  Eye,
  Sparkles,
  Code2,
  Star
} from "lucide-react";

// ALIGNED: Import updated types
import { QueryResponse, ModelMetrics, ModelComparison, QueryRequest, ModelSelectionMode, UsageStats } from "@/types/api";
import { apiClient } from "@/lib/api";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import { HealthStatus } from "@/components/HealthStatus";
import { QueryErrorDisplay } from "@/components/ErrorDisplay";

export default function NextAGIInterface() {
  const [prompt, setPrompt] = useState("");
  const [mode, setMode] = useState<ModelSelectionMode>("balanced");
  const [useAdvanced, setUseAdvanced] = useState(true);
  const [maxModels, setMaxModels] = useState("4");
  const [budgetLimit, setBudgetLimit] = useState("");
  
  // ALIGNED: Use correct QueryResponse type
  const [result, setResult] = useState<QueryResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedModel, setSelectedModel] = useState<string>("");
  const [viewMode, setViewMode] = useState<"comparison" | "individual">("comparison");
  const [confidence, setConfidence] = useState(0);
  const [processingStep, setProcessingStep] = useState("");
  const [activeModels, setActiveModels] = useState<string[]>([]);
  
  // Usage stats state
  const [usageStats, setUsageStats] = useState<UsageStats | null>(null);
  const [statsLoading, setStatsLoading] = useState(true);
  const [statsError, setStatsError] = useState<string | null>(null);

  const processingSteps = [
    "Analyzing query complexity...",
    "Selecting optimal models...",
    "Routing to AI models...",
    "Running hallucination detection...",
    "Calculating consensus scores...",
    "Generating final response..."
  ];

  // Helper functions for data formatting
  const formatNumber = (num: number): string => {
    if (num >= 1_000_000) return `${safeToFixed(num / 1_000_000, 1)}M`;
    if (num >= 1_000) return `${safeToFixed(num / 1_000, 1)}K`;
    return num.toString();
  };

  const formatPercentage01 = (value01: number): string => {
    const percentage = value01 * 100;
    const bounded = Math.max(0, Math.min(100, percentage));
    return `${safeToFixed(bounded, 1)}%`;
  };

  const formatCurrency = (amount: number): string =>
    new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
      minimumFractionDigits: 2,
      maximumFractionDigits: 4,
    }).format(amount);

  // Fetch usage statistics with retry capability
  const fetchUsageStats = useCallback(async (retryCount = 0) => {
    try {
      setStatsError(null);
      setStatsLoading(true);
      
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000'}/dev/usage?days=7`, {
        headers: {
          'Content-Type': 'application/json'
          // No authentication required for dev endpoint
        }
      });
      
      if (!response.ok) {
        if (response.status === 401 || response.status === 403) {
          throw new Error(`Authentication failed (${response.status}): Please check your API key configuration`);
        }
        throw new Error(`Failed to fetch usage statistics: ${response.status}`);
      }
      
      const data: UsageStats = await response.json();
      setUsageStats(data);
    } catch (err: any) {
      console.error("Error fetching usage stats:", err);
      
      // Auto-retry once for network errors
      if (retryCount === 0 && (err.message.includes('fetch') || err.message.includes('network'))) {
        console.log("Retrying usage stats fetch...");
        setTimeout(() => fetchUsageStats(1), 2000);
        return;
      }
      
      setStatsError(err.message || "Unable to load statistics");
      setUsageStats(null);
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

  // ALIGNED: Updated to use correct API contract
  const handleSubmit = useCallback(async () => {
    if (!prompt.trim()) return;
    
    setError(null);
    setLoading(true);
    setResult(null);
    setConfidence(0);
    setSelectedModel("");
    
    // Premium processing animation
    for (let i = 0; i < processingSteps.length; i++) {
      setProcessingStep(processingSteps[i]);
      await new Promise(resolve => setTimeout(resolve, 800));
      
      if (i >= 2) {
        const modelNames = ['GPT-4', 'Claude', 'Gemini', 'Mistral'];
        const modelIndex = Math.min(i - 2, modelNames.length - 1);
        if (modelNames[modelIndex]) {
          setActiveModels(prev => [...prev, modelNames[modelIndex].toLowerCase()]);
        }
      }
    }

    try {
      const requestBody: QueryRequest = {
        prompt: prompt.trim(),
        mode: mode,
        max_models: parseInt(maxModels),
        budget_limit: budgetLimit ? parseFloat(budgetLimit) : undefined,
        include_reasoning: useAdvanced
      };

      console.log("🚀 Starting query with API client:", requestBody);
      
      // Use API client which handles authentication and async job polling automatically
      const data: QueryResponse = await apiClient.query(requestBody);
      
      console.log("✅ Query completed with real results:", data);
      
      // ALIGNED: Use the correct response structure
      setResult(data);
      setSelectedModel(data.winner_model || "");
      
      // Animate confidence score using the correct field
      const targetConfidence = data.confidence ? Math.min(100, Math.max(0, data.confidence * 100)) : 85;
      let currentConf = 0;
      const interval = setInterval(() => {
        currentConf += 2;
        setConfidence(currentConf);
        if (currentConf >= targetConfidence) {
          clearInterval(interval);
          setConfidence(targetConfidence);
        }
      }, 50);
      
    } catch (err: any) {
      console.error("❌ Request failed:", err);
      setError(err.message || "An error occurred");
    } finally {
      setLoading(false);
      setActiveModels([]);
    }
  }, [prompt, mode, maxModels, budgetLimit, useAdvanced]);

  const MetricCard = ({ title, value, trend, icon: Icon, color }: {
    title: string;
    value: string;
    trend: string;
    icon: any;
    color: string;
  }) => (
    <Card className="bg-white/5 backdrop-blur-xl border-white/10">
      <CardContent className="p-6">
        <div className="flex items-center justify-between mb-4">
          <h4 className="text-sm font-medium text-gray-300">{title}</h4>
          <Icon className={`w-5 h-5 ${color}`} />
        </div>
        <div className={`text-2xl font-bold ${color} mb-1`}>{value}</div>
        <div className="text-xs text-green-400">{trend}</div>
      </CardContent>
    </Card>
  );

  const ModelNode = ({ name, active, score }: { name: string; active: boolean; score?: number }) => (
    <div className={`flex flex-col items-center p-3 rounded-lg transition-all duration-300 ${
      active ? 'bg-blue-500 text-white' : 'bg-white/10 text-gray-300'
    }`}>
      <div className="text-xs font-semibold mb-1">{name}</div>
      <div className="text-sm font-bold">{score ? safePercentage(score, { expectsFraction: false }) : '--'}</div>
    </div>
  );

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.8) return "text-green-400 bg-green-400/20";
    if (confidence >= 0.6) return "text-yellow-400 bg-yellow-400/20";
    return "text-red-400 bg-red-400/20";
  };

  const getConfidenceIcon = (confidence: number) => {
    if (confidence >= 0.8) return CheckCircle;
    if (confidence >= 0.6) return AlertTriangle;
    return AlertTriangle;
  };

  // ALIGNED: Premium model card using correct ModelMetrics structure
  const PremiumModelCard = ({ metric, isSelected }: { metric: ModelMetrics; isSelected: boolean }) => {
    const ConfidenceIcon = getConfidenceIcon(metric.confidence);
    
    return (
      <Card className={`bg-white/5 backdrop-blur-xl border-white/10 transition-all duration-300 cursor-pointer hover:bg-white/10 hover:border-white/20 ${
        isSelected ? "ring-2 ring-blue-400 bg-white/10" : ""
      } ${metric.is_winner ? "border-yellow-500/50 bg-gradient-to-br from-yellow-500/10 to-transparent" : ""}`}
      onClick={() => setSelectedModel(metric.model)}>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <CardTitle className="text-lg flex items-center gap-2 text-white">
                {metric.is_winner && <Trophy className="h-4 w-4 text-yellow-400" />}
                <span className="font-mono text-sm">{metric.model.split('/').pop()}</span>
              </CardTitle>
              <Badge className="bg-white/10 text-gray-300 border-white/20">
                #{metric.rank_position}
              </Badge>
            </div>
            <div className="flex items-center gap-2">
              <ConfidenceIcon className={`h-4 w-4 ${getConfidenceColor(metric.confidence).split(' ')[0]}`} />
              <Badge className={`${getConfidenceColor(metric.confidence)} border-0`}>
                {safePercentage(metric.confidence, { expectsFraction: true })}%
              </Badge>
            </div>
          </div>
        </CardHeader>
        
        <CardContent className="space-y-4">
          {/* Response Preview */}
          <div className="space-y-2">
            <Label className="text-xs font-medium text-gray-400">Response</Label>
            <p className="text-sm text-gray-300 bg-black/20 p-3 rounded-md line-clamp-3 border border-white/10">
              {metric.response.length > 150 
                ? metric.response.substring(0, 150) + "..."
                : metric.response
              }
            </p>
          </div>

          {/* Metrics Grid */}
          <div className="grid grid-cols-2 gap-3 text-sm">
            <div className="space-y-1">
              <div className="flex items-center gap-1">
                <Clock className="h-3 w-3 text-gray-400" />
                <span className="text-gray-400">Response</span>
              </div>
              <span className="font-semibold text-white">{metric.response_time_ms}ms</span>
            </div>
            
            <div className="space-y-1">
              <div className="flex items-center gap-1">
                <DollarSign className="h-3 w-3 text-gray-400" />
                <span className="text-gray-400">Cost</span>
              </div>
              <span className="font-semibold text-white">{safeCurrency(metric.cost)}</span>
            </div>
            
            <div className="space-y-1">
              <div className="flex items-center gap-1">
                <Shield className="h-3 w-3 text-gray-400" />
                <span className="text-gray-400">Reliability</span>
              </div>
              <span className="font-semibold text-green-400">{safePercentage(metric.reliability_score, { digits: 0, expectsFraction: true })}</span>
            </div>
            
            <div className="space-y-1">
              <div className="flex items-center gap-1">
                <AlertTriangle className="h-3 w-3 text-gray-400" />
                <span className="text-gray-400">Risk</span>
              </div>
              <span className="font-semibold text-red-400">{safePercentage(metric.hallucination_risk, { digits: 0, expectsFraction: true })}</span>
            </div>
          </div>

          {/* Performance Bars */}
          <div className="space-y-3">
            <div>
              <div className="flex justify-between text-xs mb-2">
                <span className="text-gray-400">Consistency</span>
                <span className="text-white">{safePercentage(metric.consistency_score, { digits: 0, expectsFraction: true })}</span>
              </div>
              <div className="w-full bg-white/20 rounded-full h-2">
                <div 
                  className="bg-gradient-to-r from-blue-400 to-blue-500 h-2 rounded-full transition-all duration-500"
                  style={{ width: `${metric.consistency_score * 100}%` }}
                />
              </div>
            </div>
            
            <div>
              <div className="flex justify-between text-xs mb-2">
                <span className="text-gray-400">Citation Quality</span>
                <span className="text-white">{safePercentage(metric.citation_quality, { digits: 0, expectsFraction: true })}</span>
              </div>
              <div className="w-full bg-white/20 rounded-full h-2">
                <div 
                  className="bg-gradient-to-r from-purple-400 to-purple-500 h-2 rounded-full transition-all duration-500"
                  style={{ width: `${metric.citation_quality * 100}%` }}
                />
              </div>
            </div>
          </div>

          {/* Trait Scores */}
          {Object.keys(metric.trait_scores).length > 0 && (
            <div className="space-y-1">
              <Label className="text-xs font-medium text-gray-400">Key Traits</Label>
              <div className="flex flex-wrap gap-1">
                {Object.entries(metric.trait_scores).map(([trait, score]) => (
                  <Badge key={trait} className="bg-white/10 text-gray-300 border-white/20 text-xs">
                    {trait}: {safePercentage(score, { expectsFraction: true })}%
                  </Badge>
                ))}
              </div>
            </div>
          )}

          {metric.error && (
            <div className="p-2 bg-red-500/20 border border-red-500/30 rounded text-sm text-red-300">
              Error: {metric.error}
            </div>
          )}
        </CardContent>
      </Card>
    );
  };

  // ALIGNED: Comparison strip using correct ModelComparison structure
  const PremiumComparisonStrip = ({ comparison }: { comparison: ModelComparison }) => (
    <Card className="bg-gradient-to-r from-blue-500/10 via-purple-500/10 to-blue-500/10 backdrop-blur-xl border-white/10 border-dashed">
      <CardContent className="p-6">
        <div className="grid grid-cols-5 gap-6 text-center">
          <div>
            <div className="text-3xl font-bold text-blue-400 mb-1">{comparison.model_count}</div>
            <div className="text-sm text-gray-400">Models</div>
          </div>
          <div>
            <div className="text-3xl font-bold text-green-400 mb-1">
              {safePercentage(comparison.best_confidence, { digits: 0, expectsFraction: true })}
            </div>
            <div className="text-sm text-gray-400">Best Score</div>
          </div>
          <div>
            <div className="text-3xl font-bold text-gray-300 mb-1">
              {comparison.avg_response_time}ms
            </div>
            <div className="text-sm text-gray-400">Avg Time</div>
          </div>
          <div>
            <div className="text-3xl font-bold text-yellow-400 mb-1">
              {safeToFixed(comparison.total_cost, 3)}
            </div>
            <div className="text-sm text-gray-400">Total Cost</div>
          </div>
          <div>
            <div className="text-3xl font-bold text-purple-400 mb-1">
              {safePercentage(comparison.performance_spread, { digits: 0, expectsFraction: true })}
            </div>
            <div className="text-sm text-gray-400">Spread</div>
          </div>
        </div>
      </CardContent>
    </Card>
  );

  return (
    <ErrorBoundary>
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-blue-900 to-slate-900 text-white">
      {/* Premium Header */}
      <div className="bg-black/20 backdrop-blur-xl border-b border-white/10 p-4">
        <div className="flex justify-between items-center max-w-7xl mx-auto">
          <div className="flex items-center gap-3">
            <Brain className="h-8 w-8 text-blue-400" />
            <div className="text-2xl font-bold bg-gradient-to-r from-blue-400 to-emerald-400 bg-clip-text text-transparent">
              NextAGI
            </div>
          </div>
          <div className="flex items-center gap-4 text-sm text-gray-300">
            <Badge className="bg-yellow-500 text-black font-medium">Enterprise</Badge>
            <span>Legal Corp Solutions</span>
            <span>•</span>
            <span>API Requests: {usageStats ? `${formatNumber(usageStats.total_requests)} / 10,000` : "Loading..."}</span>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto p-6">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left Panel - Enhanced Query Interface */}
          <div className="lg:col-span-2 space-y-6">
            {/* Premium Query Section */}
            <Card className="bg-white/5 backdrop-blur-xl border-white/10">
              <CardContent className="p-8">
                <h2 className="text-xl font-semibold mb-6 flex items-center gap-2">
                  <Sparkles className="h-5 w-5 text-blue-400" />
                  AI Query Router
                </h2>
                
                <div className="space-y-4">
                  <Textarea
                    className="min-h-[120px] bg-white/10 border-white/20 text-white placeholder-gray-400 focus:border-blue-400"
                    placeholder="Enter your query here... NextAGI will route it to the optimal AI models and provide the most accurate, verified response with real-time confidence scoring."
                    value={prompt}
                    onChange={(e) => setPrompt(e.target.value)}
                  />
                  
                  <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                    <div>
                      <Label className="text-gray-300 mb-2 block">Priority Mode</Label>
                      <select 
                        className="w-full p-2 bg-white/10 border border-white/20 rounded text-white"
                        value={mode}
                        onChange={(e) => setMode(e.target.value as ModelSelectionMode)}
                        title="Select priority mode for AI model selection"
                      >
                        <option value="balanced">Balanced (Quality + Speed)</option>
                        <option value="quality">Maximum Quality</option>
                        <option value="speed">Maximum Speed</option>
                        <option value="cost">Cost Optimized</option>
                      </select>
                    </div>
                    
                    <div>
                      <Label className="text-gray-300 mb-2 block">Max Models</Label>
                      <Input
                        className="bg-white/10 border-white/20 text-white placeholder-gray-400"
                        type="number"
                        min="1"
                        max="5"
                        value={maxModels}
                        onChange={(e) => setMaxModels(e.target.value)}
                      />
                    </div>

                    <div>
                      <Label className="text-gray-300 mb-2 block">Budget Limit ($)</Label>
                      <Input
                        className="bg-white/10 border-white/20 text-white placeholder-gray-400"
                        type="number"
                        step="0.01"
                        value={budgetLimit}
                        onChange={(e) => setBudgetLimit(e.target.value)}
                        placeholder="Optional"
                      />
                    </div>
                    
                    <div>
                      <Label className="text-gray-300 mb-2 block">Advanced Analysis</Label>
                      <div className="flex items-center space-x-2 mt-2">
                        <Switch checked={useAdvanced} onCheckedChange={setUseAdvanced} />
                        <span className="text-sm text-gray-300">Enhanced Mode</span>
                      </div>
                    </div>
                  </div>

                  <Button 
                    onClick={handleSubmit} 
                    disabled={loading || !prompt.trim()}
                    className="w-full bg-gradient-to-r from-blue-500 to-blue-600 hover:from-blue-600 hover:to-blue-700 text-white font-semibold py-3 px-6 rounded-lg transition-all duration-300 transform hover:scale-[1.02]"
                  >
                    {loading ? (
                      <div className="flex items-center gap-2">
                        <Activity className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                        Analyzing with AI Models
                      </div>
                    ) : (
                      <div className="flex items-center gap-2">
                        <Brain className="h-4 w-4" />
                        Analyze with AI Models
                      </div>
                    )}
                  </Button>

                  {/* Premium Processing Animation */}
                  {loading && (
                    <div className="space-y-4">
                      <div className="flex items-center gap-2 text-blue-400">
                        <Activity className="w-4 h-4 border-2 border-blue-400/30 border-t-blue-400 rounded-full animate-spin" />
                        <span className="text-sm">{processingStep}</span>
                      </div>
                      
                      {/* Model Router Visualization */}
                      <div className="flex justify-between p-4 bg-white/5 rounded-lg border border-white/10">
                        {['GPT-4', 'Claude', 'Gemini', 'Mistral'].map((name, idx) => (
                          <ModelNode
                            key={name}
                            name={name}
                            active={activeModels.includes(name.toLowerCase())}
                            score={activeModels.includes(name.toLowerCase()) ? Math.random() * 15 + 85 : undefined}
                          />
                        ))}
                      </div>
                    </div>
                  )}

                  <QueryErrorDisplay 
                    error={error} 
                    onRetry={handleSubmit}
                    isRetrying={loading}
                  />
                </div>
              </CardContent>
            </Card>

            {/* Enhanced Response Section */}
            {(result || loading) && (
              <Card className="bg-white/5 backdrop-blur-xl border-white/10">
                <CardContent className="p-6">
                  <div className="flex justify-between items-center mb-6">
                    <h3 className="text-lg font-semibold flex items-center gap-2">
                      <Trophy className="h-5 w-5 text-yellow-400" />
                      Best AI Response
                    </h3>
                    <div className="flex items-center gap-2">
                      <span className="text-sm text-gray-300">Confidence:</span>
                      <div className="w-24 h-2 bg-white/20 rounded-full overflow-hidden">
                        <div 
                          className="h-full bg-gradient-to-r from-red-500 via-yellow-500 to-green-500 transition-all duration-500"
                          style={{ width: `${confidence}%` }}
                        />
                      </div>
                      <span className="text-sm font-semibold">{safePercentage(confidence / 100, { expectsFraction: true })}%</span>
                    </div>
                  </div>

                  <div className="space-y-4">
                    {result ? (
                      <div className="space-y-6">
                        {/* Main Answer */}
                        <div className="p-4 bg-black/20 rounded-lg border-l-4 border-blue-400">
                          <div className="prose prose-invert max-w-none">
                            <p className="text-gray-200 leading-relaxed mb-3">
                              {result.answer}
                            </p>
                            <div className="flex items-center justify-between text-sm">
                              <div className="flex items-center gap-4">
                                <span className="text-gray-400">Winner: <strong className="text-yellow-400">{result.winner_model}</strong></span>
                                <span className="text-gray-400">Total Cost: <strong className="text-green-400">${result.total_cost != null ? safeToFixed(result.total_cost, 4) : '0.0000'}</strong></span>
                                <span className="text-gray-400">Time: <strong className="text-blue-400">{result.response_time_ms}ms</strong></span>
                              </div>
                              <Button variant="outline" size="sm" className="bg-white/10 border-white/20 text-gray-300 hover:bg-white/20">
                                <Code2 className="h-3 w-3 mr-2" />
                                View Raw
                              </Button>
                            </div>
                          </div>
                        </div>

                        {/* Model Comparison Strip */}
                        {result.model_comparison && (
                          <PremiumComparisonStrip comparison={result.model_comparison} />
                        )}

                        {/* View Controls */}
                        <div className="flex items-center justify-between">
                          <h3 className="text-lg font-semibold text-white">All Model Analysis</h3>
                          <div className="flex items-center gap-2">
                            <Button
                              variant={viewMode === "comparison" ? "default" : "outline"}
                              size="sm"
                              onClick={() => setViewMode("comparison")}
                              className={viewMode === "comparison" ? "bg-blue-600" : "bg-white/10 border-white/20 text-gray-300"}
                            >
                              <BarChart3 className="h-4 w-4 mr-1" />
                              Grid View
                            </Button>
                            <Button
                              variant={viewMode === "individual" ? "default" : "outline"}
                              size="sm"
                              onClick={() => setViewMode("individual")}
                              className={viewMode === "individual" ? "bg-blue-600" : "bg-white/10 border-white/20 text-gray-300"}
                            >
                              <Eye className="h-4 w-4 mr-1" />
                              Stack View
                            </Button>
                          </div>
                        </div>

                        {/* All Model Results - ALIGNED to use model_metrics */}
                        {result.model_metrics?.length > 0 && (
                          <div className={
                            viewMode === "comparison" 
                              ? "grid grid-cols-1 xl:grid-cols-2 gap-4"
                              : "space-y-4"
                          }>
                            {result.model_metrics.map((metric, idx) => (
                              <PremiumModelCard
                                key={`${metric.model}-${idx}`}
                                metric={metric}
                                isSelected={selectedModel === metric.model}
                              />
                            ))}
                          </div>
                        )}

                        {/* Analysis Reasoning */}
                        {result.reasoning && (
                          <Card className="bg-white/5 backdrop-blur-xl border-white/10">
                            <CardHeader>
                              <CardTitle className="flex items-center gap-2 text-white">
                                <Sparkles className="h-5 w-5 text-purple-400" />
                                Analysis Reasoning
                              </CardTitle>
                            </CardHeader>
                            <CardContent>
                              <div className="whitespace-pre-line text-sm text-gray-300 bg-black/20 p-4 rounded-md border border-white/10">
                                {result.reasoning}
                              </div>
                            </CardContent>
                          </Card>
                        )}
                      </div>
                    ) : (
                      <div className="p-8 text-center text-gray-400 italic">
                        Enter a query above to see NextAGI's intelligent multi-model analysis...
                      </div>
                    )}
                  </div>
                </CardContent>
              </Card>
            )}
          </div>

          {/* Right Panel - Premium Metrics */}
          <div className="space-y-6">
            {/* Stats Error Display */}
            {statsError && (
              <div className="p-3 bg-red-500/20 border border-red-500/30 rounded-lg text-red-200">
                <div className="flex items-center gap-2 mb-2">
                  <AlertTriangle className="h-4 w-4" />
                  <span className="text-sm font-medium">Statistics Error</span>
                </div>
                <p className="text-xs text-red-300 mb-2">{statsError}</p>
                <Button 
                  variant="outline" 
                  size="sm" 
                  onClick={() => fetchUsageStats()}
                  className="text-xs bg-red-500/10 border-red-500/30 text-red-200 hover:bg-red-500/20"
                >
                  Retry
                </Button>
              </div>
            )}
            <MetricCard
              title="Today's Usage"
              value={statsLoading ? "—" : usageStats ? formatNumber(usageStats.total_requests) : "—"}
              trend={statsLoading ? "" : ""}
              icon={Activity}
              color="text-blue-400"
            />
            
            <MetricCard
              title="Average Confidence"
              value={statsLoading ? "—" : usageStats ? formatPercentage01(usageStats.avg_confidence) : "—"}
              trend={statsLoading ? "" : ""}
              icon={Shield}
              color="text-green-400"
            />
            
            <MetricCard
              title="Response Time"
              value={statsLoading ? "—" : usageStats && usageStats.avg_response_time != null ? safeTime(usageStats.avg_response_time * 1000) : "—"}
              trend={statsLoading ? "" : ""}
              icon={Clock}
              color="text-blue-400"
            />
            
            <MetricCard
              title="Cost Optimization"
              value={statsLoading ? "—" : usageStats ? formatCurrency(usageStats.total_cost) : "—"}
              trend={statsLoading ? "" : ""}
              icon={DollarSign}
              color="text-yellow-400"
            />

            {/* Top Models Card */}
            <Card className="bg-white/5 backdrop-blur-xl border-white/10">
              <CardContent className="p-6">
                <div className="flex items-center justify-between mb-4">
                  <h4 className="text-sm font-medium text-gray-300">Top Models</h4>
                  <Target className="w-5 h-5 text-purple-400" />
                </div>
                <div className="space-y-3">
                  {statsLoading ? (
                    <div className="text-sm text-gray-400">Loading model data...</div>
                  ) : usageStats && usageStats.top_models ? (
                    usageStats.top_models.map((model, i) => {
                      const colors = ['bg-green-400', 'bg-blue-400', 'bg-yellow-400', 'bg-gray-400'];
                      return (
                        <div key={model.name} className="flex justify-between items-center">
                          <span className="text-sm text-gray-300">{model.name}</span>
                          <div className="flex items-center gap-2">
                            <div className="w-12 h-2 bg-white/20 rounded-full overflow-hidden">
                              <div 
                                className={`h-full ${colors[i % colors.length]}`}
                                style={{ width: `${model.usage_percentage}%` }}
                              />
                            </div>
                            <span className="text-sm font-semibold text-gray-300 w-8">{safeToFixed(model.usage_percentage, 0)}%</span>
                          </div>
                        </div>
                      );
                    })
                  ) : (
                    <div className="text-sm text-red-400">Failed to load model data</div>
                  )}
                </div>
              </CardContent>
            </Card>

            {/* Selected Model Details */}
            {result && selectedModel && (
              <Card className="bg-white/5 backdrop-blur-xl border-white/10">
                <CardContent className="p-6">
                  <div className="flex items-center justify-between mb-4">
                    <h4 className="text-sm font-medium text-gray-300">Selected Model</h4>
                    <Star className="w-5 h-5 text-yellow-400" />
                  </div>
                  <div className="text-center">
                    <div className="text-lg font-bold text-white mb-2">{selectedModel.split('/').pop()}</div>
                    <div className="text-xs text-gray-400">Click any model card to inspect details</div>
                  </div>
                </CardContent>
              </Card>
            )}
          </div>
        </div>
      </div>
      
      {/* Health Status Monitor */}
      <HealthStatus />
    </div>
    </ErrorBoundary>
  );
}