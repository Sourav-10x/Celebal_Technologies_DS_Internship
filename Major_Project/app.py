import os
import shutil
from typing import Optional

from fastapi import (
    FastAPI,
    File,
    UploadFile,
    HTTPException,
    Request
)

from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from rag_engine import RAGEngine


# ============================================================
# APPLICATION
# ============================================================

app = FastAPI(
    title="Alexa - AI-Powered Study Assistant",
    description=(
        "Intelligent RAG-powered study workspace with "
        "voice, flashcards, quiz generator, and custom UI."
    ),
    version="2.0.0"
)


# ============================================================
# DIRECTORIES
# ============================================================

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

UPLOAD_DIR = os.path.join(
    BASE_DIR,
    "uploads"
)

SAMPLE_DIR = os.path.join(
    BASE_DIR,
    "sample_notes"
)

STATIC_DIR = os.path.join(
    BASE_DIR,
    "static"
)

TEMPLATES_DIR = os.path.join(
    BASE_DIR,
    "templates"
)


# Create directories if they don't exist

os.makedirs(
    UPLOAD_DIR,
    exist_ok=True
)

os.makedirs(
    SAMPLE_DIR,
    exist_ok=True
)

os.makedirs(
    STATIC_DIR,
    exist_ok=True
)

os.makedirs(
    TEMPLATES_DIR,
    exist_ok=True
)


# ============================================================
# STATIC FILES + TEMPLATES
# ============================================================

app.mount(
    "/static",
    StaticFiles(
        directory=STATIC_DIR
    ),
    name="static"
)

templates = Jinja2Templates(
    directory=TEMPLATES_DIR
)


# ============================================================
# RAG ENGINE
# ============================================================

rag = RAGEngine()


# ============================================================
# SAMPLE STUDY GUIDE
# ============================================================

SAMPLE_FILENAME = (
    "ai_rag_study_guide.txt"
)

SAMPLE_FILE = os.path.join(
    SAMPLE_DIR,
    SAMPLE_FILENAME
)


def sample_already_loaded() -> bool:
    """
    Checks whether the sample document is already
    present in the current RAG document registry.
    """

    for document in rag.documents.values():

        if document.get(
            "filename"
        ) == SAMPLE_FILENAME:

            return True

    return False


def load_sample_if_available():
    """
    Automatically loads the sample study guide
    when the application starts.
    """

    if not os.path.exists(
        SAMPLE_FILE
    ):

        print(
            "Sample study guide not found:"
        )

        print(
            SAMPLE_FILE
        )

        return

    if sample_already_loaded():

        print(
            "Sample study guide is already loaded."
        )

        return

    try:

        result = rag.process_file(
            SAMPLE_FILE,
            SAMPLE_FILENAME
        )

        print(
            "Loaded default sample study guide."
        )

        print(
            f"Chunks indexed: "
            f"{result.get('chunk_count', 0)}"
        )

        print(
            f"Words processed: "
            f"{result.get('word_count', 0)}"
        )

    except Exception as error:

        print(
            f"Sample load notice: {error}"
        )


# Load sample when server starts

load_sample_if_available()


# ============================================================
# PYDANTIC SCHEMAS
# ============================================================

class ChatQueryRequest(BaseModel):

    query: str

    doc_id: Optional[str] = None


class SettingsRequest(BaseModel):

    api_key: Optional[str] = ""


# ============================================================
# HOME PAGE
# ============================================================

@app.get(
    "/",
    response_class=HTMLResponse
)
async def read_root(
    request: Request
):

    """
    Renders Alexa Study Assistant UI.
    """

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "request": request
        }
    )


# ============================================================
# UPLOAD DOCUMENT
# ============================================================

