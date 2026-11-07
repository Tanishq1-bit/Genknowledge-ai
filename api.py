from typing import List, Literal
from fastapi import UploadFile, File, HTTPException
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from tempfile import NamedTemporaryFile
import os
from main import retriever, llm, prompt, vectorstore

from fastapi import FastAPI
from pydantic import BaseModel
from langchain_core.messages import HumanMessage, AIMessage

from main import retriever, llm, prompt  

app = FastAPI(title="GenKnowledge AI API")


class Message(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    question: str
    history: List[Message] = []


@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/upload")
def upload_document(file: UploadFile = File(...)):

    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Only PDF files are supported.")

    temp_path = None

    try:
        with NamedTemporaryFile(suffix=".pdf", delete=False) as temp:
            temp_path = temp.name
            temp.write(file.file.read())

    
        loader = PyPDFLoader(temp_path)
        documents = loader.load()

        if not documents:
            raise HTTPException(400, "PDF contains no readable pages.")

        
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=50
        )

        chunks = splitter.split_documents(documents)

        
        vectorstore.add_documents(chunks)

        return {
            "message": "Document uploaded successfully!",
            "filename": file.filename,
            "chunks_added": len(chunks)
        }

    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)


@app.post("/chat")
def chat(req: ChatRequest):
    docs = retriever.invoke(req.question)
    context = "\n\n".join(d.page_content for d in docs)

    history = [
        HumanMessage(content=m.content) if m.role == "user" else AIMessage(content=m.content)
        for m in req.history[-8:]
    ]

    final_prompt = prompt.invoke({
        "context": context,
        "question": req.question,
        "chat_history": history,
    })
    response = llm.invoke(final_prompt)

    sources = [
        {
            "page": d.metadata["page"] + 1 if isinstance(d.metadata.get("page"), int) else None,
            "text": d.page_content[:300],
        }
        for d in docs
    ]
    return {"answer": response.content, "sources": sources}

class QuizRequest(BaseModel):
    topic: str


@app.post("/quiz")
def generate_quiz(req: QuizRequest):

    docs = retriever.invoke(req.topic)

    if not docs:
        raise HTTPException(404, "No relevant course material found.")

    context = "\n\n".join(d.page_content for d in docs)

    quiz_prompt = f"""
    Create exactly 5 MCQs about {req.topic}.

    Use ONLY this context:
    {context}

    Return ONLY valid JSON. No markdown or extra text.

    Format:
    {{
      "questions": [
        {{
          "question": "Question",
          "options": {{
            "A": "Option 1",
            "B": "Option 2",
            "C": "Option 3",
            "D": "Option 4"
          }},
          "answer": "B",
          "explanation": "Explanation"
        }}
      ]
    }}
    """

    response = llm.invoke(quiz_prompt)

    return {"quiz": response.content}