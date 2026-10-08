import logfire
from app.agents.state import AgentState
from app.config import settings
from langchain_groq import ChatGroq
from app.agents.nodes.prompts.responder_prompt import technical_prompt, conversational_prompt
from app.gateway import portkey_client, extract_cache_status


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
      prompt_value = conversational_prompt.invoke({
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

      prompt_value = technical_prompt.invoke({
         "context": full_context,
         "history": history_str,
         "user_message": user_msg
      })

   messages = [
      {
         "role": "system" if msg.type == "system" else "user" if msg.type == "human" else msg.type,
         "content": msg.content,
      }
      for msg in prompt_value.to_messages()
   ]

   with logfire.span("LLM Synthesis"):
      try:
         response = portkey_client.chat.completions.create(
            model=settings.GROQ_MODEL,
            messages=messages,
            temperature=0.1
         )
         content = response.choices[0].message.content
         cache_status = extract_cache_status(response)
         is_cache_hit = cache_status == "HIT"

         if is_cache_hit:
            logfire.info("Gateway cache hit - response served from Portkey")
            plan_update = state["plan"] + ["Cache: Hit"]
            status = "Cache Hit - Instant Response"
         else:
            logfire.info("Response synthesised via LLM.")
            plan_update = state["plan"]
            status = "Response generated"

         return {
            "final_answer" : content,
            "status":status,
            "plan":plan_update,
            "messages":[{"role":"assistant","content":content}]
         }

      except Exception as e:
         logfire.error(f"LLM Genration failed: {e}")