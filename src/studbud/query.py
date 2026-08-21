from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .embeddings import Embedder
from .llm import Message
from .stores.base import SearchHit, VectorStore

DEFAULT_SYSTEM_PROMPT = (
    "You are StudBud, an AI study assistant for students in the Department of "
    "Information and Communication Technology (JTMK) at Politeknik Mukah. "
    "Your main purpose is to help students understand ICT subjects using the "
    "learning materials provided in the StudBud knowledge base. "
    "Use retrieved course materials as your primary source when they are relevant. "
    "Explain concepts in clear, simple language suitable for diploma students. "
    "For programming questions, identify errors, explain why they happen, provide hints, "
    "and guide the student step by step. You may provide small code examples when useful, "
    "but do not immediately complete an entire assignment, practical exercise, or project "
    "for the student. Encourage understanding and independent problem solving. "
    "If the retrieved context is incomplete, you may use reliable general ICT knowledge, "
    "but never invent facts or pretend the context contains information that it does not. "
    "Do not mention source filenames and do not use phrases such as 'According to the documents'. "
    "If a question is unrelated to ICT, programming, computing, or the supported academic "
    "materials, politely explain that StudBud is focused on JTMK academic support. "
    "Keep responses friendly, educational, concise, and conversational."
)


@dataclass
class RetrievedContext:
    hits: list[SearchHit]
    
    def to_prompt_block(self) -> str:
        if not self.hits:
            return "(no relevant context found)"
        parts = []
        for h in self.hits:
            name = Path(h.source_path).name
            parts.append(
                f"[source: {name}] | chunk {h.chunk_index} | score {h.score:.2f}\n"
                f"{h.text}"
            )
        return "\n\n---\n\n".join(parts)

def retrieve(
        store: VectorStore, embedder: Embedder, question: str, k: int
) -> RetrievedContext:
    [vec] = embedder.embed(question)
    return RetrievedContext(hits=store.search(question, vec, k))


def build_user_message(question: str, ctx: RetrievedContext) -> str :
    return(
        "Context: \n"
        f"{ctx.to_prompt_block()}\n\n"
        "Question: \n"
        f"{question}"
    )


def initial_messages(system_prompt: str | None) -> list[Message]:
    base = system_prompt if system_prompt is not None else DEFAULT_SYSTEM_PROMPT
    return [{"role": "system", "content": base}]