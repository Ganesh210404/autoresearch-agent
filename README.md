🚀 AutoResearch Agent
######################################################################################################################################################################################
LangChain (LCEL) + Tavily + Groq
Plan → Search → Evaluate → Refine → Synthesize

“This agent does not just search — it thinks in loops until evidence becomes clarity.”
######################################################################################################################################################################################
📌 Overview

AutoResearch Agent is an autonomous AI research system that:

Breaks complex questions into sub-tasks

Uses web search tools intelligently

Self-evaluates information quality

Refines search strategy when gaps exist

Synthesizes structured, cited answers

Generates a real-time Thinking Log

This is not a chatbot wrapper.
This is a reasoning loop agent with tool-triggered self-correction.

🏗 System Architecture (Track 1 – Agent Flow Diagram)``````````````````````````````

https://drive.google.com/drive/folders/1d1HxsEC9aQJW0KagROsyYxSWXCL_W-d_?usp=sharing

🧠 Reasoning Pattern Used
Pattern: Plan → Execute → Evaluate → Refine → Synthesize

Why not simple ReAct?

ReAct mixes reasoning and acting in one loop.
Plan-and-Execute provides:

Clear separation of strategy vs execution

Better traceability

Structured evaluation stage

Controlled stopping criteria

Deterministic iteration limits

This makes it safer, more debuggable, and hackathon-demo friendly.

🔁 Self-Correction Logic

After each search:

The evaluator must respond:

DECISION: YES or NO
GAPS: explanation

If:

No relevant sources → Force NO

Invalid format → Force NO

Missing gaps → Refine search

Then:

Improved query includes credible domains

Includes year if required

Targets missing entities

This prevents hallucination and premature stopping.

🛠 Tools Used
1️⃣ Tavily Web Search

Purpose:

Real-time research

Credible source retrieval

Multi-result search

Trigger:

After query generation

After refinement
######################################################################################################################################################################################
📚 Prompt Library
🧩 1. Planning Prompt

Purpose:

Break question into sub-tasks

Define stop criteria

Returns:

PLAN:
1) ...
2) ...
3) ...
STOP_CRITERIA: ...

Why:
Structured planning ensures the agent doesn’t blindly search.

🔍 2. Query Generation Prompt

Returns:

Single short Google-style query

Max 12 words

No explanation

Why:
Short queries improve search precision and reduce noise.

🔄 3. Query Refinement Prompt

Includes:

Previous query

Evaluator feedback

Instructions to target gaps

Enforces:

Specific entities

Credible domains

Year inclusion if needed

Why:
Prevents infinite loops and improves iteration quality.

🧪 4. Evaluation Prompt

Returns STRICT format:

DECISION: YES or NO
GAPS: ...

Why:
Strict format enables programmatic loop control.

🧾 5. Synthesis Prompt

Generates:

Answer

Key Points

Contradictions / Uncertainty

Citations

Confidence (0-100)
######################################################################################################################################################################################
Why:
Prevents hallucination and enforces evidence grounding.

🎛 Model Configuration

LLM: Groq (Llama 3.1)
Temperature: 0.3

Why 0.3?

Lower hallucination risk

More deterministic reasoning

Better evaluator stability

Max Tokens: Configurable via environment

🔁 Infinite Loop Prevention

MAX_ITERATIONS limit

If evaluator returns invalid format → forced NO

If no sources → forced NO

Hard stop after iteration threshold

📊 Thinking Log

Every step is recorded:

question

plan_created

search_query

tool_search_call

tool_search_result

evaluation

stop

final_answer

Exported as:

thinking_log.json

This enables traceability and live demo inspection.
######################################################################################################################################################################################
🚀 How To Run

1️⃣ Clone repository

git clone https://github.com/Ganesh210404/autoresearch-agent.git
cd autoresearch-agent

2️⃣ Install dependencies

pip install -r requirements.txt

3️⃣ Add .env file

GROQ_API_KEY=your_key_here
TAVILY_API_KEY=your_key_here

4️⃣ Run Streamlit

streamlit run app.py

######################################################################################################################################################################################


What are the "Hallucination Risks" of your agent? How do you prevent the agent from getting stuck in an infinite loop during research?
🧠 Hallucination Risks & Infinite Loop Prevention
1️⃣ Hallucination Risks of the AutoResearch Agent

Even though the system is tool-augmented, hallucination risks still exist:

🔹 A. Source Misinterpretation

The LLM may:

Overgeneralize from limited snippets

Misinterpret partial search results

Infer conclusions not explicitly supported

🔹 B. Weak or Low-Quality Sources

If search returns:

Blogs

Forums

SEO articles

Outdated content

The synthesis step may build on unreliable data.

🔹 C. Fabricated Connections

The model might:

Combine unrelated facts

Assume causality from correlation

Extrapolate beyond evidence

🔹 D. Premature Stopping

If evaluator incorrectly returns:

DECISION: YES

the agent may stop before collecting sufficient evidence.

🛡 How Hallucination Is Mitigated
✅ 1. Source-Grounded Synthesis

The synthesis prompt enforces:

“Use ONLY the provided sources.”

Explicit citations section

Contradictions section

Confidence score requirement

This reduces free-form hallucination.

✅ 2. Evaluator Gate (Self-Correction Layer)

After every search iteration:

The evaluator must return:

DECISION: YES or NO
GAPS: ...

If:

No sources found → forced NO

Missing entities → refinement required

Weak coverage → refinement triggered

This prevents premature conclusions.

✅ 3. Controlled Temperature (0.3)

Low temperature:

Reduces creative generation

Increases determinism

Improves consistency in evaluation format

✅ 4. Explicit Contradiction Section

The final answer requires:

“Contradictions / Uncertainty” section

This forces the model to:

Admit ambiguity

Compare differing viewpoints

Avoid overconfidence

✅ 5. Confidence Scoring

The model must provide:

0–100 confidence score

One-line justification

This discourages overly assertive hallucinated claims.

🔁 Infinite Loop Prevention

Autonomous research loops can risk endless refinement.

The agent prevents infinite loops using:

✅ 1. MAX_ITERATIONS Limit

Hard stop:

MAX_ITERATIONS = 3 (configurable)

Even if evaluator keeps returning NO,
the loop stops safely.

✅ 2. Deterministic Stop Condition

Loop exits when:

DECISION: YES

Strict format enforcement ensures reliable parsing.

✅ 3. Forced Exit on Invalid Evaluator Output

If evaluator returns invalid format:

Automatically treated as NO

Iteration counter increases

Eventually capped by MAX_ITERATIONS

✅ 4. No-Source Safeguard

If Tavily returns zero results:

Force DECISION: NO

Add explicit gap message

Prevent useless synthesis


######################################################################################################################################################################################

🏁 Conclusion

AutoResearch Agent demonstrates:

Autonomous multi-step reasoning

Evidence-based synthesis

Safe loop-controlled search refinement

Real-time transparency through Thinking Log

This is a controllable research system — not a chatbot.


######################################################################################################################################################################################
