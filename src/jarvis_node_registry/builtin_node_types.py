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
        "additionalProperties": True,
        "properties": {
            "goal": {"type": "string", "description": "High-level goal to plan/execute."},
            "prompt": {"type": "string", "description": "Alias for goal (legacy/compat)."},
            "context": {
                "type": "object",
                "additionalProperties": True,
                "description": "Optional context/facts for planning. Must not include secrets.",
            },
            "max_steps": {"type": "integer", "minimum": 1, "description": "Hard cap on planned steps."},
            "max_depth": {"type": "integer", "minimum": 1, "description": "Hard cap on planning recursion depth."},
        },
        "anyOf": [{"required": ["goal"]}, {"required": ["prompt"]}],
    }

    planner_output_schema: dict[str, Any] = {
        "type": "object",
        "additionalProperties": True,
        "description": "Planner outputs are implementation-defined in v0.x.",
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
