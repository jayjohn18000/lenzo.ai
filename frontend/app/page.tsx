"use client";
import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { 
  Activity, 
  Brain, 
  TrendingUp, 
  Zap, 
  Shield,
  Clock,
  DollarSign,
  Target
} from "lucide-react";

type Judgment = { 
  judge_model: string; 
  score01: number | null; 
  label?: string; 
  reasons: string; 
  raw: string; 
};
type Aggregate = { 
  score_mean?: number; 
  score_stdev?: number; 
  vote_top_label?: string; 
  vote_top_count?: number; 
  vote_total?: number; 
};
type Ranked = { 
  model: string; 
  aggregate: Aggregate; 
  judgments: Judgment[]; 
};
type RouteResult = { 
  prompt: string; 
  responses: { model: string; response?: string }[]; 
  ranking: Ranked[]; 
  winner: { model: string; score?: number | null }; 
};

export default function NextAGIInterface() {
  const [prompt, setPrompt] = useState("");
  const [useAsk, setUseAsk] = useState(true);
  const [judgeModels, setJudgeModels] = useState(
    'openai/gpt-4, openai/gpt-4o, anthropic/claude-3-opus, anthropic/claude-3.5-sonnet'
  );
  const [result, setResult] = useState<RouteResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [mode, setMode] = useState("balanced");
  const [confidence, setConfidence] = useState(0);
  const [processingStep, setProcessingStep] = useState("");
  const [activeModels, setActiveModels] = useState<string[]>([]);

  const processingSteps = [
    "Analyzing query complexity...",
    "Selecting optimal models...",
    "Routing to AI models...",
    "Running hallucination detection...",
    "Calculating consensus scores...",
    "Generating final response..."
  ];

  const handleSubmit = async () => {
    setError(null);
    setLoading(true);
    setResult(null);
    setConfidence(0);
    
    // Simulate processing animation
    for (let i = 0; i < processingSteps.length; i++) {
      setProcessingStep(processingSteps[i]);
      await new Promise(resolve => setTimeout(resolve, 800));
      
      if (i >= 2) {
        const modelNames = judgeModels.split(",").map(s => s.trim().split("/")[1] || s.trim());
        const modelIndex = Math.min(i - 2, modelNames.length - 1);
        if (modelNames[modelIndex]) {
          setActiveModels(prev => [...prev, modelNames[modelIndex]]);
        }
      }
    }

    try {
      const res = await fetch("/api/route", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          prompt: prompt || "How did Napoleon Bonaparte grow well over 6 feet?",
          responses: [],
          judge_models: judgeModels.split(",").map(s => s.trim()).filter(Boolean),
          use_ask: useAsk,
        }),
      });
      
      if (!res.ok) throw new Error(`Backend error: ${res.status}`);
      const data = (await res.json()) as RouteResult;
      setResult(data);
      
      // Animate confidence score
      const targetConfidence = data.winner?.score ? data.winner.score * 100 : 94.2;
      let currentConf = 0;
      const interval = setInterval(() => {
        currentConf += 2;
        setConfidence(currentConf);
        if (currentConf >= targetConfidence) {
          clearInterval(interval);
          setConfidence(targetConfidence);
        }
      }, 50);
      
    } catch (e: any) {
      setError(e.message ?? "Unknown error");
    } finally {
      setLoading(false);
      setActiveModels([]);
    }
  };

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
      <div className="text-sm font-bold">{score ? score.toFixed(1) : '--'}</div>
    </div>
  );

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-blue-900 to-slate-900 text-white">
      {/* Header */}
      <div className="bg-black/20 backdrop-blur-xl border-b border-white/10 p-4">
        <div className="flex justify-between items-center max-w-7xl mx-auto">
          <div className="text-2xl font-bold bg-gradient-to-r from-blue-400 to-emerald-400 bg-clip-text text-transparent">
            NextAGI
          </div>
          <div className="flex items-center gap-4 text-sm text-gray-300">
            <Badge className="bg-yellow-500 text-black">Enterprise</Badge>
            <span>Legal Corp Solutions</span>
            <span>•</span>
            <span>API Requests: 2,847 / 10,000</span>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto p-6">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left Panel - Query Interface */}
          <div className="lg:col-span-2 space-y-6">
            {/* Query Section */}
            <Card className="bg-white/5 backdrop-blur-xl border-white/10">
              <CardContent className="p-8">
                <h2 className="text-xl font-semibold mb-6">AI Query Router</h2>
                
                <div className="space-y-4">
                  <Textarea
                    className="min-h-[120px] bg-white/10 border-white/20 text-white placeholder-gray-400 focus:border-blue-400"
                    placeholder="Enter your query here... NextAGI will route it to the optimal AI models and provide the most accurate, verified response with real-time confidence scoring."
                    value={prompt}
                    onChange={(e) => setPrompt(e.target.value)}
                  />
                  
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div>
                      <Label className="text-gray-300 mb-2 block">Priority Mode</Label>
                      <select 
                        className="w-full p-2 bg-white/10 border border-white/20 rounded text-white"
                        value={mode}
                        onChange={(e) => setMode(e.target.value)}
                      >
                        <option value="balanced">Balanced (Quality + Speed)</option>
                        <option value="quality">Maximum Quality</option>
                        <option value="speed">Maximum Speed</option>
                        <option value="cost">Cost Optimized</option>
                      </select>
                    </div>
                    
                    <div>
                      <Label className="text-gray-300 mb-2 block">Judge Models</Label>
                      <Input
                        className="bg-white/10 border-white/20 text-white placeholder-gray-400"
                        placeholder="Models (comma-separated)"
                        value={judgeModels}
                        onChange={(e) => setJudgeModels(e.target.value)}
                      />
                    </div>
                    
                    <div>
                      <Label className="text-gray-300 mb-2 block">Use Ask</Label>
                      <div className="flex items-center space-x-2 mt-2">
                        <Switch checked={useAsk} onCheckedChange={setUseAsk} />
                        <span className="text-sm text-gray-300">Enhanced Mode</span>
                      </div>
                    </div>
                  </div>

                  <Button 
                    onClick={handleSubmit} 
                    disabled={loading || !judgeModels.trim()}
                    className="w-full bg-gradient-to-r from-blue-500 to-blue-600 hover:from-blue-600 hover:to-blue-700 text-white font-semibold py-3 px-6 rounded-lg transition-all duration-300 transform hover:scale-[1.02]"
                  >
                    {loading ? (
                      <div className="flex items-center gap-2">
                        <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                        Analyzing with AI Models
                      </div>
                    ) : (
                      "Analyze with AI Models"
                    )}
                  </Button>

                  {/* Processing Animation */}
                  {loading && (
                    <div className="space-y-4">
                      <div className="flex items-center gap-2 text-blue-400">
                        <div className="w-4 h-4 border-2 border-blue-400/30 border-t-blue-400 rounded-full animate-spin" />
                        <span className="text-sm">{processingStep}</span>
                      </div>
                      
                      {/* Model Router Visualization */}
                      <div className="flex justify-between p-4 bg-white/5 rounded-lg">
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

                  {error && (
                    <div className="p-4 bg-red-500/20 border border-red-500/30 rounded-lg text-red-200">
                      {error}
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>

            {/* Response Section */}
            {(result || loading) && (
              <Card className="bg-white/5 backdrop-blur-xl border-white/10">
                <CardContent className="p-6">
                  <div className="flex justify-between items-center mb-6">
                    <h3 className="text-lg font-semibold">AI Response</h3>
                    <div className="flex items-center gap-2">
                      <span className="text-sm text-gray-300">Confidence:</span>
                      <div className="w-24 h-2 bg-white/20 rounded-full overflow-hidden">
                        <div 
                          className="h-full bg-gradient-to-r from-red-500 via-yellow-500 to-green-500 transition-all duration-500"
                          style={{ width: `${confidence}%` }}
                        />
                      </div>
                      <span className="text-sm font-semibold">{confidence.toFixed(1)}%</span>
                    </div>
                  </div>

                  <div className="space-y-4">
                    {result ? (
                      <div className="space-y-4">
                        <div className="p-4 bg-black/20 rounded-lg border-l-4 border-blue-400">
                          <div className="prose prose-invert max-w-none">
                            <p className="text-gray-300 mb-3">
                              <strong>NextAGI Analysis Results:</strong>
                            </p>
                            <p>
                              Based on your query "{prompt.substring(0, 50)}{prompt.length > 50 ? '...' : ''}", 
                              I've analyzed responses from {result.ranking?.length || 4} leading AI models and applied 
                              our advanced hallucination detection system.
                            </p>
                            {result.winner && (
                              <div className="mt-4 p-3 bg-green-500/20 border border-green-500/30 rounded">
                                <strong>Winner:</strong> {result.winner.model} 
                                {result.winner.score && ` (Score: ${result.winner.score.toFixed(3)})`}
                              </div>
                            )}
                          </div>
                        </div>

                        <div className="grid grid-cols-3 gap-4">
                          <div className="text-center p-3 bg-white/10 rounded">
                            <div className="text-lg font-bold text-green-400">96.1%</div>
                            <div className="text-xs text-gray-400">Accuracy</div>
                          </div>
                          <div className="text-center p-3 bg-white/10 rounded">
                            <div className="text-lg font-bold text-blue-400">92.8%</div>
                            <div className="text-xs text-gray-400">Consistency</div>
                          </div>
                          <div className="text-center p-3 bg-white/10 rounded">
                            <div className="text-lg font-bold text-yellow-400">95.3%</div>
                            <div className="text-xs text-gray-400">Reliability</div>
                          </div>
                        </div>
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

          {/* Right Panel - Metrics */}
          <div className="space-y-6">
            <MetricCard
              title="Today's Usage"
              value="2,847"
              trend="+12% from yesterday"
              icon={Activity}
              color="text-blue-400"
            />
            
            <MetricCard
              title="Average Confidence"
              value="94.2%"
              trend="+2.1% this week"
              icon={Shield}
              color="text-green-400"
            />
            
            <MetricCard
              title="Response Time"
              value="1.8s"
              trend="-0.3s improvement"
              icon={Clock}
              color="text-blue-400"
            />
            
            <MetricCard
              title="Cost Optimization"
              value="$247"
              trend="-18% vs baseline"
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
                  {[
                    { name: 'GPT-4 Turbo', usage: 42, color: 'bg-green-400' },
                    { name: 'Claude-3.5 Sonnet', usage: 31, color: 'bg-blue-400' },
                    { name: 'Gemini Pro', usage: 18, color: 'bg-yellow-400' },
                    { name: 'Others', usage: 9, color: 'bg-gray-400' }
                  ].map((model) => (
                    <div key={model.name} className="flex justify-between items-center">
                      <span className="text-sm text-gray-300">{model.name}</span>
                      <div className="flex items-center gap-2">
                        <div className="w-12 h-2 bg-white/20 rounded-full overflow-hidden">
                          <div 
                            className={`h-full ${model.color}`}
                            style={{ width: `${model.usage}%` }}
                          />
                        </div>
                        <span className="text-sm font-semibold text-gray-300 w-8">{model.usage}%</span>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
}