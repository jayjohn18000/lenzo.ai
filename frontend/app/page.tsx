// frontend/app/page.tsx - LANDING PAGE WITH QUICK CHAT
"use client";

import { useState, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { 
  Brain, 
  Sparkles, 
  ArrowRight, 
  BarChart3,
  Shield,
  Zap,
  Target
} from "lucide-react";

import { QueryRequest, ModelSelectionMode } from "@/types/api";
import { apiClient } from "@/lib/api/unified-client";
import ComprehensiveErrorBoundary from "@/components/ComprehensiveErrorBoundary";
import { isDevelopment } from "@/lib/env-config";

export default function NextAGILanding() {
  const [prompt, setPrompt] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<string | null>(null);

  const handleQuickQuery = useCallback(async () => {
    if (!prompt.trim()) return;
    
    setLoading(true);
    setResult(null);

    try {
      const requestBody: QueryRequest = {
        prompt: prompt.trim(),
        mode: "balanced" as ModelSelectionMode,
        max_models: 3,
        include_reasoning: false,
      };

      console.log("🚀 Quick query:", requestBody);
      
      const data = await apiClient.query(requestBody);
      setResult(data.answer);
      
    } catch (err: any) {
      console.error("❌ Quick query failed:", err);
      setResult(`Error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  }, [prompt]);

  return (
    <ComprehensiveErrorBoundary showDetails={isDevelopment}>
      <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50">
        {/* Header */}
        <header className="bg-white/80 backdrop-blur-sm border-b border-gray-200">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex items-center justify-between py-6">
              <div className="flex items-center space-x-3">
                <Brain className="h-10 w-10 text-blue-600" />
                <div>
                  <h1 className="text-3xl font-bold text-gray-900">NextAGI</h1>
                  <p className="text-sm text-gray-600">Multi-Model AI Platform</p>
                </div>
              </div>
              <div className="flex items-center space-x-4">
                <Badge variant="outline" className="text-sm bg-green-50 text-green-700 border-green-200">
                  Enterprise Ready
                </Badge>
                <Button 
                  variant="outline" 
                  size="sm"
                  onClick={() => window.location.href = '/dashboard'}
                >
                  <BarChart3 className="h-4 w-4 mr-2" />
                  Dashboard
                </Button>
              </div>
            </div>
          </div>
        </header>

        {/* Hero Section */}
        <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
          <div className="text-center mb-12">
            <h2 className="text-4xl font-bold text-gray-900 mb-4">
              Get the Best Answer from Multiple AI Models
            </h2>
            <p className="text-xl text-gray-600 max-w-3xl mx-auto">
              NextAGI routes your query to the optimal AI models, compares responses, 
              and delivers the most accurate answer with confidence scoring.
            </p>
          </div>

          {/* Quick Chat Interface */}
          <div className="max-w-4xl mx-auto mb-12">
            <Card className="shadow-lg border-0 bg-white/80 backdrop-blur-sm">
              <CardHeader className="text-center pb-4">
                <CardTitle className="flex items-center justify-center gap-2 text-2xl">
                  <Sparkles className="h-6 w-6 text-blue-600" />
                  Quick AI Query
                </CardTitle>
                <p className="text-gray-600">
                  Ask anything and get the best answer from multiple AI models
                </p>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="space-y-2">
                  <Textarea
                    className="min-h-[120px] resize-none text-lg"
                    placeholder="What would you like to know? Ask anything..."
                    value={prompt}
                    onChange={(e) => setPrompt(e.target.value)}
                  />
                </div>

                <div className="flex justify-center">
                  <Button 
                    onClick={handleQuickQuery} 
                    disabled={loading || !prompt.trim()}
                    size="lg"
                    className="bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white px-8 py-3 text-lg"
                  >
                    {loading ? (
                      <div className="flex items-center gap-2">
                        <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                        Analyzing with AI Models...
                      </div>
                    ) : (
                      <div className="flex items-center gap-2">
                        <Brain className="h-5 w-5" />
                        Get Best Answer
                        <ArrowRight className="h-5 w-5" />
                      </div>
                    )}
                  </Button>
                </div>

                {/* Result */}
                {result && (
                  <Card className="bg-gradient-to-r from-green-50 to-blue-50 border-green-200">
                    <CardContent className="p-6">
                      <div className="flex items-start gap-3">
                        <div className="p-2 bg-green-100 rounded-full">
                          <Target className="h-5 w-5 text-green-600" />
                        </div>
                        <div className="flex-1">
                          <h4 className="font-semibold text-green-800 mb-2">Best Answer</h4>
                          <p className="text-gray-700 leading-relaxed">{result}</p>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                )}
              </CardContent>
            </Card>
          </div>

          {/* Features Grid */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8 mb-12">
            <Card className="text-center p-6 bg-white/60 backdrop-blur-sm border-0">
              <div className="p-3 bg-blue-100 rounded-full w-fit mx-auto mb-4">
                <Shield className="h-8 w-8 text-blue-600" />
              </div>
              <h3 className="text-xl font-semibold mb-2">Reliability</h3>
              <p className="text-gray-600">
                Multiple AI models ensure accuracy with confidence scoring and hallucination detection.
              </p>
            </Card>

            <Card className="text-center p-6 bg-white/60 backdrop-blur-sm border-0">
              <div className="p-3 bg-purple-100 rounded-full w-fit mx-auto mb-4">
                <Zap className="h-8 w-8 text-purple-600" />
              </div>
              <h3 className="text-xl font-semibold mb-2">Speed</h3>
              <p className="text-gray-600">
                Optimized routing and parallel processing deliver fast responses without compromising quality.
              </p>
            </Card>

            <Card className="text-center p-6 bg-white/60 backdrop-blur-sm border-0">
              <div className="p-3 bg-green-100 rounded-full w-fit mx-auto mb-4">
                <BarChart3 className="h-8 w-8 text-green-600" />
              </div>
              <h3 className="text-xl font-semibold mb-2">Analytics</h3>
              <p className="text-gray-600">
                Comprehensive dashboard with usage metrics, model performance, and cost optimization.
              </p>
            </Card>
          </div>

          {/* CTA Section */}
          <div className="text-center">
            <Card className="bg-gradient-to-r from-blue-600 to-purple-600 text-white border-0">
              <CardContent className="p-8">
                <h3 className="text-2xl font-bold mb-4">Ready for Enterprise?</h3>
                <p className="text-blue-100 mb-6 max-w-2xl mx-auto">
                  Access advanced analytics, custom model configurations, and enterprise-grade reliability 
                  with our comprehensive dashboard.
                </p>
                <Button 
                  variant="secondary" 
                  size="lg"
                  onClick={() => window.location.href = '/dashboard'}
                  className="bg-white text-blue-600 hover:bg-gray-100 px-8 py-3"
                >
                  <BarChart3 className="h-5 w-5 mr-2" />
                  Open Dashboard
                </Button>
              </CardContent>
            </Card>
          </div>
        </main>

        {/* Footer */}
        <footer className="bg-gray-50 border-t border-gray-200 mt-16">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
            <div className="text-center text-gray-600">
              <p>&copy; 2025 NextAGI. Enterprise-grade multi-model AI platform.</p>
            </div>
          </div>
        </footer>
      </div>
    </ComprehensiveErrorBoundary>
  );
}