from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class RiskLevel(str, Enum):
    SAFE = "safe"
    APPROVAL = "approval"
    DANGEROUS = "dangerous"


class ApprovalRequired(Exception):
    def __init__(
        self,
        tool: str,
        arguments: dict,
        reason: str,
    ) -> None:
        self.tool = tool
        self.arguments = arguments
        self.reason = reason

        super().__init__(
            f"Approval required for '{tool}': {reason}"
        )


@dataclass(frozen=True)
class PermissionDecision:
    allowed: bool
    requires_approval: bool
    risk: RiskLevel
    reason: str


class PermissionPolicy:
    """
    Central policy for deciding whether Sage may execute a tool.
    """

    def __init__(self) -> None:
        self._policies: dict[str, RiskLevel] = {
            # Read-only / informational
            "calculator": RiskLevel.SAFE,
            "web_search": RiskLevel.SAFE,
            "web_fetch": RiskLevel.SAFE,
            "browser_open": RiskLevel.SAFE,
            "list_files": RiskLevel.SAFE,
            "read_file": RiskLevel.SAFE,
            "search_files": RiskLevel.SAFE,

            # Changes local state
            "write_file": RiskLevel.APPROVAL,

            # Document ingestion does not modify the source
            "docling_ingest": RiskLevel.SAFE,

            # Memory changes persistent user state
            "remember": RiskLevel.APPROVAL,

            # Future high-impact operations
            "git_commit": RiskLevel.APPROVAL,
            "git_push": RiskLevel.DANGEROUS,
            "delete_file": RiskLevel.DANGEROUS,
        }

    def risk_for(self, tool: str) -> RiskLevel:
        return self._policies.get(
            tool,
            RiskLevel.APPROVAL,
        )

    def check(
        self,
        tool: str,
        arguments: dict,
    ) -> PermissionDecision:
        risk = self.risk_for(tool)

        if risk == RiskLevel.SAFE:
            return PermissionDecision(
                allowed=True,
                requires_approval=False,
                risk=risk,
                reason="Tool is classified as safe.",
            )

        if risk == RiskLevel.APPROVAL:
            return PermissionDecision(
                allowed=False,
                requires_approval=True,
                risk=risk,
                reason="Tool can modify state and requires user approval.",
            )

        return PermissionDecision(
            allowed=False,
            requires_approval=True,
            risk=risk,
            reason="Tool is classified as dangerous and requires explicit approval.",
        )

    def require_approval(
        self,
        tool: str,
        arguments: dict,
    ) -> None:
        decision = self.check(tool, arguments)

        if decision.requires_approval:
            raise ApprovalRequired(
                tool=tool,
                arguments=arguments,
                reason=decision.reason,
            )
