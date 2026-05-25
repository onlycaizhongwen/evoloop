from __future__ import annotations

from orchestrator.domain.models.rule_proposal import RuleProposal


class RuleProposalWriter:
    def render(self, proposal: RuleProposal) -> str:
        lines = [
            f"# Pending Rule Proposal {proposal.proposal_id}",
            "",
            f"- task_id: `{proposal.task_id}`",
            f"- run_id: `{proposal.run_id}`",
            f"- source: `{proposal.source}`",
            f"- review_status: `{proposal.review_status}`",
            f"- created_at: `{proposal.created_at.isoformat()}`",
            "",
            "## Reason",
            "",
            proposal.reason,
            "",
            "## Suggested Rule",
            "",
            proposal.suggested_rule,
            "",
            "## Scope",
            "",
            proposal.scope,
            "",
            "## Evidence",
            "",
        ]
        if proposal.cluster_key:
            lines[5:5] = [
                f"- cluster_key: `{proposal.cluster_key}`",
                f"- observed_count: `{proposal.observed_count}`",
                f"- first_seen_run_id: `{proposal.first_seen_run_id or proposal.run_id}`",
                f"- last_seen_run_id: `{proposal.last_seen_run_id or proposal.run_id}`",
            ]
        if proposal.evidence:
            lines.extend(f"- {item}" for item in proposal.evidence)
        else:
            lines.append("- No additional evidence captured.")
        lines.extend(
            [
                "",
                "## Review Note",
                "",
                "This is a pending candidate only. Do not apply it to formal Skills until a human reviewer approves it.",
            ]
        )
        return "\n".join(lines) + "\n"
