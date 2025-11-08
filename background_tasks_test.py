from db import SessionLocal, File
from background_tasks import TextProcessor

db = SessionLocal()

# Create a new file record
new_file = File(file_name="sample.txt")
db.add(new_file)
db.commit()
db.refresh(new_file)

print(f"Created file with ID: {new_file.file_id}")


processor = TextProcessor(db=db, file_id=new_file.file_id, chunk_size=2)
processor.chunk_and_embed("My Name is John. I live in New York. I love programming in Python. FastAPI is my favorite web framework. I am from the USA.")
