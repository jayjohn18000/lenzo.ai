# backend/judge/pipelines/runner.py
import time
from typing import Dict
from backend.judge.schemas import RouteRequest
from backend.judge.policy.dispatcher import should_escalate_after_prepass
from backend.judge.pipelines.judge import run_judge
from backend.judge.pipelines.tool_chain import run_tool_chain


async def run_pipeline(pipeline_id: str, req: RouteRequest, trace_id: str) -> Dict:
    """
    Execute the selected pipeline with proper metrics tracking.
    """
    start_time = time.perf_counter()
    
    if pipeline_id == "judge":
        judge_result = await run_judge(req, trace_id)
        conf = judge_result.get("confidence")

        # Adaptive escalation: if the judge pre-pass lacks confidence, rerun via tool_chain
        if should_escalate_after_prepass(conf, req):
            tool_result = await run_tool_chain(req, trace_id)
            # Merge metrics from both pipelines
            tool_result.setdefault("citations", [])
            tool_result["response_time_ms"] = int((time.perf_counter() - start_time) * 1000)
            # Combine models attempted from both pipelines
            judge_models = judge_result.get("models_attempted", [])
            tool_models = tool_result.get("models_attempted", [])
            tool_result["models_attempted"] = list(set(judge_models + tool_models))
            return tool_result

        judge_result.setdefault("citations", [])
        judge_result["response_time_ms"] = int((time.perf_counter() - start_time) * 1000)
        return judge_result

    if pipeline_id == "tool_chain":
        tool_result = await run_tool_chain(req, trace_id)
        tool_result.setdefault("citations", [])
        tool_result["response_time_ms"] = int((time.perf_counter() - start_time) * 1000)
        return tool_result

    raise ValueError(f"Unknown pipeline_id: {pipeline_id}")