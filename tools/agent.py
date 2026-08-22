from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from core.docling_ingest import DoclingIngestor
from core.ocr_ingest import OCRIngestor
from core.research import ResearchEngine
from core.evidence_store import EvidenceStore
from core.task_manager import TaskManager
from core.permissions import PermissionPolicy, ApprovalRequired
from sage_mcp.client import call_tool

from core.capability_registry import create_capability_router
from inference.router import InferenceRouter
from tools.registry import ToolRegistry
from tools.web_tools import download_pdf


@dataclass
class AgentExecutor:
    inference: InferenceRouter
    tools: ToolRegistry
    task_manager: TaskManager
    research: ResearchEngine

    def __post_init__(self) -> None:
        self.capabilities = create_capability_router()
        evidence = EvidenceStore()
        self.docling_ingestor = DoclingIngestor(evidence)
        self.ocr_ingestor = OCRIngestor(evidence)
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
            r"(?i)\b(ocr|optical\s+character|scanned|scan)\b",
            text,
        ):
            source = document_match.group(1).rstrip(".,)")

            return {
                "use_tool": True,
                "capability": "document",
                "tool": "ocr_ingest",
                "arguments": {
                    "source": source,
                },
            }
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
        paper_patterns = [
            r"\b(search|find|look\s+for)\s+(academic\s+)?papers?\b",
            r"\b(search|find)\s+(the\s+)?scholarly\s+literature\b",
            r"\b(search|find)\s+(academic\s+)?research\b",
            r"\b(scholarly|academic)\s+(papers?|literature|research)\b",
        ]

        if any(
            re.search(pattern, text, re.IGNORECASE)
            for pattern in paper_patterns
        ):
            query = re.sub(
                r"(?i)^(please\s+)?"
                r"(search|find|look\s+for)\s+"
                r"(?:(?:the\s+)?academic\s+)?"
                r"(?:papers?|research|scholarly\s+literature)"
                r"\s*(?:about|on|for|regarding)?\s*",
                "",
                text,
            ).strip()

            return {
                "use_tool": True,
                "capability": "research",
                "tool": "paper_search",
                "arguments": {
                    "query": query or text,
                    "max_results": 5,
                },
            }
        # Deterministic paper-find provider routing
        provider_patterns = {
            "google_scholar": r"(?i)\bgoogle\s+scholar\b",
            "pubmed": r"(?i)\bpubmed\b",
            "arxiv": r"(?i)\barxiv\b",
            "semantic": r"(?i)\bsemantic\s+scholar\b",
            "crossref": r"(?i)\bcrossref\b",
            "biorxiv": r"(?i)\bbioRxiv\b",
            "medrxiv": r"(?i)\bmedRxiv\b",
        }

        for provider, pattern in provider_patterns.items():
            if re.search(pattern, text):
                query = re.sub(
                    pattern,
                    "",
                    text,
                ).strip()

                query = re.sub(
                    r"(?i)^(please\s+)?"
                    r"(search|find|look\s+for)\s*"
                    r"(academic\s+)?(papers?|literature|research)?"
                    r"\s*(about|on|for|regarding)?\s*",
                    "",
                    query,
                ).strip()

                return {
                    "use_tool": True,
                    "capability": "research",
                    "tool": "paperfind_search",
                    "arguments": {
                        "provider": provider,
                        "query": query or text,
                        "max_results": 5,
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
                r"(?i)^(please\s+)?(search the web|search online|search for|look up)\s*(?:for\s+)?",
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

        tools.append(
            {
                "name": "ocr_ingest",
                "description": (
                    "Render a local PDF and extract text with Tesseract OCR "
                    "when the document is scanned or image-based."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "source": {
                            "type": "string",
                            "description": "Local PDF file path to OCR.",
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

        tools.append(
            {
                "name": "paperfind_search",
                "description": (
                    "Search scholarly sources through paper-find-mcp and "
                    "return paper metadata, IDs, DOI, and available PDF URLs.",
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "provider": {
                            "type": "string",
                            "description": "paper-find-mcp search provider.",
                        },
                        "query": {
                            "type": "string",
                            "description": "Scholarly search query.",
                        },
                        "max_results": {
                            "type": "integer",
                            "description": "Maximum number of papers.",
                        },
                    },
                    "required": ["provider", "query"],
                },
            }
        )

        tools.append(
            {
                "name": "paper_download",
                "description": "Download an actual paper PDF through paper-find-mcp.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "provider": {
                            "type": "string",
                            "description": "paper-find-mcp download provider.",
                        },
                        "paper_id": {
                            "type": "string",
                            "description": "Provider-specific paper ID or DOI.",
                        },
                        "url": {
                            "type": "string",
                            "description": (
                                "Publisher or direct PDF URL. Required when "
                                "the provider is google_scholar.",
                            ),
                        },
                        "save_path": {
                            "type": "string",
                            "description": "Directory for the downloaded PDF.",
                        },
                    },
                    "required": ["provider", "paper_id"],
                },
            }
        )

        tools.append(
            {
                "name": "paper_read",
                "description": "Read an actual paper through paper-find-mcp as Markdown.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "provider": {
                            "type": "string",
                            "description": "paper-find-mcp read provider.",
                        },
                        "paper_id": {
                            "type": "string",
                            "description": "Provider-specific paper ID or DOI.",
                        },
                        "save_path": {
                            "type": "string",
                            "description": "Optional directory for paper files.",
                        },
                    },
                    "required": ["provider", "paper_id"],
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

        # Document ingestion
        elif capability_name == "document":
            if tool_name == "ocr_ingest":
                return self.ocr_ingestor.ingest(
                    conversation_id=conversation_id,
                    source=arguments["source"],
                    title=arguments.get("title", ""),
                )

            return self.docling_ingestor.ingest(
                conversation_id=conversation_id,
                source=arguments["source"],
                title=arguments.get("title", ""),
            )
        # OpenAlex scholarly research
        elif capability_name == "research" and tool_name == "paper_search":
            return self.research.search_papers(
                conversation_id=conversation_id,
                query=arguments["query"],
                max_results=arguments.get("max_results", 5),
            )
        # paper-find MCP tools
        elif capability_name == "research" and tool_name in (
            "paperfind_search",
            "paper_download",
            "paper_read",
        ):
            provider = arguments.get("provider", "")
            paper_id = arguments.get("paper_id", "")
            save_path = arguments.get(
                "save_path",
                r"D:\Sage\workspace\papers",
            )

            search_tools = {
                "google_scholar": "search_google_scholar",
                "semantic": "search_semantic",
                "pubmed": "search_pubmed",
                "arxiv": "search_arxiv",
                "crossref": "search_crossref",
                "biorxiv": "search_biorxiv",
                "medrxiv": "search_medrxiv",
                "iacr": "search_iacr",
                "repec": "search_repec",
            }

            download_tools = {
                "semantic": "download_semantic",
                "pubmed": "download_pubmed",
                "arxiv": "download_arxiv",
                "biorxiv": "download_biorxiv",
                "medrxiv": "download_medrxiv",
                "iacr": "download_iacr",
                "repec": "download_repec",
                "scihub": "download_scihub",
            }

            read_tools = {
                "semantic": "read_semantic_paper",
                "pubmed": "read_pubmed_paper",
                "arxiv": "read_arxiv_paper",
                "biorxiv": "read_biorxiv_paper",
                "medrxiv": "read_medrxiv_paper",
                "iacr": "read_iacr_paper",
                "repec": "read_repec_paper",
                "scihub": "read_scihub_paper",
            }

            if tool_name == "paperfind_search":
                mcp_tool = search_tools.get(provider)
                if not mcp_tool:
                    raise ValueError(
                        f"Unsupported paper search provider: {provider}"
                    )

                mcp_arguments = {
                    "query": arguments["query"],
                    "max_results": arguments.get("max_results", 5),
                }

            elif tool_name == "paper_download":
                mcp_tool = download_tools.get(provider)

                # Google Scholar is discovery-only in paper-find-mcp.
                # Fall back to the discovered publisher URL.
                if provider == "google_scholar":
                    source_url = arguments.get("url", "").strip()

                    if not source_url:
                        raise ValueError(
                            "Google Scholar download requires the paper URL."
                        )

                    safe_id = re.sub(
                        r"[^A-Za-z0-9._-]+",
                        "_",
                        paper_id,
                    ).strip("_")

                    destination = str(
                        Path(save_path) / f"{safe_id or 'paper'}.pdf"
                    )

                    return download_pdf(
                        source_url,
                        destination,
                    )

                if not mcp_tool:
                    raise ValueError(
                        f"Unsupported paper download provider: {provider}"
                    )

                mcp_arguments = {
                    "paper_id": paper_id,
                    "save_path": save_path,
                }

            else:
                mcp_tool = read_tools.get(provider)
                if not mcp_tool:
                    raise ValueError(
                        f"Unsupported paper read provider: {provider}"
                    )

                mcp_arguments = {
                    "paper_id": paper_id,
                    "save_path": save_path,
                }

            result = call_tool(
                mcp_tool,
                mcp_arguments,
                server="paperfind",
            )

            if hasattr(result, "structured_content"):
                structured = result.structured_content

                if (
                    isinstance(structured, dict)
                    and "result" in structured
                ):
                    result = structured["result"]
                elif structured is not None:
                    result = structured
                elif hasattr(result, "content") and result.content:
                    result = result.content[0].text

            return result
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
