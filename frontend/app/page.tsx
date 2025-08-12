"use client";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { useEffect } from "react";

type Judgment = { judge_model: string; score01: number | null; label?: string; reasons: string; raw: string };
type Aggregate = { score_mean?: number; score_stdev?: number; vote_top_label?: string; vote_top_count?: number; vote_total?: number };
type Ranked = { model: string; aggregate: Aggregate; judgments: Judgment[] };
type RouteResult = { prompt: string; responses: { model: string; response?: string }[]; ranking: Ranked[]; winner: { model: string; score?: number | null } };

export default function Home() {
  const [prompt, setPrompt] = useState("");
  const [useAsk, setUseAsk] = useState(true);
  const [judgeModels, setJudgeModels] = useState(
    'openai/gpt-4, openai/gpt-4o, anthropic/claude-3-opus, anthropic/claude-3.5-sonnet, google/gemini-pro, mistral/mistral-large, meta/llama-3-70b-instruct'
  );
  const [result, setResult] = useState<RouteResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async () => {
    setError(null);
    setLoading(true);
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
    } catch (e: any) {
      setError(e.message ?? "Unknown error");
    } finally {
      setLoading(false);
    }
  };

  const RankingTable = ({ ranking }: { ranking: Ranked[] }) => (
    <div className="overflow-x-auto rounded-xl border border-zinc-700">
      <table className="w-full text-sm">
        <thead className="bg-zinc-800 text-zinc-100">
          <tr>
            <th className="p-2 text-left">Model</th>
            <th className="p-2 text-left">Score (mean)</th>
            <th className="p-2 text-left">Votes</th>
          </tr>
        </thead>
        <tbody className="bg-zinc-900 text-zinc-100">
          {ranking.map((r) => (
            <tr key={r.model} className="border-t border-zinc-700">
              <td className="p-2 font-medium">{r.model}</td>
              <td className="p-2">{r.aggregate.score_mean?.toFixed(3) ?? "—"}</td>
              <td className="p-2">
                {r.aggregate.vote_top_label
                  ? `${r.aggregate.vote_top_label} (${r.aggregate.vote_top_count}/${r.aggregate.vote_total})`
                  : "—"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );

  return (
    <main className="p-6 max-w-4xl mx-auto space-y-6">
      <Card>
        <CardContent className="space-y-4 p-4">
          <Label htmlFor="prompt">Prompt</Label>
          <Textarea id="prompt" value={prompt} onChange={(e) => setPrompt(e.target.value)} />

          <div className="flex items-center gap-4">
            <Label htmlFor="judge_models">Judge Models (comma-separated)</Label>
            <Input id="judge_models" value={judgeModels} onChange={(e) => setJudgeModels(e.target.value)} />
          </div>

          <div className="flex items-center justify-between">
            <Label htmlFor="useAsk">Use Ask</Label>
            <Switch id="useAsk" checked={useAsk} onCheckedChange={setUseAsk} />
          </div>

          <Button onClick={handleSubmit} disabled={loading || !judgeModels.trim()}>
            {loading ? "Evaluating..." : "Evaluate"}
          </Button>
          {error && <p className="text-red-400 text-sm">{error}</p>}
        </CardContent>
      </Card>

      {result && (
        <div className="space-y-4">
          <h2 className="text-xl font-bold">Results</h2>

          {result.ranking?.length > 0 && <RankingTable ranking={result.ranking} />}

          <pre className="bg-zinc-900 text-zinc-100 border border-zinc-700 p-4 rounded-xl text-sm overflow-x-auto">
            {JSON.stringify(result, null, 2)}
          </pre>
        </div>
      )}
    </main>
  );
}

