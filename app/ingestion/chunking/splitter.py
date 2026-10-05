import logfire

from langchain_text_splitters import RecursiveCharacterTextSplitter
from typing import List


def chunk_text(text: str, chunk_size: int = 1500, chunk_overlap: int = 200) -> List[str]:
   """
   Split input text into smaller, overlapping chunks for RAG processing.

   Uses LangChain's RecursiveCharacterTextSplitter to preserve natural
   boundaries such as paragraphs, lines, sentences, and words while ensuring
   chunks remain within the configured size as much as possible.

   Args:
      text: The input text to split into chunks.
      chunk_size: Maximum target size of each chunk.
      chunk_overlap: Number of characters shared between consecutive chunks.

   Returns:
      A list of non-empty text chunks.
   """

   with logfire.span("Text Chunking", text_length=len(text)):
      if not text or not text.strip():
         return []

      splitter = RecursiveCharacterTextSplitter(
         chunk_size=chunk_size,
         chunk_overlap=chunk_overlap,
         separators=["\n\n", "\n", ". ", " ", "",],
      )

      chunks = splitter.split_text(text)

      valid_chunks = [
         chunk.strip()
         for chunk in chunks
         if chunk and chunk.strip()
      ]

      logfire.info(f"Generated {len(valid_chunks)} chunks")
      
      return valid_chunks