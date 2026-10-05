import logfire
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from app.agents.state import AgentState
from langchain_groq import ChatGroq
from app.config import settings
from app.agents.nodes.prompts.planner_prompt import planner_prompt
from typing import Literal


# Portkey-backed LLM: fallback + cache + retry — same .invoke() interface as ChatGroq
llm = ChatGroq(api_key=settings.GROQ_API_KEY, model=settings.GROQ_MODEL)



class PlannerDecision(BaseModel):
   """
   Structured output returned by the Planner LLM.

   The planner decides whether the latest user message can be
   handled conversationally or requires technical retrieval.
   """

   intent: Literal["conversational", "technical"] = Field(description=("Whether the user's latest message can be answered from conversation memory or requires technical retrieval."))
   search_query: str | None = Field(default=None,description=("A refined search query for technical retrieval.Must be null when intent is conversational."))


# Structured LLM 
structured_llm = llm.with_structured_output(PlannerDecision)



def planner_node(state: AgentState):
   """
   Analyze the conversation and determine whether the latest
   user message should be handled conversationally or routed
   to the technical retrieval workflow.

   The planner uses structured LLM output to produce a reliable
   intent classification and, when required, a refined search query.
   """


   # Get the conversation history(excluding the latest message)
   history = ""
   for msg in state["messages"][:-1]:
      role = "User" if msg["role"] == "user" else "Assistent"
      history += f"{role}: {msg['content']}\n"


   user_message = state["messages"][-1]["content"] if state["messages"] else ""


   with logfire.span("Planner Decision", user_message=user_message):
      # prompt
      prompt = planner_prompt.invoke({"history":history,"user_message":user_message})

      decision = structured_llm.invoke(prompt)
      logfire.info(f"Planner Decision Completed. Intent identified: {decision.intent}. Search_query = {decision.search_query}")
   
   if decision.intent == "conversational":
      return {
         "current_query": "CONVERSATIONAL",
         "status": "Handling conversationally (using memory)...",
         "plan": ["Intent: Conversational/Memory", "Retrieval: Skipped"]
      }

   search_query = decision.search_query or user_message
   return {
      "current_query": search_query,
      "status": f"Technical research needed. Searching for: {search_query}",
      "plan": ["Intent: Technical", f"Search Term: {search_query}"]
   }