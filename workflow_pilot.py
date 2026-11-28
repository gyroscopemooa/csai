"""Offline workflow planning and read-only execution pilot."""
from dataclasses import dataclass
from hashlib import sha256
import json


@dataclass(frozen=True)
class Step:
    id: str
    tool: str
    role: str
    depends_on: tuple = ()


@dataclass(frozen=True)
class ToolSpec:
    role: str
    read_only: bool


def validate_plan(steps, registry):
    if not 1 <= len(steps) <= 20:
        raise ValueError('invalid step count')
    seen = set()
    for step in steps:
        if not isinstance(step, Step) or not all(isinstance(v, str) and 0 < len(v) <= 100 for v in (step.id, step.tool, step.role)):
            raise ValueError('invalid step')
        spec = registry.get(step.tool)
        if not isinstance(spec, ToolSpec) or spec.role != step.role or type(spec.read_only) is not bool:
            raise ValueError('tool or role not authorized')
        if step.id in seen or not isinstance(step.depends_on, tuple) or not all(isinstance(v, str) for v in step.depends_on):
            raise ValueError('invalid dependency')
        if not set(step.depends_on) <= seen:
            raise ValueError('dependencies must precede step')
        seen.add(step.id)
    return sha256(json.dumps([[s.id, s.tool, s.role, list(s.depends_on), registry[s.tool].read_only] for s in steps], ensure_ascii=False).encode()).hexdigest()


def run_read_only(steps, registry, *, workspace, enabled=False, max_steps=0, execute=None, verify=None):
    """Callbacks are trusted server adapters, never model-provided code.

    No mutations or automatic retries. Real authorization, budget reservation
    and provider isolation are prerequisites for supplying actual adapters.
    """
    if enabled is not True:
        return None
    if not isinstance(workspace, str) or not workspace.strip() or type(max_steps) is not int or not 1 <= max_steps <= 20:
        raise ValueError('scope or budget invalid')
    digest = validate_plan(steps, registry)
    if len(steps) > max_steps or any(registry[s.tool].read_only is not True for s in steps):
        raise ValueError('write tools prohibited or budget exceeded')
    if not callable(execute) or not callable(verify):
        raise ValueError('trusted adapters required')
    outcomes = []
    for step in steps:
        try:
            output = execute(workspace, step)
            if verify(workspace, step, output) is not True:
                outcomes.append((step.id, 'unverified'))
                break
        except Exception:
            outcomes.append((step.id, 'error'))
            break
        outcomes.append((step.id, 'verified'))
    return {'workspace': workspace, 'plan': digest, 'outcomes': outcomes,
            'complete': len(outcomes) == len(steps) and all(s == 'verified' for _, s in outcomes)}


def approval_preview(steps, registry, *, workspace):
    """Describe write steps for review; does not grant or store authorization."""
    if not isinstance(workspace, str) or not workspace.strip():
        raise ValueError('scope required')
    return {'workspace': workspace, 'plan': validate_plan(steps, registry),
            'review_required': [s.id for s in steps if not registry[s.tool].read_only]}
