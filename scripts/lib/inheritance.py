"""Compose the effective skills + instructions for one workspace.

Operates on a generic ORDERED LIST OF LAYERS, not hardcoded enterprise/workspace.
The workspace itself is always the final layer. Today the list is `[enterprise]`;
adding a `profiles/hipaa` layer later is a config change, not a code change.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .config import WorkspaceConfig, layer_path


@dataclass
class EffectiveState:
    instructions_files: list[Path] = field(default_factory=list)
    # skill name -> source folder (the directory containing SKILL.md)
    skills: dict[str, Path] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)


def _find_skill_dirs(skills_root: Path) -> dict[str, Path]:
    """Walk skills_root recursively, return {skill_name: folder}.

    A skill is any folder containing a SKILL.md. Skill `name` comes from the folder
    name; nested folders (e.g. `data_eng/pii-handling/`) are flattened to their
    leaf name (`pii-handling`). Domain subfolders are purely organizational.
    """
    if not skills_root.exists():
        return {}
    found: dict[str, Path] = {}
    for skill_md in skills_root.rglob("SKILL.md"):
        skill_dir = skill_md.parent
        # Skip folders whose name starts with `_` (templates, drafts) and anything
        # nested under such a folder. Same convention used for workspaces/_example/.
        rel_parts = skill_dir.relative_to(skills_root).parts
        if any(part.startswith("_") for part in rel_parts):
            continue
        found[skill_dir.name] = skill_dir
    return found


def _filter_by_allowlist(
    skills: dict[str, Path], allowlist: list[str] | str
) -> dict[str, Path]:
    if allowlist == "all":
        return dict(skills)
    return {name: path for name, path in skills.items() if name in set(allowlist)}


def compose(workspace: WorkspaceConfig) -> EffectiveState:
    """Build the effective state for one workspace."""
    state = EffectiveState()

    # Layers in order, then workspace as the implicit final layer.
    for layer in workspace.layers:
        lpath = layer_path(layer)
        if not lpath.exists():
            state.warnings.append(
                f"layer '{layer}' referenced in {workspace.name}/config.yaml "
                f"but {lpath} does not exist"
            )
            continue

        # Instructions
        if workspace.instructions_enabled:
            inst_dir = lpath / "instructions"
            if inst_dir.exists():
                state.instructions_files.extend(
                    sorted(inst_dir.glob("*.md"))
                )

        # Skills (filtered by per-layer allow-list)
        layer_skills = _find_skill_dirs(lpath / "skills")
        allowlist = workspace.skill_allowlist(layer)
        if isinstance(allowlist, list):
            missing = set(allowlist) - layer_skills.keys()
            for name in sorted(missing):
                state.warnings.append(
                    f"workspace {workspace.name}: layer '{layer}' allow-list "
                    f"requests skill '{name}' but it does not exist"
                )
        for name, path in _filter_by_allowlist(layer_skills, allowlist).items():
            state.skills[name] = path  # later layer wins; workspace overlays last

    # Workspace itself is the final layer.
    wpath = workspace.path

    # Workspace always contributes its own instructions (instructions_enabled only
    # gates INHERITED instructions, never the workspace's own).
    workspace_inst = wpath / "instructions"
    if workspace_inst.exists():
        state.instructions_files.extend(sorted(workspace_inst.glob("*.md")))

    # Workspace skills overlay; on collision the workspace wins and we warn.
    workspace_skills = _find_skill_dirs(wpath / "skills")
    for name, path in workspace_skills.items():
        if name in state.skills:
            state.warnings.append(
                f"workspace {workspace.name}: skill '{name}' overrides an inherited "
                f"skill of the same name (workspace version wins)"
            )
        state.skills[name] = path

    return state
