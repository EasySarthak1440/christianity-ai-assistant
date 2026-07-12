from __future__ import annotations

import os

from crewai import LLM, Agent, Crew, Process, Task

from vector_store import VectorStore


class RAGCrew:
    def __init__(self, vs: VectorStore, query: str, top_k: int = 8, source_filter: str | None = None):
        self.vs = vs
        self.query = query
        self.top_k = top_k
        self.source_filter = source_filter
        self._results: list[dict] = []
        self._context: str = ""
        self._answer: str = ""

    def _get_llm(self) -> LLM:
        return LLM(
            model="llama-3.3-70b-versatile",
            provider="openai",
            base_url="https://api.groq.com/openai/v1",
            api_key=os.environ.get("GROQ_API_KEY", ""),
            temperature=0,
        )

    def _create_agents(self) -> list[Agent]:
        llm = self._get_llm()
        return [
            Agent(
                role="Research Analyst",
                goal="Find the most relevant information from document sources to answer the user query",
                backstory="Expert at analyzing document corpora and extracting key information using hybrid search techniques.",
                llm=llm,
                allow_delegation=False,
                verbose=False,
            ),
            Agent(
                role="Information Synthesizer",
                goal="Synthesize retrieved information into a coherent, well-structured answer",
                backstory="Expert at combining information from multiple sources into clear, factual responses with proper citations.",
                llm=llm,
                allow_delegation=False,
                verbose=False,
            ),
            Agent(
                role="Quality Reviewer",
                goal="Verify the answer is accurate, complete, and properly cited",
                backstory="Detail-oriented reviewer ensuring answers are faithful to source material and properly reference their origins.",
                llm=llm,
                allow_delegation=False,
                verbose=False,
            ),
        ]

    def run(self) -> dict:
        agents = self._create_agents()
        research_agent, synthesis_agent, reviewer_agent = agents

        retrieve_task = Task(
            description=(
                f"Search the document store for information relevant to: '{self.query}'\n"
                f"Return the top {self.top_k} most relevant chunks with their sources and scores."
            ),
            expected_output="A list of relevant document chunks with source, page, and relevance score.",
            agent=research_agent,
        )

        synthesize_task = Task(
            description=(
                f"Using the retrieved document chunks, synthesize an answer to: '{self.query}'\n"
                "Base the answer strictly on the provided context. Cite sources. "
                "Do not make up facts not present in the context."
            ),
            expected_output="A concise, factual answer with source citations.",
            agent=synthesis_agent,
        )

        review_task = Task(
            description=(
                "Review the synthesized answer for accuracy, completeness, and proper source attribution. "
                "Ensure no hallucinated facts are present."
            ),
            expected_output="The final verified answer with any corrections applied.",
            agent=reviewer_agent,
        )

        crew = Crew(
            agents=agents,
            tasks=[retrieve_task, synthesize_task, review_task],
            process=Process.sequential,
            verbose=False,
        )

        result = crew.kickoff()
        return {"answer": str(result), "results": self._results}
