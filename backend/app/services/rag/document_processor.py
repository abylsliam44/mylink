"""
Document Processing Service
Handles text chunking, cleaning, and preparation for vector storage
"""
import re
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

class DocumentProcessor:
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
    
    def clean_text(self, text: str) -> str:
        """Clean and normalize text"""
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        # Remove special characters but keep punctuation
        text = re.sub(r'[^\w\s.,!?;:()-]', '', text)
        # Remove multiple dots
        text = re.sub(r'\.{3,}', '...', text)
        return text.strip()
    
    def chunk_text(self, text: str, metadata: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Split text into overlapping chunks"""
        if not text or len(text) < self.chunk_size:
            return [{
                "text": self.clean_text(text),
                "metadata": metadata or {},
                "source": metadata.get("source", "unknown") if metadata else "unknown",
                "type": metadata.get("type", "document") if metadata else "document"
            }]
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + self.chunk_size
            
            # Try to break at sentence boundary
            if end < len(text):
                # Look for sentence endings
                sentence_end = text.rfind('.', start, end)
                if sentence_end == -1:
                    sentence_end = text.rfind('!', start, end)
                if sentence_end == -1:
                    sentence_end = text.rfind('?', start, end)
                
                if sentence_end > start:
                    end = sentence_end + 1
            
            chunk_text = text[start:end].strip()
            if chunk_text:
                chunks.append({
                    "text": self.clean_text(chunk_text),
                    "metadata": {
                        **(metadata or {}),
                        "chunk_index": len(chunks),
                        "start_pos": start,
                        "end_pos": end
                    },
                    "source": metadata.get("source", "unknown") if metadata else "unknown",
                    "type": metadata.get("type", "document") if metadata else "document"
                })
            
            start = end - self.chunk_overlap
            if start >= len(text):
                break
        
        return chunks
    
    def process_job_description(self, job_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Process job description into chunks"""
        text_parts = []
        
        # Title
        if job_data.get("title"):
            text_parts.append(f"Должность: {job_data['title']}")
        
        # Description
        if job_data.get("description"):
            text_parts.append(f"Описание: {job_data['description']}")
        
        # Requirements
        if job_data.get("requirements"):
            if isinstance(job_data["requirements"], list):
                req_text = "Требования: " + ", ".join(job_data["requirements"])
            else:
                req_text = f"Требования: {job_data['requirements']}"
            text_parts.append(req_text)
        
        # Location and salary
        if job_data.get("location"):
            text_parts.append(f"Локация: {job_data['location']}")
        
        if job_data.get("salary_min") or job_data.get("salary_max"):
            salary_text = "Зарплата: "
            if job_data.get("salary_min"):
                salary_text += f"от {job_data['salary_min']}"
            if job_data.get("salary_max"):
                salary_text += f" до {job_data['salary_max']}"
            text_parts.append(salary_text)
        
        full_text = "\n".join(text_parts)
        
        metadata = {
            "job_id": job_data.get("id"),
            "employer_id": job_data.get("employer_id"),
            "title": job_data.get("title"),
            "location": job_data.get("location"),
            "source": "job_description",
            "type": "job"
        }
        
        return self.chunk_text(full_text, metadata)
    
    def process_cv_text(self, cv_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Process CV text into chunks"""
        text_parts = []
        
        # Basic info
        if cv_data.get("full_name"):
            text_parts.append(f"Кандидат: {cv_data['full_name']}")
        
        if cv_data.get("city"):
            text_parts.append(f"Город: {cv_data['city']}")
        
        if cv_data.get("email"):
            text_parts.append(f"Email: {cv_data['email']}")
        
        # Resume text
        if cv_data.get("resume_text"):
            text_parts.append(f"Резюме: {cv_data['resume_text']}")
        
        full_text = "\n".join(text_parts)
        
        metadata = {
            "candidate_id": cv_data.get("id"),
            "full_name": cv_data.get("full_name"),
            "city": cv_data.get("city"),
            "source": "cv_text",
            "type": "candidate"
        }
        
        return self.chunk_text(full_text, metadata)
    
    def process_hr_knowledge(self, knowledge_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Process HR knowledge base into chunks"""
        text = knowledge_data.get("text", "")
        metadata = {
            "category": knowledge_data.get("category", "general"),
            "source": "hr_knowledge",
            "type": "knowledge"
        }
        
        return self.chunk_text(text, metadata)

# Global instance
document_processor = DocumentProcessor()
