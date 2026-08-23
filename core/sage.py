from __future__ import annotations

from dataclasses import dataclass, field

from core.research import ResearchEngine
from core.task_manager import TaskManager
from core.context_compressor import ContextCompressor
from inference.router import InferenceRouter
from inference.routing import get_route
from memory.bridge import MemoryBridge
from memory.manager import MemoryManager
from tools.agent import AgentExecutor
from tools.basic import calculate
from tools.browser_tool import browser_open
from tools.memory_tool import remember
from tools.registry import Tool, ToolParameter, ToolRegistry
from tools.web import web_search
from tools.web_tools import fetch_web


def _paper_search_registry_handler(
    query: str,
    max_results: int = 5,
):
    raise RuntimeError(
        "paper_search requires AgentExecutor context and must be "
        "executed through Sage's research capability."
    )

@dataclass
class SageCore:
    inference: InferenceRouter
    memory: MemoryBridge
    memory_manager: MemoryManager
    tools: ToolRegistry
    agent: AgentExecutor
    task_manager: TaskManager
    research: ResearchEngine

    context_compressor: ContextCompressor = field(default_factory=ContextCompressor)
    def _latest_user_message(
        self,
        messages: list[dict[str, str]],
    ) -> str:
        for message in reversed(messages):
            if message.get("role") == "user":
                return str(message.get("content", ""))
        return ""

    def _update_task(
        self,
        conversation_id: str,
        message: str,
        capability: str,
    ) -> None:
        task = self.task_manager.current(conversation_id)

        if task is None:
            self.task_manager.start(
                conversation_id=conversation_id,
                intent=message,
                capability=capability,
            )
        else:
            self.task_manager.set_focus(
                conversation_id,
                message,
            )
            task.active_capability = capability
            self.task_manager.store.save(conversation_id, task)

    def respond(
        self,
        messages: list[dict[str, str]],
        workload: str = "chat",
        conversation_id: str = "default",
    ) -> str:
        if not messages:
            raise ValueError("Messages cannot be empty.")

        route = get_route(workload)

        normalized_messages = [
            {
                "role": str(message.get("role", "user")),
                "content": str(message.get("content", "")),
            }
            for message in messages
            if message.get("content") is not None
        ]

        latest_user_message = self._latest_user_message(
            normalized_messages
        )

        tool_result = self.agent.run(
            latest_user_message,
            conversation_id=conversation_id,
        )
        capability = tool_result.get("capability", "conversation")

        self._update_task(
            conversation_id,
            latest_user_message,
            capability,
        )

        if tool_result["used_tool"]:
            self.task_manager.record_tool_result(
                conversation_id=conversation_id,
                tool=tool_result["tool"],
                arguments=tool_result.get("arguments", {}),
                result=tool_result["result"],
            )

        # If a research tool was selected, persist its evidence through
        # the dedicated evidence store as well.
        if tool_result["used_tool"] and tool_result["tool"] == "web_search":
            args = tool_result.get("arguments", {})
            results = tool_result.get("result", [])
            for item in results:
                if isinstance(item, dict):
                    self.research.evidence.add(
                        conversation_id=conversation_id,
                        source_type="web_search",
                        title=str(item.get("title", "")),
                        url=str(item.get("url", "")),
                        content=str(item.get("snippet", "")),
                        metadata={"query": args.get("query", "")},
                    )


        elif tool_result["used_tool"] and tool_result["tool"] == "paperfind_search":
            args = tool_result.get("arguments", {})
            results = tool_result.get("result", [])

            if isinstance(results, list):
                for item in results:
                    if isinstance(item, dict):
                        self.research.evidence.add(
                            conversation_id=conversation_id,
                            source_type="academic_paper",
                            title=str(item.get("title", "")),
                            url=str(
                                item.get("url")
                                or item.get("pdf_url")
                                or ""
                            ),
                            content=str(item.get("abstract", "")),
                            metadata={
                                "provider": args.get("provider", ""),
                                "paper_id": item.get("paper_id", ""),
                                "doi": item.get("doi", ""),
                                "published_date": item.get(
                                    "published_date",
                                    "",
                                ),
                                "source": item.get("source", ""),
                            },
                        )

        elif tool_result["used_tool"] and tool_result["tool"] == "web_fetch":
            result = tool_result.get("result", {})
            if isinstance(result, dict):
                self.research.evidence.add(
                    conversation_id=conversation_id,
                    source_type="web_page",
                    title=str(result.get("title", "")),
                    url=str(result.get("url", "")),
                    content=str(result.get("text", "")),
                    metadata={
                        "status": result.get("status"),
                        "stealth": result.get("stealth", False),
                    },
                )

        current_memory = self.memory.get().strip()

        task = self.task_manager.current(conversation_id)

        task_context = ""
        if task is not None:
            task_context = (
                "\n\nCURRENT TASK:\n"
                f"{task.summary()}\n"
                f"Current focus: {task.current_focus}\n"
            )

        evidence_context = ""
        if capability == "research":
            evidence_context = self.research.evidence_context(
                conversation_id,
                limit=20,
            )

        context_message = {
            "role": "user",
            "content": (
                "[SAGE INTERNAL CONTEXT]\n"
                "You are Sage, a personal AI assistant.\n\n"
                "PERSISTENT MEMORY:\n"
                f"{current_memory}\n"
                f"{task_context}\n"
                "\nRESEARCH EVIDENCE:\n"
                f"{evidence_context}\n"
                "\nUse evidence when relevant. Distinguish sourced "
                "information from model knowledge. Do not mention "
                "internal context unless asked.\n"
                "[END SAGE INTERNAL CONTEXT]"
            ),
        }



        compressed_conversation = self.context_compressor.compress_messages(
            normalized_messages,
        )

        context_message["content"] = self.context_compressor.compress_context_message(
            context_message["content"],
        )

        final_messages = [
            context_message,
            *compressed_conversation,
        ]

        if tool_result["used_tool"]:
            final_messages.append(
                {
                    "role": "user",
                    "content": (
                        "[TOOL RESULT]\n"
                        f"Capability: {tool_result['capability']}\n"
                        f"Tool: {tool_result['tool']}\n"
                        f"Arguments: {tool_result['arguments']}\n"
                        f"Result: {self.context_compressor.compress_tool_result(tool_result['result'])}\n"
                        "[END TOOL RESULT]\n"
                        "Use the tool result and available evidence "
                        "to answer the user's request naturally."
                    ),
                }
            )

        return self.inference.chat_messages(
            final_messages,
            provider=route.provider,
            model=route.model,
        )


