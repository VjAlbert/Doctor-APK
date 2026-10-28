"""Orchestration: creating a project from an analysis, and drafting a change from an idea."""

from __future__ import annotations

from datetime import datetime, timezone

from ..ai import claude_cli
from ..i18n import t
from . import WorkspaceError, draft, spec
from .store import Workspace


def create_project(report: dict, code_map: dict | None, name: str, lang: str, *,
                   owner_confirmed: bool, use_ai: bool) -> tuple[Workspace, str]:
    """Creates a project holding a specification of the analysed app. Returns (project, spec source)."""
    if owner_confirmed is not True:
        raise WorkspaceError("ownership")
    verdict = report.get("verdict")
    if not isinstance(verdict, dict) or not isinstance(report.get("app"), dict):
        raise WorkspaceError("bad_request")
    if verdict.get("id") == "do_not_install":
        raise WorkspaceError("malicious")  # study it, never recreate it

    name = (name or report["app"].get("name") or report["app"].get("package") or "project").strip()[:80]
    source = "template"
    text = None
    if use_ai:
        try:
            system, prompt = spec.build_prompt(report, code_map, lang)
            text = claude_cli.ask(system, prompt, timeout=claude_cli.LONG_ASK_TIMEOUT)["text"]
            source = "ai"
        except claude_cli.AiError:
            text = None  # fall back to the template rather than failing the whole project
    if not text:
        text = spec.fallback_spec(name, report, code_map, lang)

    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    project = Workspace.create(
        name=name, package=str(report["app"].get("package", "")),
        files={"SPEC.md": text.strip() + "\n", "README.md": t("workspace.readme", lang)},
        source={"sha256": report.get("file", {}).get("sha256", ""), "verdict": verdict.get("id"),
                "category": (report.get("category") or {}).get("id"), "spec": source},
        ownership={"confirmed": True, "statement": t("workspace.ownership", lang), "at": now},
    )
    return project, source


def draft_idea(project: Workspace, idea_id: str, lang: str) -> dict:
    """Asks Claude to turn an idea into a proposal. Returns {"proposal", "summary", "declined"}."""
    idea = project.get_idea(idea_id)
    if idea["status"] != "new":
        raise WorkspaceError("not_open")
    system, prompt = draft.build(project.read_all(), idea["text"], lang)
    reply = claude_cli.ask(system, prompt, timeout=claude_cli.LONG_ASK_TIMEOUT)["text"]
    summary, files = draft.parse_reply(reply)
    if not files:
        return {"proposal": None, "summary": summary, "declined": True}
    proposal = project.create_proposal(idea_id, summary, files)
    idea["status"], idea["proposal_id"] = "drafted", proposal["id"]
    project.update_idea(idea)
    return {"proposal": project.proposal_view(proposal["id"]), "summary": summary, "declined": False}