@app.post(
    "/api/upload"
)
async def upload_document(
    file: UploadFile = File(...)
):

    """
    Uploads and processes a study document
    into the RAG vector store.
    """

    allowed_exts = {
        ".pdf",
        ".docx",
        ".txt",
        ".md",
        ".py",
        ".json",
        ".csv"
    }

    filename = (
        file.filename
        or "uploaded_doc.txt"
    )

    ext = os.path.splitext(
        filename
    )[1].lower()

    # --------------------------------------------------------
    # Validate extension
    # --------------------------------------------------------

    if ext not in allowed_exts:

        raise HTTPException(
            status_code=400,
            detail=(
                f"Unsupported file type '{ext}'. "
                "Allowed: PDF, DOCX, TXT, MD, PY, JSON, CSV"
            )
        )

    # --------------------------------------------------------
    # Prevent unsafe path traversal
    # --------------------------------------------------------

    safe_filename = os.path.basename(
        filename
    )

    file_path = os.path.join(
        UPLOAD_DIR,
        safe_filename
    )

    try:

        # ----------------------------------------------------
        # Save uploaded file
        # ----------------------------------------------------

        with open(
            file_path,
            "wb"
        ) as buffer:

            shutil.copyfileobj(
                file.file,
                buffer
            )

        # ----------------------------------------------------
        # Process document
        # ----------------------------------------------------

        result = rag.process_file(
            file_path,
            safe_filename
        )

        return {
            "status": "success",

            "message": (
                f"Successfully processed "
                f"'{safe_filename}'!"
            ),

            "data": result
        }

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=(
                f"Failed to process document: "
                f"{str(error)}"
            )
        )


# ============================================================
# LOAD SAMPLE DOCUMENT
# ============================================================

@app.post(
    "/api/load_sample"
)
async def load_sample_document():

    """
    Loads the pre-packaged sample RAG study guide.
    Prevents duplicate indexing.
    """

    # --------------------------------------------------------
    # Check sample file
    # --------------------------------------------------------

    if not os.path.exists(
        SAMPLE_FILE
    ):

        return {
            "status": "error",

            "message": (
                "Sample file not found. "
                "Please make sure this file exists:\n"
                f"{SAMPLE_FILE}"
            )
        }

    # --------------------------------------------------------
    # Already loaded
    # --------------------------------------------------------

    if sample_already_loaded():

        # Find existing sample
        existing_document = None

        for doc_id, document in (
            rag.documents.items()
        ):

            if document.get(
                "filename"
            ) == SAMPLE_FILENAME:

                existing_document = {
                    "doc_id": doc_id,
                    "filename": document.get(
                        "filename"
                    ),
                    "word_count": document.get(
                        "word_count",
                        0
                    ),
                    "page_count": document.get(
                        "page_count",
                        1
                    ),
                    "chunk_count": document.get(
                        "chunk_count",
                        0
                    )
                }

                break

        return {
            "status": "success",

            "message": (
                "Sample RAG notes are already loaded."
            ),

            "data": existing_document
        }

    # --------------------------------------------------------
    # Load sample
    # --------------------------------------------------------

    try:

        result = rag.process_file(
            SAMPLE_FILE,
            SAMPLE_FILENAME
        )

        return {
            "status": "success",

            "message": (
                "Sample RAG notes loaded "
                "into vector index!"
            ),

            "data": result
        }

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=(
                f"Failed to load sample document: "
                f"{str(error)}"
            )
        )


# ============================================================
# DOCUMENT LIST + STATISTICS
# ============================================================

@app.get(
    "/api/documents"
)
async def get_documents():

    """
    Returns indexed documents and vector statistics.
    """

    documents = []

    total_chunks = 0

    total_words = 0

    # --------------------------------------------------------
    # Iterate through RAG documents
    # --------------------------------------------------------

    for doc_id, info in (
        rag.documents.items()
    ):

        chunk_count = info.get(
            "chunk_count",
            0
        )

        word_count = info.get(
            "word_count",
            0
        )

        total_chunks += chunk_count

        total_words += word_count

        # IMPORTANT:
        # rag_engine.py uses "extension",
        # not "ext".

        extension = info.get(
            "extension",
            info.get(
                "ext",
                ""
            )
        )

        documents.append({

            "id":
                doc_id,

            "filename":
                info.get(
                    "filename",
                    "Unknown"
                ),

            "ext":
                extension,

            "word_count":
                word_count,

            "page_count":
                info.get(
                    "page_count",
                    1
                ),

            "chunk_count":
                chunk_count
        })

    return {

        "documents":
            documents,

        "total_documents":
            len(documents),

        "total_chunks":
            total_chunks,

        "total_words":
            total_words
    }