def create_sage() -> SageCore:
    inference = InferenceRouter()
    context_compressor = ContextCompressor()
    memory = MemoryBridge()
    memory_manager = MemoryManager(memory)
    evidence = __import__("core.evidence_store", fromlist=["EvidenceStore"]).EvidenceStore()
    task_manager = TaskManager(evidence=evidence)
    research = ResearchEngine(evidence=evidence)

    tools = ToolRegistry()

    tools.register(
        Tool(
            name="calculator",
            description="Perform deterministic arithmetic.",
            handler=calculate,
            parameters=[
                ToolParameter(
                    name="expression",
                    description="Arithmetic expression.",
                    type="string",
                )
            ],
        )
    )

    tools.register(
        Tool(
            name="web_search",
            description="Search the web for current information.",
            handler=web_search,
            parameters=[
                ToolParameter(
                    name="query",
                    description="Search query.",
                    type="string",
                ),
                ToolParameter(
                    name="max_results",
                    description="Maximum number of results.",
                    type="integer",
                    required=False,
                ),
            ],
        )
    )

    tools.register(
        Tool(
            name="web_fetch",
            description="Fetch and read a web page.",
            handler=fetch_web,
            parameters=[
                ToolParameter(
                    name="url",
                    description="Full URL to fetch.",
                    type="string",
                ),
                ToolParameter(
                    name="stealth",
                    description="Use stealth fetching.",
                    type="boolean",
                    required=False,
                ),
            ],
        )
    )

    tools.register(
        Tool(
            name="browser_open",
            description="Open a webpage with Playwright and return its visible content.",
            handler=browser_open,
            parameters=[
                ToolParameter(
                    name="url",
                    description="Full URL to open.",
                    type="string",
                )
            ],
        )
    )

    tools.register(
        Tool(
            name="paper_search",
            description="Search scholarly literature using OpenAlex.",
            handler=_paper_search_registry_handler,
            parameters=[
                ToolParameter(
                    name="query",
                    description="Scholarly search query.",
                    type="string",
                ),
                ToolParameter(
                    name="max_results",
                    description="Maximum number of papers to return.",
                    type="integer",
                    required=False,
                ),
            ],
        )
    )

    tools.register(
        Tool(
            name="remember",
            description="Save a fact or preference to persistent memory.",
            handler=remember,
            parameters=[
                ToolParameter(
                    name="memory",
                    description="The fact or preference to remember.",
                    type="string",
                )
            ],
        )
    )

    agent = AgentExecutor(
        inference=inference,
        tools=tools,
        task_manager=task_manager,
        research=research,
    )

    return SageCore(
        inference=inference,
        context_compressor=context_compressor,
        memory=memory,
        memory_manager=memory_manager,
        tools=tools,
        agent=agent,
        task_manager=task_manager,
        research=research,
    )
