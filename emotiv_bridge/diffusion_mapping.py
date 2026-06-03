from __future__ import annotations

from typing import Any

from emotiv_bridge.metrics_parser import CognitiveState


def map_engagement_to_cfg_scale(state: CognitiveState) -> dict[str, Any]:
    return {
        "parameter": "cfg_scale",
        "source_metric": "engagement",
        "value": state.engagement,
        "status": "placeholder",
    }


def map_stress_to_noise_strength(state: CognitiveState) -> dict[str, Any]:
    return {
        "parameter": "noise_strength",
        "source_metric": "stress",
        "value": state.stress,
        "status": "placeholder",
    }


def map_interest_to_prompt_weighting(state: CognitiveState) -> dict[str, Any]:
    return {
        "parameter": "prompt_weighting",
        "source_metric": "interest",
        "value": state.interest,
        "status": "placeholder",
    }


def map_relaxation_to_image_stabilization(state: CognitiveState) -> dict[str, Any]:
    return {
        "parameter": "image_stabilization",
        "source_metric": "relaxation",
        "value": state.relaxation,
        "status": "placeholder",
    }

