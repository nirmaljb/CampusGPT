# Agentic RAG – LLM Context

## Purpose
Give LLMs the full operating context for the Pondicherry University agentic RAG chatbot so they respond consistently, with citations, tabular detail, and the right control flow.

## Data & Collections
- Current collection: `PONDICHERRY_UNIVERSITY_INFO` (NIRF-only) in Qdrant at `http://localhost:6333`. Embeddings: `models/gemini-embedding-001`.
- Indexing scripts (`preprocessing/indexing.py`, `preprocessing/parse.py`) parse `data/pondiuni_clean_final.md`; writes are commented and target `PONDICHERRY_UNIVERSITY_INFO_NORMAL` / `_FACULTY`. Align future collection names before reindexing.
- Faculty rows are normalized into structured `Document` metadata; other sections are prefixed with section headers.

## Models & Tools (from backend/agent_graph.py)
- Router: Groq `openai/gpt-oss-120b` → routes to `basic`, `vectorstore`, or `web_search`.
- Basic responder: Groq `openai/gpt-oss-120b` (warming/greeting + optional knowledge).
- Retriever: Qdrant collection `PONDICHERRY_UNIVERSITY_INFO` via Gemini embeddings.
- RAG generation: Groq `llama-3.3-70b-versatile`, temperature 0.
- Document relevance grader: Groq `llama-3.3-70b-versatile` (lenient yes/no + explanation) → sets `web_search` flag if any doc irrelevant.
- Hallucination grader: Groq `openai/gpt-oss-120b` yes/no on grounding vs documents.
- Usefulness grader: Groq `openai/gpt-oss-120b` yes/no on answering the question.
- Web search: Tavily (k=3), results concatenated into a single `Document`.

## Graph State
`{ question: str, generation: str, web_search: str, documents: List[Document] }`

## Control Flow
1) Entry routing (`route_question`):
   - `basic` → `basic_response` (finish)
   - `vectorstore` → `retrieve`
   - `web_search` → `websearch`
2) `retrieve` → fetch docs.
3) `grade_documents` → filter docs; if any irrelevant, set `web_search = "Yes"`.
4) `decide_to_generate`: if `web_search == "Yes"` → `websearch`, else → `generate`.
5) `websearch` → append Tavily results → `generate`.
6) `generate` (RAG) → `grade_generation_v_documents_and_question`:
  - `useful` → END
  - `not useful` → `websearch`
  - `not supported` (hallucination) → `handle_hallucination`
7) `handle_hallucination`:
  - retries < 3 → back to `generate`
  - first time hitting cap → set `limit_exhausted`, force `websearch`
  - already exhausted → END with warning note
8) Finish point also set to `basic_response` for basic path.

### Hallucination Retry Plan
- Implemented: retries capped at 3. On first cap hit → force a `websearch` fallback once; if still ungrounded after that, return the last generation with a verification-limit warning and stop.

## Answer Formatting (frontend expectation)
- Always include citations and sources. Prefer table-first, detailed answers (avoid terse bullets). Suggested structure:
  1) Short lead-in sentence.
  2) Table with key fields (e.g., metric, year, value, source).
  3) If table not suitable, use numbered sections with inline citations.
  4) Sources: list URLs or doc identifiers after the answer.
- Inline citations: use bracketed tags like [source 1], [source 2] mapped to Sources list.
- If web + vector docs combined, mark which source is vector vs web.

## API Contract
- Non-streaming: `POST /chat` body `{ "messages": "<text>", "thread_id"?: "..." }` → JSON `{ "output": <graph_result> }` (invoke).
- Streaming (SSE): `POST /chat/stream` body `{ "messages": "<text>", "thread_id"?: "..." }` → `text/event-stream` with events:
  - `token`: `{ text }` (current generation chunk)
  - `done`: `{ text, sources, thread_id }`
  - `error`: `{ error }`
- Sources are derived from retrieved documents’ metadata (section/faculty_name fallback labels). Frontend should map to inline citations.

## Web Search Policy
- Provider: Tavily only (k=3). Triggered when router says `web_search` or when doc grading finds gaps, or when generation is `not useful`.

## Collections Roadmap
- Today: single NIRF collection (`PONDICHERRY_UNIVERSITY_INFO`).
- Future: define clear names (e.g., `PU_NIRF`, `PU_POLICIES`, `PU_RESEARCH`, `PU_FACULTY`). Update retriever routing/metadata before adding.

## Environment / Config
- Required keys in `.env`: `GOOGLE_API_KEY` (Gemini embeddings), `GROQ_API_KEY` (Groq models), `TAVILY_API_KEY` (search). Qdrant at `http://localhost:6333` (see docker-compose).

## Known Gaps / TODOs
- Align collection naming between live NIRF data and indexing scripts; uncomment and run indexing when ready.
- Add richer citations extraction inside generation (map doc metadata to inline refs consistently).
- Frontend: consume SSE (`token/done/error`), render tables + inline citations.
- Consider per-branch temperature/format tuning for more tabular outputs.
