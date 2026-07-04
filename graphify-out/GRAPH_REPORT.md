# Graph Report - D:\Projects & Stuff\multi-agent-research-team  (2026-07-05)

## Corpus Check
- 7 files · ~5,143 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 27 nodes · 47 edges · 5 communities detected
- Extraction: 72% EXTRACTED · 28% INFERRED · 0% AMBIGUOUS · INFERRED: 13 edges (avg confidence: 0.8)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Community 0|Community 0]]
- [[_COMMUNITY_Community 1|Community 1]]
- [[_COMMUNITY_Community 2|Community 2]]
- [[_COMMUNITY_Community 3|Community 3]]
- [[_COMMUNITY_Community 4|Community 4]]

## God Nodes (most connected - your core abstractions)
1. `build_crew()` - 10 edges
2. `get_llm()` - 6 edges
3. `load_config()` - 5 edges
4. `research_agent()` - 4 edges
5. `get_config()` - 4 edges
6. `get_web_search_tool()` - 4 edges
7. `manager_agent()` - 3 edges
8. `coding_agent()` - 3 edges
9. `run_research_workflow()` - 3 edges
10. `main()` - 3 edges

## Surprising Connections (you probably didn't know these)
- `research_agent()` --calls--> `get_web_search_tool()`  [INFERRED]
  D:\Projects & Stuff\multi-agent-research-team\src\agents.py → D:\Projects & Stuff\multi-agent-research-team\src\config.py
- `get_web_search_tool()` --calls--> `build_crew()`  [INFERRED]
  D:\Projects & Stuff\multi-agent-research-team\src\config.py → D:\Projects & Stuff\multi-agent-research-team\src\crew.py
- `build_crew()` --calls--> `research_task()`  [INFERRED]
  D:\Projects & Stuff\multi-agent-research-team\src\crew.py → D:\Projects & Stuff\multi-agent-research-team\src\tasks.py
- `build_crew()` --calls--> `coding_task()`  [INFERRED]
  D:\Projects & Stuff\multi-agent-research-team\src\crew.py → D:\Projects & Stuff\multi-agent-research-team\src\tasks.py
- `build_crew()` --calls--> `manager_task()`  [INFERRED]
  D:\Projects & Stuff\multi-agent-research-team\src\crew.py → D:\Projects & Stuff\multi-agent-research-team\src\tasks.py

## Communities

### Community 0 - "Community 0"
Cohesion: 0.5
Nodes (6): coding_agent(), manager_agent(), research_agent(), get_llm(), build_crew(), run_research_workflow()

### Community 1 - "Community 1"
Cohesion: 0.52
Nodes (6): AppConfig, get_config(), get_web_search_tool(), load_config(), _parse_float(), _parse_int()

### Community 2 - "Community 2"
Cohesion: 0.29
Nodes (6): coding_task(), manager_task(), Task B: Coding/analysis based on the research., Task C: Manager synthesizes everything into a final deliverable., Task A: Web research., research_task()

### Community 3 - "Community 3"
Cohesion: 1.33
Nodes (2): build_parser(), main()

### Community 4 - "Community 4"
Cohesion: 1.0
Nodes (1): Multi-Agent Research Team package.

## Knowledge Gaps
- **4 isolated node(s):** `Task A: Web research.`, `Task B: Coding/analysis based on the research.`, `Task C: Manager synthesizes everything into a final deliverable.`, `Multi-Agent Research Team package.`
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Community 4`** (2 nodes): `__init__.py`, `Multi-Agent Research Team package.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `build_crew()` connect `Community 0` to `Community 1`, `Community 2`?**
  _High betweenness centrality (0.398) - this node is a cross-community bridge._
- **Why does `run_research_workflow()` connect `Community 0` to `Community 3`?**
  _High betweenness centrality (0.194) - this node is a cross-community bridge._
- **Why does `main()` connect `Community 3` to `Community 0`?**
  _High betweenness centrality (0.135) - this node is a cross-community bridge._
- **Are the 8 inferred relationships involving `build_crew()` (e.g. with `get_llm()` and `get_web_search_tool()`) actually correct?**
  _`build_crew()` has 8 INFERRED edges - model-reasoned connections that need verification._
- **Are the 4 inferred relationships involving `get_llm()` (e.g. with `manager_agent()` and `research_agent()`) actually correct?**
  _`get_llm()` has 4 INFERRED edges - model-reasoned connections that need verification._
- **Are the 3 inferred relationships involving `research_agent()` (e.g. with `get_llm()` and `get_web_search_tool()`) actually correct?**
  _`research_agent()` has 3 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Task A: Web research.`, `Task B: Coding/analysis based on the research.`, `Task C: Manager synthesizes everything into a final deliverable.` to the rest of the system?**
  _4 weakly-connected nodes found - possible documentation gaps or missing edges._