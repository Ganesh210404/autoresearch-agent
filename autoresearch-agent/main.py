import os
import json
from datetime import datetime
from dotenv import load_dotenv
from groq import Groq
from tavily import TavilyClient
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# ---------------------------
# Setup
# ---------------------------
load_dotenv()
console = Console()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

if not GROQ_API_KEY or not TAVILY_API_KEY:
    console.print("[red]Missing API keys in .env file[/red]")
    console.print("Make sure .env contains:")
    console.print("GROQ_API_KEY=...\nTAVILY_API_KEY=...")
    raise SystemExit(1)

llm = Groq(api_key=GROQ_API_KEY)
search = TavilyClient(api_key=TAVILY_API_KEY)

# Use a current Groq model name
MODEL = "llama-3.1-8b-instant"   # fallback: "llama-3.1-8b-instant"
TEMPERATURE = 0.3

MAX_ITERATIONS = 3
MAX_RESULTS_PER_SEARCH = 3

# Thinking log (for demo + possible export)
thinking_log = []


def log(step: str, data=None):
    """Store and print thinking log events."""
    entry = {
        "time": datetime.utcnow().isoformat() + "Z",
        "step": step,
        "data": data
    }
    thinking_log.append(entry)


def ask_llm(prompt: str) -> str:
    """Call Groq chat completion and return text."""
    resp = llm.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=TEMPERATURE,
    )
    return (resp.choices[0].message.content or "").strip()


def make_plan(question: str) -> str:
    """Generate a simple research plan (for demo)."""
    prompt = f"""
You are an autonomous research agent.
Create a short research plan for answering the question below.

Question: {question}

Return in this exact format:
PLAN:
1) ...
2) ...
3) ...
STOP_CRITERIA: one sentence
"""
    plan = ask_llm(prompt)
    return plan


def choose_initial_query(question: str) -> str:
    """Generate ONE short initial search query."""
    prompt = f"""
Research question: {question}

Return ONLY ONE short Google-style search query (max 12 words).
No explanations. No quotes. No bullet points.
Only the query text.
"""
    q = ask_llm(prompt)
    return q[:300].strip()


def improve_query(question: str, previous_query: str, evaluation: str) -> str:
    """Generate ONE improved search query based on gaps."""
    prompt = f"""
Research question: {question}

Previous query: {previous_query}

Evaluator feedback:
{evaluation}

Return ONE improved search query that targets the missing gaps.
Constraints:
- max 12 words
- no quotes
- no bullet points
- only the query text
"""
    q = ask_llm(prompt)
    return q[:300].strip()


def evaluate_enough(question: str, recent_sources: list) -> str:
    """Ask LLM if we have enough info; must output DECISION & GAPS."""
    prompt = f"""
We are researching: {question}

Here are the most recent sources (snippets):
{json.dumps(recent_sources, ensure_ascii=False, indent=2)}

Answer in EXACTLY this format (2 lines):
DECISION: YES or NO
GAPS: one short sentence on what's missing
"""
    return ask_llm(prompt)


def synthesize_answer(question: str, sources: list) -> str:
    """Produce final answer with citations + confidence."""
    prompt = f"""
You are a research assistant. Use ONLY the sources below.

Question: {question}

Sources (title, url, snippet):
{json.dumps(sources, ensure_ascii=False, indent=2)}

Write the final response with:
1) Answer (clear and structured)
2) Key points (bullets)
3) Contradictions / uncertainty (if any)
4) Citations (list URLs used)
5) Confidence (0-100) + one sentence why

Rules:
- Do NOT invent facts not supported by the sources.
- If sources are insufficient, say what is missing.
"""
    return ask_llm(prompt)


def print_sources_table(sources: list):
    table = Table(title="Collected Sources", show_lines=True)
    table.add_column("#", justify="right", style="cyan")
    table.add_column("Title", style="white")
    table.add_column("URL", style="green")

    for i, s in enumerate(sources, start=1):
        table.add_row(str(i), (s.get("title") or "")[:60], (s.get("url") or "")[:80])

    console.print(table)


def research(question: str):
    console.print(Panel(f"[bold cyan]Research Question:[/bold cyan] {question}"))

    # 0) Plan
    plan = make_plan(question)
    log("plan_created", plan)
    console.print(Panel(plan, title="PLAN", border_style="cyan"))

    context_data = []
    evaluation = ""
    search_query = ""

    # 1) Iterative loop
    for iteration in range(MAX_ITERATIONS):
        console.print(f"\n[yellow]Iteration {iteration + 1}[/yellow]")

        if iteration == 0:
            search_query = choose_initial_query(question)
        else:
            search_query = improve_query(question, search_query, evaluation)

        log("search_query", {"iteration": iteration + 1, "query": search_query})
        console.print(f"[blue]Search Query:[/blue] {search_query}")

        results = search.search(search_query, max_results=MAX_RESULTS_PER_SEARCH)

        new_sources = []
        for r in results.get("results", []):
            item = {
                "title": r.get("title"),
                "url": r.get("url"),
                "content": r.get("content"),
            }
            context_data.append(item)
            new_sources.append(item)

        log("search_results", {"iteration": iteration + 1, "count": len(new_sources)})

        # Show sources each iteration (nice for demo)
        if new_sources:
            print_sources_table(new_sources)
        else:
            console.print("[red]No results returned from search.[/red]")

        # Evaluate sufficiency using only recent sources (prevents huge prompts)
        evaluation = evaluate_enough(question, new_sources or context_data[-3:])
        log("evaluation", {"iteration": iteration + 1, "evaluation": evaluation})
        console.print(f"[magenta]Evaluation:[/magenta]\n{evaluation}")

        if "DECISION: YES" in evaluation.upper():
            log("stop", {"reason": "sufficient_information"})
            break
    else:
        log("stop", {"reason": "max_iterations_reached"})

    # 2) Final synthesis
    final_answer = synthesize_answer(question, context_data)
    log("final_answer", final_answer)

    console.print(Panel(final_answer, title="FINAL ANSWER", border_style="green"))

    # 3) Optional: export thinking log (for submission)
    with open("thinking_log.json", "w", encoding="utf-8") as f:
        json.dump(thinking_log, f, ensure_ascii=False, indent=2)

    console.print("[bold green]Saved thinking log to thinking_log.json[/bold green]")


if __name__ == "__main__":
    q = input("Enter your research question: ").strip()
    if not q:
        console.print("[red]Please enter a question.[/red]")
        raise SystemExit(1)
    research(q)