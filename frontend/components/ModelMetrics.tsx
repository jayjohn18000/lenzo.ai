// frontend/app/dashboard/components/ModelMetrics.tsx
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { 
  safeToFixed, 
  safeCurrency, 
  safePercentage, 
  safeTime,
  ensureNumeric 
} from "@/lib/safe-formatters";
import type { ModelMetrics } from "@/lib/api/schemas";

interface ModelMetricsCardProps {
  metrics: ModelMetrics[];
  loading?: boolean;
  winner?: string;
}

export function ModelMetricsCard({ metrics, loading, winner }: ModelMetricsCardProps) {
  if (loading) {
    return <ModelMetricsCardSkeleton />;
  }

  if (!metrics || metrics.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Model Performance</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground">No model metrics available</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Model Performance Comparison</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {metrics.map((metric, index) => {
          const isWinner = metric.model === winner;
          const confidence = ensureNumeric(metric.confidence);
          const reliability = ensureNumeric(metric.reliability_score);
          
          return (
            <div key={index} className="space-y-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="font-medium">{metric.model}</span>
                  {isWinner && (
                    <Badge variant="default" className="text-xs">
                      Winner
                    </Badge>
                  )}
                </div>
                <span className="text-sm text-muted-foreground">
                  {safeCurrency(metric.cost, 4)}
                </span>
              </div>

              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <div className="flex justify-between mb-1">
                    <span className="text-muted-foreground">Confidence</span>
                    <span className="font-medium">{safePercentage(confidence)}</span>
                  </div>
                  <Progress value={confidence * 100} className="h-2" />
                </div>

                <div>
                  <div className="flex justify-between mb-1">
                    <span className="text-muted-foreground">Response Time</span>
                    <span className="font-medium">
                      {safeTime(metric.response_time_ms, 'ms', 0)}
                    </span>
                  </div>
                </div>
              </div>

              {/* Additional metrics */}
              <div className="grid grid-cols-3 gap-2 text-xs">
                <MetricBadge
                  label="Reliability"
                  value={reliability}
                  format="percentage"
                />
                <MetricBadge
                  label="Hallucination Risk"
                  value={metric.hallucination_risk}
                  format="percentage"
                  inverse
                />
                <MetricBadge
                  label="Citation Quality"
                  value={metric.citation_quality}
                  format="percentage"
                />
              </div>
            </div>
          );
        })}
      </CardContent>
    </Card>
  );
}

interface MetricBadgeProps {
  label: string;
  value: number | undefined;
  format?: 'percentage' | 'number';
  inverse?: boolean;
}

function MetricBadge({ label, value, format = 'percentage', inverse }: MetricBadgeProps) {
  const numValue = ensureNumeric(value);
  const displayValue = inverse ? 1 - numValue : numValue;
  
  const variant = getVariant(displayValue, inverse);
  const formatted = format === 'percentage' 
    ? safePercentage(displayValue, 0) 
    : safeToFixed(displayValue, 2);

  return (
    <div className="flex flex-col items-center p-2 rounded-md bg-muted/50">
      <span className="text-xs text-muted-foreground">{label}</span>
      <Badge variant={variant} className="mt-1">
        {formatted}
      </Badge>
    </div>
  );
}

function getVariant(value: number, inverse?: boolean): "default" | "secondary" | "destructive" {
  const threshold = inverse ? 0.3 : 0.7;
  const warningThreshold = inverse ? 0.5 : 0.5;
  
  if (value >= threshold) return "default";
  if (value >= warningThreshold) return "secondary";
  return "destructive";
}

function ModelMetricsCardSkeleton() {
  return (
    <Card>
      <CardHeader>
        <div className="h-6 w-48 bg-muted animate-pulse rounded" />
      </CardHeader>
      <CardContent className="space-y-4">
        {[...Array(3)].map((_, i) => (
          <div key={i} className="space-y-2">
            <div className="flex items-center justify-between">
              <div className="h-4 w-32 bg-muted animate-pulse rounded" />
              <div className="h-4 w-16 bg-muted animate-pulse rounded" />
            </div>
            <div className="h-2 w-full bg-muted animate-pulse rounded" />
          </div>
        ))}
      </CardContent>
    </Card>
  );
}