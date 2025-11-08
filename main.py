from fastapi import FastAPI, HTTPException, UploadFile
import os
from dotenv import load_dotenv
from pydantic import BaseModel
import google.generativeai as genai
import shutil
import io

app = FastAPI()

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL_NAME = os.getenv("GEMINI_MODEL_NAME")

if not GEMINI_API_KEY or not GEMINI_MODEL_NAME:
    raise ValueError("GEMINI_API_KEY or GEMINI_MODEL_NAME not found in environment variables")

genai.configure(api_key=GEMINI_API_KEY)


class Question(BaseModel):
    system: str | None = "You are a helpful assistant."
    question: str

@app.get("/")
def read_root():
    return "Hello World!"

@app.post("/uploadfile/")
async def upload_file(file: UploadFile):
    allowed_extensions = ["txt", "pdf"]
    
    file_extension = file.filename.split(".")[-1]
    if file_extension not in allowed_extensions:
        raise HTTPException(status_code=400, detail="Invalid file type. Only .txt and .pdf are allowed.")
    
    FOLDER = "sources"
    try: 
        os.makedirs(FOLDER, exist_ok=True)
        
        file_location = os.path.join(FOLDER, file.filename)
        file_content = await file.read()
        with open(file_location, "wb+") as file_object:
            # Convert bytes content to a file-like object
            file_like_object = io.BytesIO(file_content)
             # Use shutil.copyfileobj for secure file writing
            shutil.copyfileobj(file_like_object, file_object)
            
        return {"info": "File saved", "filename": file.filename}
    except Exception as e:
        print(f"Error saving file: {e}")
        return HTTPException(status_code=500, detail="Error saving file.")

@app.post("/ask")
async def ask_question(question: Question):
    try:
        model = genai.GenerativeModel(GEMINI_MODEL_NAME)
        response = model.generate_content([
            question.system,
            question.question
        ])
        return {"response": response.text}
    except Exception as e:
        return HTTPException(status_code=500, detail=str(e))