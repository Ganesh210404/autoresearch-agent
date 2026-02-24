import os
import json
from datetime import datetime, timezone
from typing import Any, Dict, List

from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableLambda, RunnablePassthrough

from langchain_tavily import TavilySearch

# ---------------------------
# Setup
# ---------------------------
load_dotenv()
console = Console()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

if not GROQ_API_KEY or not TAVILY_API_KEY:
    console.print("[red]Missing API keys in .env file[/red]")
    raise SystemExit(1)

# Use a model that works for you (you said it’s working now)
MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.3"))
MAX_OUTPUT_TOKENS = int(os.getenv("MAX_OUTPUT_TOKENS", "1400"))

MAX_ITERATIONS = int(os.getenv("MAX_ITERATIONS", "3"))
MAX_RESULTS = int(os.getenv("MAX_RESULTS", "3"))

llm = ChatGroq(
    model=MODEL,
    temperature=TEMPERATURE,
    max_tokens=MAX_OUTPUT_TOKENS,
    api_key=GROQ_API_KEY,
)

thinking_log: List[Dict[str, Any]] = []


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def log(step: str, data: Any = None):
    thinking_log.append({"time": utc_now_iso(), "step": step, "data": data})


def print_sources_table(sources: List[Dict[str, Any]], title: str):
    table = Table(title=title, show_lines=True)
    table.add_column("#", justify="right", style="cyan")
    table.add_column("Title", style="white")
    table.add_column("URL", style="green")
    for i, s in enumerate(sources, start=1):
        table.add_row(str(i), (s.get("title") or "")[:70], (s.get("url") or "")[:90])
    console.print(table)


# ---------------------------
# LCEL Chains
# ---------------------------

plan_prompt = ChatPromptTemplate.from_template(
    """You are an autonomous research agent.
Create a short plan for answering the question.

Question: {question}

Return EXACTLY:
PLAN:
1) ...
2) ...
3) ...
STOP_CRITERIA: one sentence
"""
)

plan_chain = plan_prompt | llm | StrOutputParser()

query_prompt = ChatPromptTemplate.from_template(
    """Research question: {question}

Return ONLY ONE short Google-style search query (max 12 words).
No explanations. No quotes. No bullet points.
Only the query text.
"""
)
query_chain = query_prompt | llm | StrOutputParser()

improve_query_prompt = ChatPromptTemplate.from_template(
    """Research question: {question}
Previous query: {prev_query}

Evaluator feedback:
{evaluation}

Return ONE improved search query targeting the missing gaps.
Rules:
- include year 2025 if the question is about 2025
- include 1-2 specific entities if missing (company/lab/paper)
- prefer credible sources (site:arxiv.org OR site:nature.com OR site:ieee.org OR site:mit.edu OR site:ibm.com)
- max 12 words, no quotes, no bullet points
Only the query text.
"""
)
improve_query_chain = improve_query_prompt | llm | StrOutputParser()

eval_prompt = ChatPromptTemplate.from_template(
    """We are researching: {question}

Here are the most recent sources:
{recent_sources}

Respond in EXACTLY this format:

DECISION: YES or NO
GAPS: If DECISION is YES, write "None".
If DECISION is NO, write one short sentence explaining what is missing.
"""
)
eval_chain = eval_prompt | llm | StrOutputParser()

synth_prompt = ChatPromptTemplate.from_template(
    """You are a research assistant. Use ONLY the sources below.

Question: {question}

Sources (title, url, snippet):
{all_sources}

Write the final response with:
1) Answer (clear)
2) Key points (bullets)
3) Contradictions / uncertainty (if any)
4) Citations (list URLs used)
5) Confidence (0-100) + one sentence why

Rules:
- Do NOT invent facts not supported by the sources.
- If sources are insufficient, say what is missing.
- Length target: {length_target}
"""
)
synth_chain = synth_prompt | llm | StrOutputParser()


# ---------------------------
# Tool wrapper
# ---------------------------
def run_search(query: str) -> List[Dict[str, Any]]:
    q = (query or "").strip()[:300]
    log("tool_search_call", {"query": q})

    results = search_tool.invoke(q)

    cleaned = []

    # TavilySearch may return list[dict] or dict with "results"
    if isinstance(results, list):
        for r in results:
            if isinstance(r, dict):
                cleaned.append({
                    "title": r.get("title", ""),
                    "url": r.get("url", ""),
                    "content": r.get("content", r.get("snippet", "")),
                })
            else:
                cleaned.append({"title": "", "url": "", "content": str(r)})

    elif isinstance(results, dict):
        for r in results.get("results", []):
            cleaned.append({
                "title": r.get("title", ""),
                "url": r.get("url", ""),
                "content": r.get("content", r.get("snippet", "")),
            })

    else:
        cleaned.append({"title": "", "url": "", "content": str(results)})

    log("tool_search_result", {"count": len(cleaned)})
    return cleaned


