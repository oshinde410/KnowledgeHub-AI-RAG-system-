# Plan (Chat streaming UI overwrite fix)

## Information gathered
- Bug is in the frontend streaming handler in `frontend/src/App.tsx`.
- Current code, on every `token`, finds the **last** assistant message in the whole conversation and overwrites it.
- When the user sends question2, streaming continues and overwrites the assistant message created for question1.

## Plan
- Edit only `frontend/src/App.tsx` in `askWithWebSocket()`.
- Maintain a per-request `assistantMessageId` (created on the first token of that request).
- On subsequent tokens update that specific assistant message id.
- On `done`, finalize the same assistant message id.
- Keep the same `conversation_id` for all questions in the same chat (no new conversation per Q/A).

## Dependent Files to edit
- `frontend/src/App.tsx`

## Followup steps
- Run `npm run build` in `frontend/` to ensure TypeScript compiles.
- Manually test: ask Q1 then Q2 in same conversation; verify UI shows Q1,A1 then Q2,A2 without overwriting A1.

