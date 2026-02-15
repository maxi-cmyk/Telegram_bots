import chromadb
from chromadb.utils import embedding_functions
import logging
import os
from config import CHROMA_DB_PATH, OLLAMA_MODEL
from ollama import Client

logger = logging.getLogger(__name__)

class RagEngine:
    def __init__(self):
        self.client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
        self.embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
        
        self.collection = self.client.get_or_create_collection(
            name="articles",
            embedding_function=self.embedding_fn
        )
        self.ollama = Client()

    def index_article(self, text, metadata):
        """
        Chunks and indexes an article. 
        metadata must include 'source', 'title', 'link', 'published_str'
        """
        try:
            # Simple chunking (checking size)
            # 1000 chars overlap 100
            chunk_size = 1000
            overlap = 100
            
            chunks = []
            ids = []
            metadatas = []
            
            if not text:
                return

            for i in range(0, len(text), chunk_size - overlap):
                chunk = text[i:i + chunk_size]
                if len(chunk) < 50: continue # Skip tiny chunks
                
                chunks.append(chunk)
                ids.append(f"{metadata['link']}_{i}")
                metadatas.append(metadata)
            
            if chunks:
                self.collection.upsert(
                    documents=chunks,
                    metadatas=metadatas,
                    ids=ids
                )
                logger.info(f"Indexed {len(chunks)} chunks for {metadata['title']}")
                
        except Exception as e:
            logger.error(f"Error indexing article {metadata.get('title')}: {e}")

    def query_similar(self, query, n_results=5):
        results = self.collection.query(
            query_texts=[query],
            n_results=n_results
        )
        return results

    def generate_answer(self, query):
        # 1. Retrieve relevant chunks
        results = self.query_similar(query, n_results=10) # Fetch more to ensure we get enough distinct sources
        
        if not results['documents'][0]:
            return "I couldn't find any relevant articles in my database to answer that."
            
        # Group chunks by source to limit to top 2 articles
        source_map = {} # link -> {title, chunks}
        
        for i, doc in enumerate(results['documents'][0]):
            meta = results['metadatas'][0][i]
            link = meta['link']
            
            if link not in source_map:
                source_map[link] = {
                    'title': meta['title'],
                    'chunks': []
                }
            source_map[link]['chunks'].append(doc)
            
        # Take top 2 sources (based on retrieval order, which implies relevance)
        top_links = list(source_map.keys())[:2]
        
        context_text = ""
        sources_text = ""
        
        for link in top_links:
            data = source_map[link]
            context_text += f"Article: {data['title']}\n"
            context_text += "\n".join(data['chunks'])
            context_text += "\n\n"
            sources_text += f"- [{data['title']}]({link})\n"
        
        # 2. Prompt Ollama
        prompt = f"""
        You are a helpful legal-tech assistant. Answer the user's question based ONLY on the following context.
        If the context doesn't contain the answer, say you don't know.
        
        Context:
        {context_text}
        
        Question: {query}
        
        Answer:
        """
        
        try:
            response = self.ollama.chat(
                model=OLLAMA_MODEL, 
                messages=[{'role': 'user', 'content': prompt}],
                options={'temperature': 0.3}
            )
            answer = response['message']['content']
            
            # Append sources
            answer += "\n\n📚 **Sources:**\n" + sources_text
            return answer
            
        except Exception as e:
            logger.error(f"Ollama generation failed: {e}")
            return "Sorry, I encountered an error generating the answer."