def get_length_target(mode: str) -> str:
    m = (mode or "Balanced").strip().lower()
    if m == "fast":
        return "Keep concise (~120-180 words total)."
    if m == "deep":
        return "Provide a detailed answer (~450-700 words total)."
    return "Provide moderate detail (~220-350 words total)."


# ---------------------------
# Orchestrator (LangChain-style, but controlled loop)
# ---------------------------
def run_agent(
    question: str,
    max_iterations: int | None = None,
    max_results: int | None = None,
    mode: str = "Balanced",
):
    console.print(Panel(f"[bold cyan]Research Question:[/bold cyan] {question}"))
    log("question", question)
    length_target = get_length_target(mode)

    iterations = max(1, int(max_iterations if max_iterations is not None else MAX_ITERATIONS))
    results = max(1, int(max_results if max_results is not None else MAX_RESULTS))

    global search_tool
    search_tool = TavilySearch(max_results=results)

    # 1) PLAN (LCEL)
    console.print("[bold cyan]→ Creating plan...[/bold cyan]")
    plan = plan_chain.invoke({"question": question})
    log("plan_created", plan)
    console.print(Panel(plan, title="PLAN", border_style="cyan"))

    all_sources: List[Dict[str, Any]] = []
    evaluation = ""
    prev_query = ""
    final_answer = ""

    # 2) ITERATE
    for i in range(iterations):
        console.print(f"\n[yellow]Iteration {i+1}[/yellow]")

        # Query (LCEL)
        if i == 0:
            console.print("[bold blue]→ Generating initial search query...[/bold blue]")
            q = query_chain.invoke({"question": question})
        else:
            console.print("[bold blue]→ Improving search query (self-correction)...[/bold blue]")
            q = improve_query_chain.invoke(
                {"question": question, "prev_query": prev_query, "evaluation": evaluation}
            )

        q = (q or "").strip()[:300]
        prev_query = q
        log("search_query", {"iteration": i + 1, "query": q})
        console.print(f"[blue]Search Query:[/blue] {q}")

        # Search tool
        console.print("[bold blue]→ Searching web (Tavily)...[/bold blue]")
        new_sources = run_search(q)
        all_sources.extend(new_sources)

        if new_sources:
            print_sources_table(new_sources, title="Collected Sources (this iteration)")
        else:
            console.print("[red]No sources found for this query.[/red]")

        # Evaluate (LCEL)
        console.print("[bold magenta]→ Evaluating if we have enough info...[/bold magenta]")

        # If nothing came back, force NO with an explicit gap
        if not new_sources:
            evaluation = "DECISION: NO\nGAPS: No relevant sources returned. Try a different query."
        else:
            recent_str = json.dumps(new_sources[:3], ensure_ascii=False, indent=2)
            evaluation = eval_chain.invoke(
                {"question": question, "recent_sources": recent_str}
            ).strip()

        # Normalize evaluation format (prevent YES + weird gaps)
        if "DECISION:" not in evaluation.upper():
            evaluation = f"DECISION: NO\nGAPS: Evaluator returned an invalid format: {evaluation[:120]}"

        if "DECISION: YES" in evaluation.upper():
            # Force GAPS: None when YES (for clean logic)
            evaluation = "DECISION: YES\nGAPS: None"

        log("evaluation", {"iteration": i + 1, "evaluation": evaluation})
        console.print(f"[magenta]Evaluation:[/magenta]\n{evaluation}")

        if "DECISION: YES" in evaluation.upper():
            log("stop", {"reason": "sufficient_information", "iteration": i + 1})
            break
    else:
        log("stop", {"reason": "max_iterations_reached", "iteration": iterations})

    # 3) SYNTHESIZE (LCEL)
    console.print("\n[bold green]→ Synthesizing final answer...[/bold green]")
    all_sources_str = json.dumps(all_sources, ensure_ascii=False, indent=2)
    final_answer = synth_chain.invoke(
        {
            "question": question,
            "all_sources": all_sources_str,
            "length_target": length_target,
        }
    )
    log("final_answer", final_answer)

    console.print(Panel(final_answer, title="FINAL ANSWER", border_style="green"))

    # 4) Export thinking log
    with open("thinking_log.json", "w", encoding="utf-8") as f:
        json.dump(thinking_log, f, ensure_ascii=False, indent=2)

    console.print("[bold green]Saved thinking log to thinking_log.json[/bold green]")

    # ✅ IMPORTANT for Streamlit
    return final_answer, thinking_log


if __name__ == "__main__":
    q = input("Enter your research question: ").strip()
    if not q:
        console.print("[red]Please enter a question.[/red]")
        raise SystemExit(1)

    # For CLI run, we don't need the returned values
    run_agent(q)
