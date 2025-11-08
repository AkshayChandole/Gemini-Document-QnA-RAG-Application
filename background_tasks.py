from sqlalchemy.orm import Session
from db import FileChunk
import nltk
from nltk.tokenize import sent_tokenize
from dotenv import load_dotenv
import google.generativeai as genai
import os
from sentence_transformers import SentenceTransformer

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Configure Gemini API
genai.configure(api_key=GEMINI_API_KEY)

nltk.download('punkt')
nltk.download('punkt_tab')

class TextProcessor:
    def __init__(self, db: Session, file_id: int, chunk_size: int = 2):
        self.db = db
        self.file_id = file_id
        self.chunk_size = chunk_size
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        pass
    
    def chunk_and_embed(self, text: str):
        # Split text into sentences
        sentences = sent_tokenize(text)
        print(f"Sentences: {sentences} \n")
        
        # Chunk sentences (2 sentences per chunk by default)
        chunks = [
            " ".join(sentences[i:i + self.chunk_size])
            for i in range(0, len(sentences), self.chunk_size)
        ]
        print(f"Chunks: {chunks} \n")
        
        for chunk in chunks:
            # Generate embeddings using SentenceTransformer
            embeddings = self.model.encode(chunk).tolist()
            print(f"Embeddings: {embeddings} \n")
            
            # Store chunk and embedding in the database
            file_chunk = FileChunk(
                file_id=self.file_id,
                chunk_text=chunk,
                embedding_vector=embeddings
            )
            self.db.add(file_chunk)
        self.db.commit()
        print(f"✅ {len(chunks)} chunks embedded and stored successfully.")
