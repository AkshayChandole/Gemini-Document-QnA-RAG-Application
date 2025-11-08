from fastapi import FastAPI, UploadFile, HTTPException, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import select
from dotenv import load_dotenv
from pydantic import BaseModel
import google.generativeai as genai
import os
import io
import shutil

from db import get_db, File, FileChunk
from file_parser import FileParser
from background_tasks import TextProcessor
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse


# Load environment variables
load_dotenv()

# Configure Gemini API
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL_NAME = os.getenv("GEMINI_MODEL_NAME", "gemini-2.5-flash-lite")

genai.configure(api_key=GEMINI_API_KEY)

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")


# ---------- Request Models ----------
class QuestionModel(BaseModel):
    question: str

class AskModel(BaseModel):
    document_id: int
    question: str


# ---------- ROUTES ----------

@app.get("/")
async def serve_ui():
    return FileResponse("static/index.html")

@app.get("/get-uploaded-files/")
async def root(db: Session = Depends(get_db)):
    """List all uploaded files"""
    files = db.scalars(select(File)).all()
    return [{"file_id": f.file_id, "file_name": f.file_name} for f in files]


@app.post("/uploadfile/")
async def upload_file(background_tasks: BackgroundTasks, file: UploadFile, db: Session = Depends(get_db)):
    """Upload and process a file in the background"""
    allowed_extensions = ["txt", "pdf"]
    file_extension = file.filename.split('.')[-1]

    if file_extension not in allowed_extensions:
        raise HTTPException(status_code=400, detail="File type not allowed")

    folder = "sources"
    os.makedirs(folder, exist_ok=True)
    file_path = os.path.join(folder, file.filename)

    try:
        # Save the uploaded file
        file_content = await file.read()
        with open(file_path, "wb+") as f:
            shutil.copyfileobj(io.BytesIO(file_content), f)

        # Parse the file content
        content_parser = FileParser(file_path)
        file_text_content = content_parser.parse()

        # Save file metadata in DB
        new_file = File(file_name=file.filename, file_content=file_text_content)
        db.add(new_file)
        db.commit()
        db.refresh(new_file)

        # Process embeddings in background
        background_tasks.add_task(TextProcessor(db, new_file.file_id).chunk_and_embed, file_text_content)

        return {"info": f"✅ File '{file.filename}' uploaded and processing started", "file_id": new_file.file_id}

    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ---------- Helper Function ----------
async def get_similar_chunks(file_id: int, question: str, db: Session):
    """Retrieve top 10 similar chunks using L2 distance"""
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer('all-MiniLM-L6-v2')

    question_embedding = model.encode(question).tolist()

    similar_chunks_query = (
        select(FileChunk)
        .where(FileChunk.file_id == file_id)
        .order_by(FileChunk.embedding_vector.l2_distance(question_embedding))
        .limit(10)
    )

    return db.scalars(similar_chunks_query).all()


# ---------- ASK Endpoint ----------
@app.post("/ask/")
async def ask_question(request: AskModel, db: Session = Depends(get_db)):
    """Answer a question using context retrieved from the document"""
    try:
        similar_chunks = await get_similar_chunks(request.document_id, request.question, db)
        context = " ".join(chunk.chunk_text for chunk in similar_chunks)

        # Prepare Gemini prompt
        prompt = f"""
        You are a helpful assistant.
        Use the following document context to answer the question.

        Context:
        {context}

        Question:
        {request.question}
        """

        # Call Gemini model
        response = genai.GenerativeModel(GEMINI_MODEL_NAME).generate_content(prompt)
        answer = response.text if response.text else "⚠️ No response generated."

        return {"response": answer}

    except Exception as e:
        print(f"Error in /ask/: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/find-similar-chunks/{file_id}")
async def find_similar_chunks_endpoint(file_id: int, question_data: QuestionModel, db: Session = Depends(get_db)):
    """Return top 10 most similar chunks for debugging or visualization"""
    try:
        similar_chunks = await get_similar_chunks(file_id, question_data.question, db)
        return [{"chunk_id": c.chunk_id, "chunk_text": c.chunk_text} for c in similar_chunks]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
