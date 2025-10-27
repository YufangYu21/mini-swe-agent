import dataclasses
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

from minisweagent import Agent, __version__


def _get_class_name_with_module(obj: Any) -> str:
    """Get the full class name with module path."""
    return f"{obj.__class__.__module__}.{obj.__class__.__name__}"


def _asdict(obj: Any) -> dict:
    """Convert config objects to dicts."""
    if dataclasses.is_dataclass(obj):
        return dataclasses.asdict(obj)  # type: ignore[arg-type]
    return obj  # let's try our luck


def _extract_logprobs_from_messages(messages: list[dict]) -> list[dict]:
    """Extract logprobs data from agent messages."""
    logprobs_data = []

    for i, message in enumerate(messages):
        if message.get("role") == "assistant" and "extra" in message:
            extra = message["extra"]
            if "response" in extra and "choices" in extra["response"]:
                choice = extra["response"]["choices"][0]
                if "logprobs" in choice:
                    logprobs_data.append({"message_index": i, "logprobs": choice["logprobs"]})

    return logprobs_data


def save_traj(
    agent: Agent | None,
    path: Path,
    *,
    print_path: bool = True,
    exit_status: str | None = None,
    result: str | None = None,
    extra_info: dict | None = None,
    print_fct: Callable = print,
    save_logprobs: bool = True,
    **kwargs,
):
    """Save the trajectory of the agent to a file.

    Args:
        agent: The agent to save the trajectory of.
        path: The path to save the trajectory to.
        print_path: Whether to print confirmation of path to the terminal.
        exit_status: The exit status of the agent.
        result: The result/submission of the agent.
        extra_info: Extra information to save (will be merged into the info dict).
        print_fct: Function to use for printing messages.
        save_logprobs: Whether to save logprobs data to a separate file.
        **kwargs: Additional information to save (will be merged into top level)

    """
    data = {
        "info": {
            "exit_status": exit_status,
            "submission": result,
            "model_stats": {
                "instance_cost": 0.0,
                "api_calls": 0,
            },
            "mini_version": __version__,
        },
        "messages": [],
        "trajectory_format": "mini-swe-agent-1",
    } | kwargs
    if agent is not None:
        data["info"]["model_stats"]["instance_cost"] = agent.model.cost
        data["info"]["model_stats"]["api_calls"] = agent.model.n_calls
        data["messages"] = agent.messages
        data["info"]["config"] = {
            "agent": _asdict(agent.config),
            "model": _asdict(agent.model.config),
            "environment": _asdict(agent.env.config),
            "agent_type": _get_class_name_with_module(agent),
            "model_type": _get_class_name_with_module(agent.model),
            "environment_type": _get_class_name_with_module(agent.env),
        }
    if extra_info:
        data["info"].update(extra_info)

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2))
    if print_path:
        print_fct(f"Saved trajectory to '{path}'")

    # Save logprobs data to a separate file if requested and available
    if save_logprobs and agent is not None:
        logprobs_data = _extract_logprobs_from_messages(agent.messages)
        if len(logprobs_data) > 0:
            logprobs_path = path.with_suffix(".logprobs.json")
            logprobs_file_data = {
                "info": {
                    "traj_file": str(path),
                    "mini_version": __version__,
                    "logprobs_count": len(logprobs_data),
                },
                "logprobs": logprobs_data,
            }
            logprobs_path.write_text(json.dumps(logprobs_file_data, indent=2))
            if print_path:
                print_fct(f"Saved logprobs data to '{logprobs_path}'")
        elif print_path:
            print_fct("No logprobs data found in agent messages")