# ============================================================
# DELETE DOCUMENT
# ============================================================

@app.delete(
    "/api/documents/{doc_id}"
)
async def delete_document(
    doc_id: str
):

    """
    Deletes a document from the RAG vector store.
    """

    if doc_id not in rag.documents:

        raise HTTPException(
            status_code=404,
            detail="Document not found."
        )

    try:

        # ----------------------------------------------------
        # Remove from RAG engine
        # ----------------------------------------------------

        rag.remove_document(
            doc_id
        )

        return {

            "status":
                "success",

            "message":
                "Document removed from RAG database."
        }

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=(
                f"Failed to remove document: "
                f"{str(error)}"
            )
        )


# ============================================================
# RAG CHAT
# ============================================================

@app.post(
    "/api/chat"
)
async def chat_rag(
    req: ChatQueryRequest
):

    """
    Retrieves relevant document chunks and
    generates a context-based answer.
    """

    query = (
        req.query or ""
    ).strip()

    if not query:

        raise HTTPException(
            status_code=400,
            detail="Query cannot be empty."
        )

    try:

        result = rag.ask(
            query,
            req.doc_id
        )

        return result

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=(
                f"RAG query failed: "
                f"{str(error)}"
            )
        )


# ============================================================
# SUMMARY
# ============================================================

@app.get(
    "/api/summarize"
)
async def get_summary(
    doc_id: Optional[str] = None
):

    """
    Generates executive document summary
    and key takeaways.
    """

    try:

        return rag.generate_summary(
            doc_id
        )

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=(
                f"Summary generation failed: "
                f"{str(error)}"
            )
        )


# ============================================================
# FLASHCARDS
# ============================================================

@app.get(
    "/api/flashcards"
)
async def get_flashcards(
    count: int = 6
):

    """
    Generates active-recall flashcards
    from study material.
    """

    # Prevent unreasonable values

    count = max(
        1,
        min(
            count,
            30
        )
    )

    try:

        cards = rag.generate_flashcards(
            count=count
        )

        return {

            "flashcards":
                cards,

            "total":
                len(cards)
        }

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=(
                f"Flashcard generation failed: "
                f"{str(error)}"
            )
        )


# ============================================================
# QUIZ
# ============================================================

@app.get(
    "/api/quiz"
)
async def get_quiz(
    count: int = 4
):

    """
    Generates an automated multiple-choice
    quiz from study notes.
    """

    count = max(
        1,
        min(
            count,
            20
        )
    )

    try:

        quizzes = rag.generate_quiz(
            count=count
        )

        return {

            "quiz":
                quizzes,

            "total":
                len(quizzes)
        }

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=(
                f"Quiz generation failed: "
                f"{str(error)}"
            )
        )


# ============================================================
# KEY CONCEPTS
# ============================================================

@app.get(
    "/api/concepts"
)
async def get_concepts():

    """
    Generates key concept breakdown
    and frequency tags.
    """

    try:

        concepts = (
            rag.get_key_concepts()
        )

        return {
            "concepts":
                concepts
        }

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=(
                f"Concept generation failed: "
                f"{str(error)}"
            )
        )


# ============================================================
# SETTINGS
# ============================================================

@app.post(
    "/api/settings"
)
async def save_settings(
    req: SettingsRequest
):

    """
    Updates the Gemini API key used
    by the RAG engine.
    """

    try:

        if req.api_key is not None:

            rag.set_api_key(
                req.api_key
            )

        return {

            "status":
                "success",

            "message":
                "Settings updated successfully!"
        }

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=(
                f"Failed to update settings: "
                f"{str(error)}"
            )
        )


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get(
    "/api/health"
)
async def health_check():

    """
    Simple backend health check.
    Useful for debugging the frontend.
    """

    return {

        "status":
            "online",

        "service":
            "Alexa RAG Study Assistant",

        "documents":
            len(rag.documents),

        "chunks":
            sum(
                info.get(
                    "chunk_count",
                    0
                )
                for info
                in rag.documents.values()
            )
    }


# ============================================================
# START SERVER
# ============================================================
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app:app",
        host="127.0.0.1",
        port=8000,
        reload=True
    )