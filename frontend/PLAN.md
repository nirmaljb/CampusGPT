# Frontend Plan — Agentic RAG Chat (LLM Context)

Authoritative context for implementing the ChatGPT-like UI using shadcn/ui + AI Elements with streaming, tool/plan surfacing, citations, uploads, and two-pane layout. Treat this as the contract for LLMs working on the frontend.

## Current Frontend Baseline
- Next.js App Router, RSC enabled; layout uses shadcn sidebar shell ([app/layout.tsx](app/layout.tsx#L1-L36)).
- Home renders only a bare input ([app/page.tsx](app/page.tsx#L1-L5)), and UserInput is a simple shadcn `<Input>` ([components/UserInput.tsx](components/UserInput.tsx#L1-L7)).
- Sidebar scaffold exists with static items ([components/app-sidebar.tsx](components/app-sidebar.tsx#L1-L43)).
- Shadcn style: `new-york`; Tailwind + CSS vars; icon library Lucide. Registries include `@ai-elements`.

## Agreed Requirements
- Two-pane layout: left sidebar for conversation history; right pane for chat transcript + controls.
- Streaming via SSE from POST `/chat/stream` (text/event-stream) with events: `token {text}`, `done {text, sources, thread_id}`, `error {error}`. JSON fallback: POST `/chat` returns `{ output }`.
- No auth (for now). Use React Query for data/mutations.
- Conversation history stored via backend `POST /conversations` (format TBD; include thread_id, messages, sources, timestamps, uploads references).
- File upload support up to 25 MB. Endpoint TBD—front should provide UI + placeholder handler; backend route to be confirmed.
- Display chain-of-thought/plan/tool/queue/checkpoint signals live (surface tool/plan steps like “retrieving”, “web search”, “generating”).
- Answer format: table-first, detailed; always include inline citations `[S1]` mapped to sources list; show source list with labels/URLs/metadata.
- Components to leverage (AI Elements): conversation/message, prompt-input, chain-of-thought, reasoning, plan, task, tool, checkpoint, queue, confirmation, controls, artifact, loader/shimmer, panel/toolbar, inline-citation/sources, message, image (for returned artifacts), web-preview (if links), open-in-chat. Use shadcn primitives for layout/buttons/inputs.
- Theming: keep `new-york` neutral palette; can add CSS vars for accents but avoid purple bias.

## Data & API Contracts (frontend view)
- Send body `{ messages: string, thread_id?: string }` to `/chat/stream` (POST). Parse SSE lines: `event: token|done|error`, `data: <json>`.
- `done` payload includes `sources` (array of docs with `id`, `label`, `metadata`) and `thread_id` (reuse for session continuity).
- Conversation persistence: after `done`, POST to `/conversations` with `{ thread_id, user: message, answer: text, sources, uploads? }` (exact schema to be finalized when backend is ready).
- File uploads: front enforces 25 MB limit; if backend endpoint absent, stub handler and surface “upload pending backend.”

## UX Behaviors
- Input bar: multi-line prompt with send, stop (abort SSE), attach files, model indicator (optional), controls (tone/format toggles later).
- Streaming display: append assistant message and stream `token` updates into it; show typing shimmer while streaming.
- Tool/plan visibility: render a compact timeline of steps (e.g., Router decision, Retrieve, Grade, Web search, Generate, Hallucination retry/fallback) with live status badges; queue/checkpoint can mirror agent states if exposed later.
- Sources: inline `[S1]` tags in the answer; below, a Sources panel listing `S1: <label>` with metadata/links. If web + vector, label origin (web/vector).
- Files/artifacts: show uploaded files as chips; show returned artifacts/images if backend supplies URLs/base64; allow “open-in-chat” or download when applicable.
- History: left sidebar lists past threads (title = first user message), selectable to reload messages from `/conversations` (when backend supports GET). For now, list recent in-memory plus stub for backend fetch.
- Error states: surface `error` event text; keep user input; allow retry.

## Implementation Outline
1) State/Query
   - React Query for `/chat/stream` (manual streaming fetch) and `/conversations` POST; optional GET when backend ready.
   - Local state for `messages`, `activeThreadId`, `uploads`, `streaming` flag, `sources`, `steps` (plan/tool timeline).
2) Streaming hook
   - `useChatStream` to POST, parse SSE, support abort, expose `{ send, cancel, answer, sources, loading, threadId }`.
3) Components
   - Shell: Sidebar (history) + Main panel with toolbar (model/status), chat transcript, sources panel.
   - Message list using AI Elements `message` + `conversation`; assistant message supports streaming text and inline citations.
   - Steps/plan: `plan`, `task`, `tool`, `queue`, `checkpoint` components wired to inferred states (start with simple status list; upgrade when backend emits richer events).
   - Prompt input: `prompt-input` + shadcn input/textarea, send/stop buttons, file attach.
   - Loader/shimmer for streaming and sidebar loading.
   - Sources panel using `inline-citation` + `sources`; optional `web-preview` for links.
4) Uploads
   - Use shadcn `Input type=file` or dropzone; enforce 25 MB per file; hold in state; if backend route absent, show “Upload pending backend” toast.
5) Styling
   - Keep `new-york` theme; use layout CSS for two-pane (sidebar width fixed, main flexible); add scroll containers for messages and sources.

## Open Points to Finalize
- Backend upload endpoint path/payload/response.
- `/conversations` schema (fields and read API for history).
- Whether backend can emit intermediate tool/plan events; if not, front will synthesize milestones from stream progression.
- Any auth/session to add later; thread_id currently client-generated.

## Completion Checklist
- [ ] Streaming hook wired to `/chat/stream`, abortable.
- [ ] Chat UI with message list, streaming assistant bubble, user bubbles, and toolbar.
- [ ] Inline citations + Sources panel fed from `done.sources`.
- [ ] Steps/plan strip showing retrieval/websearch/generation/hallucination retry status.
- [ ] File attach UI with 25 MB limit and backend hook/stub.
- [ ] Sidebar history integrated with `/conversations` (POST now, GET later) and thread switching.
- [ ] Error and empty states; loader/shimmer.
- [ ] Theming consistent with `new-york`; responsive layout.
