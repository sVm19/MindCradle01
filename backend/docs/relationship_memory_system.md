# Relationship Memory System

## Architecture

ARIA stores durable relationship memories in `user_relationship_memories`.
Chat transcripts are not used as long-term memory. New chat records keep `messages = []` and store only operational metadata such as response type, personalization flags, and `user_message_count`.

Memory creation happens after an ARIA reply. The extractor sees only the current verified exchange plus linked latest mood/journal metadata. It may create up to two memory objects. If it cannot cite source evidence from the supplied exchange, it saves nothing.

## Database Schema

`user_relationship_memories` fields:

- `title`
- `type`
- `importance`
- `emotion`
- `confidence`
- `related_journal`
- `related_mood`
- `first_occurrence`
- `last_occurrence`
- `times_referenced`
- `supporting_evidence`

RLS restricts rows to the owning user. Ranking indexes support lookup by user, importance, recency, and reference count.

## Retrieval Algorithm

1. Load the user's top candidate memories from `user_relationship_memories`.
2. Locally rank the candidates.
3. Inject only the ranked memory objects into ARIA's prompt.
4. If no verified memory exists, instruct ARIA not to say it remembers anything.

## Ranking Algorithm

The score combines:

- importance: 45%
- recency: 25%
- relationship significance: 20%
- confidence: 10%

Relationship significance is derived from reference count, supporting evidence, and linked mood/journal records.

## Conversation Behavior

ARIA may naturally say things like:

- "I remember when this used to worry you."
- "You've overcome similar situations before."
- "You first mentioned this project a while ago."

It may only do this when the ranked verified memory objects support the reference.

## Tests

`backend/tests/test_relationship_memory.py` covers ranking order, recency, relationship significance, and no-memory prompt formatting.
