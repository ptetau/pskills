# `/quiz` — Inline Clarifier

`/quiz` asks clarifying questions, one at a time, before the work starts. The answers lock
the decisions (audience, scope, tone, approach). A back-and-forth prose conversation is
not necessary. Each question is a native picker that the user clicks. If there is no
picker, each question is a short plain-markdown question, and the user answers with a
letter.

`/quiz` plans its questions first, in a fixed order (purpose, style, scope, focus, next
step). Thus, the same request gets the same questions. `/quiz` recommends an option only
when something that the user said points to that option.

**Example**

```
/quiz a dashboard that shows real-time API health metrics
```

**Output** (plain-markdown fallback. With a picker, you can click the same options.)

> **Question 1 of 3 · Audience**
> Who is the primary audience for this dashboard?
>
> - **A · Engineers**: shows raw, dense metrics with no extra text, but it is hard for
>   anyone outside the team to read.
> - **B · Managers**: shows trends and status instead of raw numbers, but it hides the
>   detail that on-call staff need.
> - **C · Both**: gives an overview with a drill-down toggle, but it takes more work to
>   build.
>
> Reply A, B, or C. You can add a note, for example `B, keep it short`.

Reply with a letter. You can add a note (`B, include p99 latency`). `/quiz` echoes each
answer in one line (`✓ 1/3 Audience → Managers`). After the last question, `/quiz` shows
the resolved list for a final OK before the work starts.

`/quiz` has a limit of about 7 questions. When the options differ in how they look, sound, or work, use `/quiz-visual`.
