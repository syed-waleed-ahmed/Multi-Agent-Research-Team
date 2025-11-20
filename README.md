# 🤖 Multi-Agent Research Team (CrewAI + Groq + Serper)

A fully autonomous **multi-agent research system** built using **CrewAI**, **Groq LLMs**, and **Serper Web Search**, where three specialized AI agents collaborate to research topics, summarize findings, and generate actionable code examples.

This project showcases real-world agent orchestration, intelligent task delegation, and automated research workflows — perfect for portfolios and AI engineering showcases.

---

## 🚀 Features

### 🔹 Three Specialized Agents
- **Research Agent** – Performs web research using Serper search.  
- **Coding Agent** – Generates runnable Python code and technical examples.  
- **Manager Agent** – Coordinates agents and synthesizes final deliverables.

### 🔹 Automated Research Workflow
The agents follow a hierarchical structure:
1. Research Agent collects information  
2. Coding Agent generates code based on findings  
3. Manager Agent produces a polished, final report  

### 🔹 Groq LLM Integration
Ultra-fast inference with LLaMA-based Groq models for:
- Research  
- Coding  
- Final synthesis

### 🔹 High-Quality Final Deliverable  
The Manager Agent outputs a **structured, actionable Markdown report** including:
- Key findings  
- Technical insights  
- Code blocks  
- Suggested next steps  

---

## 📂 Project Structure
```text
multi-agent-research-team/
├── .env
├── requirements.txt
└── src/
├── config.py # LLM + Serper config
├── agents.py # Three agents
├── tasks.py # Defined tasks
├── crew.py # CrewAI orchestration
└── main.py # Entry point
```

## ▶️ Usage

- Run the system with a research topic:
```text
python -m src.main --topic "Applications of multi-agent systems in AI automation workflows"
```
- Example Output:
```text
──────────────── Multi-Agent Research Team ────────────────

Final Output:

# Multi-Agent Applications in Automation
## Key Findings
...
## Example Python Implementation
...

```

## 🔧 Technologies Used

1. 🧩 CrewAI
Used for:
- Multi-agent orchestration
- Hierarchical agent manager
- Task execution pipelines

2. ⚡ Groq LLMs
Provides:
- Ultra-fast inference
- Llama 3-based reasoning
- High-quality research + code generation

3. 🌐 SerperDev Tool
Used by Research Agent to:
- Perform real-time Google-style queries
- Summarize web results
- Extract key insights

## 🛠 Future Improvements

- Add memory to agents (shared knowledge store)
- Add a QA Reviewer agent
- Export results as PDF or HTML
- Add support for multiple data analysis agents
- Add a Streamlit UI for interactive control

## Author

Created by Syed Waleed Ahmed