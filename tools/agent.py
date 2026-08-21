from __future__ import annotations

import json
import re
from dataclasses import dataclass
from core.docling_ingest import DoclingIngestor
from core.evidence_store import EvidenceStore
from core.task_manager import TaskManager
from core.permissions import PermissionPolicy, ApprovalRequired
from sage_mcp.client import call_tool

from core.capability_registry import create_capability_router
from inference.router import InferenceRouter
from tools.registry import ToolRegistry


@dataclass
class AgentExecutor:
    inference: InferenceRouter
    tools: ToolRegistry
    task_manager: TaskManager

    def __post_init__(self) -> None:
        self.capabilities = create_capability_router()
        self.docling_ingestor = DoclingIngestor(EvidenceStore())
        self.permission_policy = PermissionPolicy()

    def _deterministic(self, message: str) -> dict | None:
        text = message.strip()

        match = re.search(
            r"(?i)\bwhat\s+is\s+([0-9\s\+\-\*\/\%\(\)\.]+)\??\s*$",
            text,
        )

        if match:
            expression = match.group(1).strip()

            if re.search(r"[\+\-\*\/\%]", expression):
                return {
                    "use_tool": True,
                    "capability": "calculation",
                    "tool": "calculator",
                    "arguments": {
                        "expression": expression,
                    },
                }

        # ------------------------------------------------------------
        # Deterministic document ingestion
        # ------------------------------------------------------------

        document_match = re.search(
            r"(?i)([A-Za-z]:\\[^\r\n\"']+\.(?:pdf|docx|pptx|xlsx|html|htm|md|txt))",
            text,
        )

        if document_match and re.search(
            r"(?i)\b(ingest|read|process|parse|extract|convert)\b",
            text,
        ):
            source = document_match.group(1).rstrip(".,)")

            return {
                "use_tool": True,
                "capability": "document",
                "tool": "docling_ingest",
                "arguments": {
                    "source": source,
                },
            }
        # ------------------------------------------------------------
        # Deterministic SQLite operations
        # ------------------------------------------------------------

        sqlite_db_match = re.search(
            r"(?i)([A-Za-z]:\\[^\s]+\.db)",
            text,
        )

        if sqlite_db_match:
            database = sqlite_db_match.group(1).rstrip(".,)")

            execute_prefix = re.search(
                r"(?is)\bexecute\s+(?:this\s+)?sql\b",
                text,
            )

            if execute_prefix:
                sql_start = text.find(":", sqlite_db_match.end())

                if sql_start != -1:
                    sql = text[sql_start + 1:].strip()

                    if sql:
                        return {
                            "use_tool": True,
                            "capability": "sqlite",
                            "tool": "sqlite_execute",
                            "arguments": {
                                "database": database,
                                "sql": sql,
                            },
                        }
            if re.search(
                r"(?i)\b(show|list)\b.*\b(tables|table names)\b",
                text,
            ):
                return {
                    "use_tool": True,
                    "capability": "sqlite",
                    "tool": "sqlite_list_tables",
                    "arguments": {
                        "database": database,
                    },
                }

            schema_match = re.search(
                r"(?i)\bschema\b.*?\btable\s+([A-Za-z_][A-Za-z0-9_]*)",
                text,
            )

            if schema_match:
                return {
                    "use_tool": True,
                    "capability": "sqlite",
                    "tool": "sqlite_schema",
                    "arguments": {
                        "database": database,
                        "table": schema_match.group(1),
                    },
                }
        # ------------------------------------------------------------
        # Deterministic Git operations
        # ------------------------------------------------------------

        git_text = text.lower()

        if re.search(
            r"\b(git\s+status|show\s+(me\s+)?the\s+git\s+status|check\s+(the\s+)?git\s+status)\b",
            git_text,
        ):
            return {
                "use_tool": True,
                "capability": "git",
                "tool": "git_status",
                "arguments": {},
            }

        if re.search(
            r"\b(git\s+log|show\s+(me\s+)?(the\s+)?recent\s+git\s+commits|show\s+(me\s+)?git\s+commits)\b",
            git_text,
        ):
            return {
                "use_tool": True,
                "capability": "git",
                "tool": "git_log",
                "arguments": {
                    "limit": 10,
                },
            }

        if re.search(
            r"\b(git\s+diff|show\s+(me\s+)?the\s+git\s+diff|show\s+(me\s+)?git\s+changes)\b",
            git_text,
        ):
            return {
                "use_tool": True,
                "capability": "git",
                "tool": "git_diff",
                "arguments": {},
            }

        commit_match = re.search(
            r"(?i)\bcommit\b.*?\bmessage\b\s*:?\s*[\"']?(.+?)[\"']?\s*$",
            text,
        )

        if commit_match:
            message = commit_match.group(1).strip().strip("\"'")

            if message:
                return {
                    "use_tool": True,
                    "capability": "git",
                    "tool": "git_commit",
                    "arguments": {
                        "message": message,
                    },
                }

        if re.search(
            r"(?i)\b(git\s+push|push\s+(the\s+)?git\s+changes|push\s+(the\s+)?changes\s+to\s+(the\s+)?remote)\b",
            text,
        ):
            return {
                "use_tool": True,
                "capability": "git",
                "tool": "git_push",
                "arguments": {},
            }

        if re.search(
            r"(?i)\b(git\s+add|stage\s+(the\s+)?git\s+changes|stage\s+(the\s+)?changes)\b",
            text,
        ):
            return {
                "use_tool": True,
                "capability": "git",
                "tool": "git_add",
                "arguments": {
                    "path": ".",
                },
            }
        web_patterns = [
            r"\bsearch the web\b",
            r"\bsearch online\b",
            r"\bsearch for\b",
            r"\blook up\b",
            r"\bfind the latest\b",
            r"\blatest news\b",
            r"\bcurrent news\b",
            r"\brecent news\b",
        ]

        if any(
            re.search(pattern, text, re.IGNORECASE)
            for pattern in web_patterns
        ):
            query = re.sub(
                r"(?i)^(please\s+)?(search the web|search online|search for|look up)\s*",
                "",
                text,
            ).strip()

            return {
                "use_tool": True,
                "capability": "research",
                "tool": "web_search",
                "arguments": {
                    "query": query or text,
                    "max_results": 5,
                },
            }

        if re.search(
            r"(?i)\b(remember|save|don't forget|keep in mind)\b",
            text,
        ):
            memory = re.sub(
                r"(?i)^(please\s+)?(remember|save|don't forget|keep in mind)\s*(that|this)?\s*:?\s*",
                "",
                text,
            ).strip()

            if memory:
                return {
                    "use_tool": True,
                    "capability": "memory",
                    "tool": "remember",
                    "arguments": {
                        "memory": memory,
                    },
                }

        return None

    def _planner_tools(self) -> list[dict]:
        tools = self.tools.list()

        tools.append(
            {
                "name": "docling_ingest",
                "description": (
                    "Convert a local document or PDF URL using Docling "
                    "and store the extracted content in Sage EvidenceStore."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "source": {
                            "type": "string",
                            "description": (
                                "Local file path or HTTP/HTTPS URL "
                                "of the document to ingest."
                            ),
                        },
                        "title": {
                            "type": "string",
                            "description": "Optional document title.",
                        },
                    },
                    "required": ["source"],
                },
            }
        )

        return tools

    def decide(self, message: str) -> dict:
        deterministic = self._deterministic(message)

        if deterministic is not None:
            return deterministic

        prompt = f"""
You are Sage's capability and tool planner.

CAPABILITIES:
{json.dumps(self.capabilities.list(), indent=2)}

TOOLS:
{json.dumps(self._planner_tools(), indent=2)}

USER REQUEST:
{message}

First choose the most appropriate capability.
Then choose a tool only if a tool is actually required.

Return ONLY valid JSON.

No tool:
{{
  "use_tool": false,
  "capability": "conversation"
}}

Tool:
{{
  "use_tool": true,
  "capability": "capability_name",
  "tool": "tool_name",
  "arguments": {{}}
}}

Rules:
- capability must be one of the listed capabilities.
- tool must belong to the selected capability.
- arguments must exactly match the tool schema.
- never invent argument names.
"""

        raw = self.inference.chat(
            prompt,
            provider="groq",
            model="openai/gpt-oss-20b",
        )

        try:
            decision = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                f"Tool decision was not valid JSON: {raw}"
            ) from exc

        if not isinstance(decision, dict):
            raise ValueError("Planner response must be an object.")

        capability = decision.get("capability")

        if capability:
            self.capabilities.get(capability)

        if decision.get("use_tool"):
            tool_name = decision.get("tool")
            arguments = decision.get("arguments", {})

            if not isinstance(tool_name, str):
                raise ValueError("Invalid tool name.")

            capability_obj = self.capabilities.find_for_tool(tool_name)

            if capability_obj is None:
                raise ValueError(
                    f"Tool '{tool_name}' is not assigned to a capability."
                )

            if capability_obj.name != capability:
                raise ValueError(
                    f"Tool '{tool_name}' does not belong to "
                    f"capability '{capability}'."
                )

            if not isinstance(arguments, dict):
                raise ValueError("Tool arguments must be an object.")

            if capability_obj.name not in ("filesystem", "document", "git", "sqlite"):
                self.tools.get(tool_name)

        return decision

    def approve(
        self,
        approval: dict,
        conversation_id: str = "default",
    ) -> dict:
        """Execute an already-approved action without re-planning."""
        if not approval.get("approval_required"):
            raise ValueError("No approval is required for this action.")

        tool_name = approval.get("tool")
        arguments = approval.get("arguments", {})
        capability = approval.get("capability")

        if not isinstance(tool_name, str):
            raise ValueError("Approval does not contain a valid tool.")

        if not isinstance(arguments, dict):
            raise ValueError("Approval arguments must be an object.")

        capability_obj = self.capabilities.find_for_tool(tool_name)

        if capability_obj is None:
            raise ValueError(
                f"Tool '{tool_name}' is not assigned to a capability."
            )

        if capability_obj.name != capability:
            raise ValueError(
                f"Tool '{tool_name}' does not belong to capability "
                f"'{capability}'."
            )

        permission = self.permission_policy.check(
            tool_name,
            arguments,
        )

        if not permission.requires_approval:
            raise ValueError(
                f"Tool '{tool_name}' no longer requires approval."
            )

        result = self._execute_tool(
            capability_obj.name,
            tool_name,
            arguments,
            conversation_id,
        )

        self.task_manager.record_tool_result(
            conversation_id,
            tool_name,
            arguments,
            result,
        )

        return {
            "used_tool": True,
            "approved": True,
            "capability": capability,
            "tool": tool_name,
            "arguments": arguments,
            "result": result,
        }
    def run(
        self,
        message: str,
        conversation_id: str = "default",
    ) -> dict:
        decision = self.decide(message)

        if not decision.get("use_tool"):
            return {
                "used_tool": False,
                "result": None,
                "decision": decision,
            }

        tool_name = decision["tool"]
        arguments = decision.get("arguments", {})
        capability = decision["capability"]

        capability_obj = self.capabilities.find_for_tool(tool_name)

        if capability_obj is None:
            raise ValueError(
                f"Tool '{tool_name}' is not assigned to a capability."
            )
        # Permission check MUST happen before tool execution.
        permission = self.permission_policy.check(
            tool_name,
            arguments,
        )

        if permission.requires_approval:
            return {
                "used_tool": False,
                "approval_required": True,
                "capability": capability,
                "tool": tool_name,
                "arguments": arguments,
                "risk": permission.risk.value,
                "reason": permission.reason,
                "decision": decision,
            }

        result = self._execute_tool(
            capability_obj.name,
            tool_name,
            arguments,
            conversation_id,
        )

        self.task_manager.record_tool_result(
            conversation_id,
            tool_name,
            arguments,
            result,
        )

        return {
            "used_tool": True,
            "capability": capability,
            "tool": tool_name,
            "arguments": arguments,
            "result": result,
            "decision": decision,
        }

    def _execute_tool(
        self,
        capability_name: str,
        tool_name: str,
        arguments: dict,
        conversation_id: str = "default",
    ):
        """Execute a validated tool action."""

        # MCP filesystem tools
        if capability_name == "filesystem":
            result = call_tool(
                tool_name,
                arguments,
            )

            if hasattr(result, "structured_content"):
                structured = result.structured_content

                if isinstance(structured, dict) and "result" in structured:
                    result = structured["result"]
                elif structured is not None:
                    result = structured
                elif hasattr(result, "content") and result.content:
                    result = result.content[0].text

            return result

        # Docling document ingestion
        elif capability_name == "document":
            return self.docling_ingestor.ingest(
                conversation_id=conversation_id,
                source=arguments["source"],
            )

        # Git MCP tools
        elif capability_name == "git":
            result = call_tool(
                tool_name,
                arguments,
                server="git",
            )

            if hasattr(result, "structured_content"):
                structured = result.structured_content

                if isinstance(structured, dict) and "result" in structured:
                    result = structured["result"]
                elif structured is not None:
                    result = structured
                elif hasattr(result, "content") and result.content:
                    result = result.content[0].text

            return result

        # SQLite MCP tools
        elif capability_name == "sqlite":
            if tool_name == "sqlite_query" and "query" in arguments:
                arguments = {
                    **arguments,
                    "sql": arguments["query"],
                }
                arguments.pop("query", None)

            result = call_tool(
                tool_name,
                arguments,
                server="sqlite",
            )

            if hasattr(result, "structured_content"):
                structured = result.structured_content

                if isinstance(structured, dict) and "result" in structured:
                    result = structured["result"]
                elif structured is not None:
                    result = structured
                elif hasattr(result, "content") and result.content:
                    result = result.content[0].text

            return result
        # Playwright browser tools
        elif capability_name == "browser":
            return self.tools.execute(
                tool_name,
                **arguments,
            )

        # Native Sage tools
        else:
            return self.tools.execute(
                tool_name,
                **arguments,
            )
