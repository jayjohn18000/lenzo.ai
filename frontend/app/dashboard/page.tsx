// frontend/app/dashboard/page.tsx - ALIGNED WITH BACKEND API
"use client";

import { safeToFixed, safeCurrency, safeTime } from '@/lib/safe-formatters';
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import {
  Brain,
  BarChart3,
  FileText,
  Target,
  CheckCircle,
  AlertTriangle,
  Activity,
  DollarSign,
  Clock
} from "lucide-react";

// ALIGNED: Import updated types
import { ModelMetrics, DisplayModelMetrics } from "@/types/api";
import ComprehensiveErrorBoundary from "@/components/ComprehensiveErrorBoundary";
import { useTodayStats, useUsageStats } from "@/hooks/use-stats";
import { useModelPerformance } from "@/hooks/use-models";
import { useJobStats } from "@/hooks/use-jobs";
import { isDevelopment } from "@/lib/env-config";
import { ThemeToggle } from "@/components/ui/theme-toggle";

export default function Dashboard() {

  // Real-time data hooks
  const { data: todayStats, loading: todayLoading, error: todayError } = useTodayStats();
  const { data: usageStats, loading: usageLoading, error: usageError } = useUsageStats(7);
  const { data: modelPerformance, loading: modelLoading, error: modelError } = useModelPerformance();
  const { data: jobStats, loading: jobLoading, error: jobError } = useJobStats();

  // ALIGNED: Helper functions for data formatting
  const formatNumber = (num: number): string => {
    if (num >= 1_000_000) return `${safeToFixed(num / 1_000_000, 1)}M`;
    if (num >= 1_000) return `${safeToFixed(num / 1_000, 1)}K`;
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
    // Input is already a 0-1 fraction, convert to percentage
    const percentage = value01 * 100;
    const bounded = Math.max(0, Math.min(100, percentage));
    return `${safeToFixed(bounded, 1)}%`;
  };

  const formatTimeMs = (ms: number): string => {
    if (ms >= 1000) return `${safeTime(ms / 1000)}s`;
    return `${Math.round(ms)}ms`;
  };

  // ALIGNED: Convert ModelMetrics to DisplayModelMetrics for UI
  const convertToDisplayMetrics = (metrics: ModelMetrics[]): DisplayModelMetrics[] => {
    return metrics.map(metric => ({
      model: metric.model,
      score: metric.confidence, // Keep as 0-1 fraction for safePercentage
      responseTimeMs: metric.response_time_ms,
      reliabilityPct: metric.reliability_score, // Keep as 0-1 fraction for safePercentage
      cost: metric.cost,
      isWinner: metric.is_winner,
      error: metric.error
    }));
  };


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
    <ComprehensiveErrorBoundary showDetails={isDevelopment}>
      <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="bg-card shadow-sm border-b border-border">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between py-4">
            <div className="flex items-center space-x-3">
              <Brain className="h-8 w-8 text-primary" />
              <h1 className="text-2xl font-bold text-foreground">NextAGI Dashboard</h1>
            </div>
            <div className="flex items-center space-x-4">
              <ThemeToggle />
              <Badge variant="outline" className="text-sm">
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
                  <p className="text-sm text-muted-foreground">Today's Queries</p>
                  <p className="text-2xl font-bold text-foreground">
                    {todayLoading ? "—" : todayStats ? formatNumber(todayStats.requests) : "0"}
                  </p>
                </div>
                <BarChart3 className="h-8 w-8 text-primary" />
              </div>
              {todayError && <p className="mt-2 text-xs text-red-500">{todayError}</p>}
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Today's Cost</p>
                  <p className="text-2xl font-bold text-foreground">
                    {todayLoading ? "—" : todayStats ? formatCurrency(todayStats.cost) : "$0.00"}
                  </p>
                </div>
                <DollarSign className="h-8 w-8 text-primary" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Avg Confidence</p>
                  <p className="text-2xl font-bold text-foreground">
                    {todayLoading ? "—" : todayStats ? formatPercentage01(todayStats.avg_confidence) : "0%"}
                  </p>
                </div>
                <Target className="h-8 w-8 text-primary" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Worker Status</p>
                  <p className="text-2xl font-bold text-foreground">
                    {jobLoading ? "—" : jobStats ? (jobStats.worker_active ? "Active" : "Inactive") : "Unknown"}
                  </p>
                </div>
                <Activity className="h-8 w-8 text-primary" />
              </div>
              {jobError && <p className="mt-2 text-xs text-red-500">{jobError}</p>}
            </CardContent>
          </Card>
        </div>

        {/* Quick Access to Chat */}
        <Card className="mb-8 bg-accent border-border">
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-lg font-semibold text-foreground mb-2">Need to Ask AI Models?</h3>
                <p className="text-muted-foreground">
                  Use our quick chat interface for immediate AI responses with multi-model analysis.
                </p>
              </div>
              <Button 
                onClick={() => window.location.href = '/'}
              >
                <Brain className="h-4 w-4 mr-2" />
                Open Chat
              </Button>
            </div>
          </CardContent>
        </Card>


        {/* Model Performance Stats */}
        {modelPerformance && modelPerformance.top_models?.length > 0 && (
          <Card>
            <CardHeader>
              <CardTitle>Top Models Performance</CardTitle>
              <CardDescription>Based on {modelPerformance.period_days} days of data</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {modelPerformance.top_models.map((model, i) => (
                  <div key={i} className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <span className="font-medium">{model.name}</span>
                      <span className="text-sm text-muted-foreground">{model.usage_percentage}% usage</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="w-20 h-2 bg-muted rounded-full overflow-hidden">
                        <div
                          className="h-full bg-primary transition-all duration-300"
                          style={{ width: `${model.usage_percentage}%` }}
                        />
                      </div>
                      <span className="text-sm font-medium">{formatPercentage01(model.avg_score)}</span>
                    </div>
                  </div>
                ))}
              </div>
              {modelError && <p className="mt-2 text-xs text-red-500">{modelError}</p>}
            </CardContent>
          </Card>
        )}

      </main>
      </div>
    </ComprehensiveErrorBoundary>
  );
}