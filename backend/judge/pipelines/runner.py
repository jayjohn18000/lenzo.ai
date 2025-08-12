# backend/judge/pipelines/runner.py
from typing import Dict
from backend.judge.schemas import RouteRequest
from backend.judge.policy.dispatcher import should_escalate_after_prepass
from backend.judge.pipelines.judge import run_judge
from backend.judge.pipelines.tool_chain import run_tool_chain


async def run_pipeline(pipeline_id: str, req: RouteRequest, trace_id: str) -> Dict:
    """
    Execute the selected pipeline. If 'judge' is chosen and the pre-pass confidence
    comes back below the configured threshold, escalate to 'tool_chain'.
    """
    if pipeline_id == "judge":
        judge_result = await run_judge(req, trace_id)
        conf = judge_result.get("confidence")

        # Adaptive escalation: if the judge pre-pass lacks confidence, rerun via tool_chain
        if should_escalate_after_prepass(conf, req):
            tool_result = await run_tool_chain(req, trace_id)
            # always ensure citations key exists
            tool_result.setdefault("citations", [])
            return tool_result

        judge_result.setdefault("citations", [])
        return judge_result

    if pipeline_id == "tool_chain":
        tool_result = await run_tool_chain(req, trace_id)
        tool_result.setdefault("citations", [])
        return tool_result

    raise ValueError(f"Unknown pipeline_id: {pipeline_id}")
