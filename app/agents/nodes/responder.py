import logfire
from app.agents.state import AgentState
from app.config import settings
from langchain_groq import ChatGroq
from app.agents.nodes.prompts.responder_prompt import technical_prompt, conversational_prompt

# Portkey-backed LLM: fallback + cache + retry — same .invoke() interface as ChatGroq
llm = ChatGroq(api_key=settings.GROQ_API_KEY, model=settings.GROQ_MODEL)



def generate_node(state: AgentState):
   """
   Synthesizes a response using both Documentation Context AND Conversation
   """

   query = state["current_query"]

   # Get the conversation history(excluding the latest message)
   history_str = ""
   for msg in state["messages"][:-1]:
      role = "User" if msg["role"] == "user" else "Assistent"
      history_str += f"{role}: {msg['content']}\n"


   user_msg = state["messages"][-1]["content"] if state["messages"] else ""



   if query == "CONVERSATIONAL":
      logfire.info("Generating conversational response using memory.")
      prompt = conversational_prompt.invoke({
            "history": history_str,
            "user_message": user_msg
      })
   else:
      logfire.info("Generating technical RAG response.")
      max_context_chars = 25000
      full_context = ""

      for doc in state["documents"]:
         if len(full_context) + len(doc) < max_context_chars:
               full_context += doc + "\n\n"
         else:
               logfire.warning("Context truncated to fit Groq TPM limits.")
               break

      prompt = technical_prompt.invoke({
         "context": full_context,
         "history": history_str,
         "user_message": user_msg
      })

   with logfire.span("LLM Synthesis"):
      try:
         content = llm.invoke(prompt).content
         logfire.info("Response sythesised vida LLM.")

         return {
            "final_answer" : content,
            "status" : "Response generated.",
            "plan" : state["plan"],
            "messages" : [{"role":"assistant","content":content}]
         }

      except Exception as e:
         logfire.error(f"LLM Genration failed: {e}")