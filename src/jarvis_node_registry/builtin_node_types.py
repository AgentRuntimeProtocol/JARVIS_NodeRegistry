from __future__ import annotations

from typing import Any

from arp_standard_model import Extensions, NodeKind, NodeType


def builtin_node_types(*, version: str) -> list[NodeType]:
    """
    Built-in NodeTypes seeded by the Node Registry on startup.

    These are metadata-only definitions. The executable logic for composite planner
    nodes lives in the Composite Executor (CE).
    """

    planner_input_schema: dict[str, Any] = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "goal": {"type": ["string", "null"], "description": "High-level goal to plan/execute."},
            "prompt": {"type": ["string", "null"], "description": "Alias for goal (legacy/compat)."},
            "context": {
                "type": ["string", "null"],
                "description": "Optional JSON-encoded context object for planning. Must not include secrets.",
            },
            "max_steps": {"type": ["integer", "null"], "minimum": 1, "description": "Hard cap on planned steps."},
            "max_depth": {
                "type": ["integer", "null"],
                "minimum": 0,
                "description": "Hard cap on planning recursion depth.",
            },
            "depth": {"type": ["integer", "null"], "minimum": 0, "description": "Current composite depth."},
        },
        "required": ["goal", "prompt", "context", "max_steps", "max_depth", "depth"],
    }

    # Metadata-only placeholder: outputs are produced by the Composite Executor (CE).
    planner_output_schema: dict[str, Any] = {
        "type": "object",
        "additionalProperties": False,
        "properties": {},
        "required": [],
    }

    return [
        NodeType(
            node_type_id="jarvis.composite.planner.general",
            version=version,
            kind=NodeKind.composite,
            description="General-purpose composite planner node (metadata only; executed by CE).",
            input_schema=planner_input_schema,
            output_schema=planner_output_schema,
            extensions=Extensions.model_validate({
                "jarvis.role": "planner",
                "jarvis.planner_variant": "general",
            }),
        ),
    ]
