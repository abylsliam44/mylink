"""
Vector Store Service using Qdrant
Handles document storage, retrieval, and similarity search
"""
import asyncio
from typing import List, Dict, Any, Optional
from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.http.models import Distance, VectorParams, PointStruct
import openai
import os
import logging

logger = logging.getLogger(__name__)

class VectorStore:
    def __init__(self):
        self.client = QdrantClient(
            host=os.getenv("QDRANT_HOST", "localhost"),
            port=int(os.getenv("QDRANT_PORT", "6333"))
        )
        self.collection_name = "smartbot_hr"
        self.embedding_model = "text-embedding-3-small"
        self.vector_size = 1536
        
        # Initialize OpenAI
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        
    async def initialize_collection(self):
        """Create collection if it doesn't exist"""
        try:
            collections = self.client.get_collections()
            collection_names = [col.name for col in collections.collections]
            
            if self.collection_name not in collection_names:
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=self.vector_size,
                        distance=Distance.COSINE
                    )
                )
                logger.info(f"Created collection: {self.collection_name}")
            else:
                logger.info(f"Collection {self.collection_name} already exists")
        except Exception as e:
            logger.error(f"Error initializing collection: {e}")
            raise
    
    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text using OpenAI"""
        try:
            from openai import AsyncOpenAI
            client = AsyncOpenAI(api_key=self.openai_api_key)
            response = await client.embeddings.create(
                model=self.embedding_model,
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            raise
    
    async def add_documents(self, documents: List[Dict[str, Any]]):
        """Add documents to vector store"""
        try:
            points = []
            for i, doc in enumerate(documents):
                # Generate embedding
                embedding = await self.generate_embedding(doc["text"])
                
                # Create point
                point = PointStruct(
                    id=i,
                    vector=embedding,
                    payload={
                        "text": doc["text"],
                        "metadata": doc.get("metadata", {}),
                        "source": doc.get("source", "unknown"),
                        "type": doc.get("type", "document")
                    }
                )
                points.append(point)
            
            # Upsert points
            self.client.upsert(
                collection_name=self.collection_name,
                points=points
            )
            logger.info(f"Added {len(documents)} documents to vector store")
            
        except Exception as e:
            logger.error(f"Error adding documents: {e}")
            raise
    
    async def search_similar(self, query: str, limit: int = 5, score_threshold: float = 0.7) -> List[Dict[str, Any]]:
        """Search for similar documents"""
        try:
            # Generate query embedding
            query_embedding = await self.generate_embedding(query)
            
            # Search
            results = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                limit=limit,
                score_threshold=score_threshold
            )
            
            # Format results
            documents = []
            for result in results:
                documents.append({
                    "text": result.payload["text"],
                    "metadata": result.payload["metadata"],
                    "source": result.payload["source"],
                    "type": result.payload["type"],
                    "score": result.score
                })
            
            return documents
            
        except Exception as e:
            logger.error(f"Error searching similar documents: {e}")
            raise
    
    async def search_by_filters(self, filters: Dict[str, Any], limit: int = 10) -> List[Dict[str, Any]]:
        """Search documents by metadata filters"""
        try:
            # Build filter conditions
            must_conditions = []
            for key, value in filters.items():
                must_conditions.append(
                    models.FieldCondition(
                        key=f"metadata.{key}",
                        match=models.MatchValue(value=value)
                    )
                )
            
            # Search with filters
            results = self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=models.Filter(must=must_conditions),
                limit=limit
            )
            
            # Format results
            documents = []
            for result in results[0]:  # results is tuple (points, next_page_offset)
                documents.append({
                    "text": result.payload["text"],
                    "metadata": result.payload["metadata"],
                    "source": result.payload["source"],
                    "type": result.payload["type"]
                })
            
            return documents
            
        except Exception as e:
            logger.error(f"Error searching by filters: {e}")
            raise

# Global instance
vector_store = VectorStore()
