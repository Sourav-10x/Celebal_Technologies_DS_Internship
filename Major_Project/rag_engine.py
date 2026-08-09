import os
import re
import json
import math
import uuid
from typing import List, Dict, Any, Optional
import numpy as np

# Optional imports with fallbacks
try:
    import pypdf
except ImportError:
    pypdf = None

try:
    import docx
except ImportError:
    docx = None

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
except ImportError:
    TfidfVectorizer = None
    cosine_similarity = None


class DocumentExtractor:
    """Extracts text content and metadata from multiple file formats."""

    @staticmethod
    def extract_text(file_path: str, filename: str) -> Dict[str, Any]:
        ext = os.path.splitext(filename)[1].lower()
        content = ""
        page_count = 1
        pages_detail = []

        try:
            if ext == ".pdf" and pypdf:
                reader = pypdf.PdfReader(file_path)
                page_count = len(reader.pages)

                for idx, page in enumerate(reader.pages):
                    txt = page.extract_text() or ""
                    content += f"\n--- Page {idx + 1} ---\n" + txt

                    pages_detail.append({
                        "page": idx + 1,
                        "text": txt
                    })

            elif ext == ".docx" and docx:
                doc = docx.Document(file_path)

                paras = [
                    p.text
                    for p in doc.paragraphs
                    if p.text.strip()
                ]

                content = "\n\n".join(paras)

                pages_detail.append({
                    "page": 1,
                    "text": content
                })

            else:
                # Text, MD, Python, JSON, etc.
                with open(
                    file_path,
                    "r",
                    encoding="utf-8",
                    errors="ignore"
                ) as f:
                    content = f.read()

                pages_detail.append({
                    "page": 1,
                    "text": content
                })

        except Exception as e:
            content = f"Error reading document: {str(e)}"

            pages_detail.append({
                "page": 1,
                "text": content
            })

        return {
            "id": str(uuid.uuid4())[:8],
            "filename": filename,
            "ext": ext,
            "content": content,
            "char_count": len(content),
            "word_count": len(content.split()),
            "page_count": page_count,
            "pages": pages_detail
        }


class TextChunker:
    """Splits text into overlapping semantic chunks for vector indexing."""

    def __init__(
        self,
        chunk_size: int = 400,
        overlap: int = 80
    ):
        self.chunk_size = chunk_size
        self.overlap = overlap

    def create_chunks(
        self,
        doc_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:

        text = doc_data["content"]
        filename = doc_data["filename"]
        doc_id = doc_data["id"]

        paragraphs = re.split(
            r'\n\s*\n',
            text
        )

        chunks = []
        current_chunk = ""
        chunk_idx = 0

        for para in paragraphs:
            para = para.strip()

            if not para:
                continue

            if (
                len(current_chunk)
                + len(para)
                <= self.chunk_size
            ):
                current_chunk += (
                    "\n"
                    if current_chunk
                    else ""
                ) + para

            else:
                if current_chunk:
                    chunks.append(
                        self._build_chunk_dict(
                            current_chunk,
                            doc_id,
                            filename,
                            chunk_idx
                        )
                    )

                    chunk_idx += 1

                # Keep overlap if possible
                if len(para) > self.chunk_size:

                    # Paragraph itself is larger than
                    # chunk size, split by sentences
                    sentences = re.split(
                        r'(?<=[.!?])\s+',
                        para
                    )

                    sub_chunk = ""

                    for s in sentences:
                        if (
                            len(sub_chunk)
                            + len(s)
                            <= self.chunk_size
                        ):
                            sub_chunk += (
                                " "
                                if sub_chunk
                                else ""
                            ) + s

                        else:
                            if sub_chunk:
                                chunks.append(
                                    self._build_chunk_dict(
                                        sub_chunk,
                                        doc_id,
                                        filename,
                                        chunk_idx
                                    )
                                )

                                chunk_idx += 1

                            sub_chunk = s

                    if sub_chunk:
                        current_chunk = sub_chunk
                    else:
                        current_chunk = ""

                else:
                    current_chunk = para

        if current_chunk.strip():
            chunks.append(
                self._build_chunk_dict(
                    current_chunk,
                    doc_id,
                    filename,
                    chunk_idx
                )
            )

        return chunks

    def _build_chunk_dict(
        self,
        text: str,
        doc_id: str,
        filename: str,
        idx: int
    ) -> Dict[str, Any]:

        # Estimate page number if page marker exists
        page_match = re.search(
            r'--- Page (\d+) ---',
            text
        )

        page_num = (
            int(page_match.group(1))
            if page_match
            else 1
        )

        clean_text = re.sub(
            r'--- Page \d+ ---',
            '',
            text
        ).strip()

        return {
            "chunk_id":
                f"{doc_id}_c{idx}",

            "doc_id":
                doc_id,

            "filename":
                filename,

            "chunk_index":
                idx,

            "page":
                page_num,

            "text":
                clean_text
                if clean_text
                else text,

            "word_count":
                len(text.split())
        }


class HybridVectorStore:
    """
    In-memory Vector Database using
    TF-IDF + Cosine Similarity with Dense Fallback.
    """

    def __init__(self):
        self.chunks: List[Dict[str, Any]] = []
        self.vectorizer = None
        self.tfidf_matrix = None

    def index_chunks(
        self,
        new_chunks: List[Dict[str, Any]]
    ):
        self.chunks.extend(new_chunks)
        self._rebuild_index()

    def clear_index(self):
        self.chunks = []
        self.vectorizer = None
        self.tfidf_matrix = None

    def delete_document(
        self,
        doc_id: str
    ):
        self.chunks = [
            c
            for c in self.chunks
            if c["doc_id"] != doc_id
        ]

        self._rebuild_index()

    def _rebuild_index(self):
        if not self.chunks:
            self.vectorizer = None
            self.tfidf_matrix = None
            return

        corpus = [
            c["text"]
            for c in self.chunks
        ]

        if TfidfVectorizer:
            self.vectorizer = TfidfVectorizer(
                ngram_range=(1, 2),
                stop_words="english",
                max_features=5000
            )

            try:
                self.tfidf_matrix = (
                    self.vectorizer.fit_transform(
                        corpus
                    )
                )

            except Exception:
                self.tfidf_matrix = None

        else:
            self.tfidf_matrix = None

    def search(
        self,
        query: str,
        top_k: int = 4
    ) -> List[Dict[str, Any]]:

        if not self.chunks:
            return []

        if (
            self.vectorizer
            and self.tfidf_matrix is not None
        ):
            try:
                query_vec = (
                    self.vectorizer.transform(
                        [query]
                    )
                )

                scores = cosine_similarity(
                    query_vec,
                    self.tfidf_matrix
                )[0]

                # Rank chunks by score
                ranked_indices = (
                    np.argsort(scores)[::-1]
                )

                results = []

                for idx in ranked_indices[:top_k]:
                    score = float(
                        scores[idx]
                    )

                    if score > 0.01:
                        chunk_copy = dict(
                            self.chunks[idx]
                        )

                        chunk_copy[
                            "similarity_score"
                        ] = round(
                            score,
                            4
                        )

                        results.append(
                            chunk_copy
                        )

                if results:
                    return results

            except Exception as e:
                print(
                    f"TF-IDF search fallback: {e}"
                )

        # Simple Keyword & Jaccard overlap fallback
        query_words = set(
            re.findall(
                r'\w+',
                query.lower()
            )
        )

        scored_chunks = []

        for chunk in self.chunks:

            chunk_words = set(
                re.findall(
                    r'\w+',
                    chunk["text"].lower()
                )
            )

            intersection = (
                query_words.intersection(
                    chunk_words
                )
            )

            if intersection:

                jaccard = (
                    len(intersection)
                    /
                    float(
                        len(
                            query_words.union(
                                chunk_words
                            )
                        )
                    )
                )

                score = (
                    jaccard
                    *
                    (
                        len(intersection)
                        /
                        float(
                            len(query_words)
                        )
                    )
                )

                scored_chunks.append(
                    (
                        score,
                        chunk
                    )
                )

        scored_chunks.sort(
            key=lambda x: x[0],
            reverse=True
        )

        results = []

        for score, chunk in scored_chunks[:top_k]:

            chunk_copy = dict(
                chunk
            )

            chunk_copy[
                "similarity_score"
            ] = round(
                score,
                4
            )

            results.append(
                chunk_copy
            )

        return (
            results
            if results
            else [
                dict(
                    c,
                    similarity_score=0.1
                )
                for c in self.chunks[:top_k]
            ]
        )


class RAGEngine:
    """Core RAG & Study Assistant Logic."""

    def __init__(self):
        self.extractor = DocumentExtractor()

        self.chunker = TextChunker(
            chunk_size=450,
            overlap=80
        )

        self.vector_store = (
            HybridVectorStore()
        )

        self.documents: Dict[
            str,
            Dict[str, Any]
        ] = {}

        self.gemini_api_key: Optional[str] = (
            os.environ.get(
                "GEMINI_API_KEY",
                ""
            )
        )

    def set_api_key(
        self,
        api_key: str
    ):
        self.gemini_api_key = (
            api_key.strip()
        )

    def process_file(
        self,
        file_path: str,
        filename: str
    ) -> Dict[str, Any]:

        doc_info = (
            self.extractor.extract_text(
                file_path,
                filename
            )
        )

        doc_id = doc_info["id"]

        # Save in memory doc cache
        self.documents[doc_id] = (
            doc_info
        )

        # Chunk text
        chunks = (
            self.chunker.create_chunks(
                doc_info
            )
        )

        doc_info["chunk_count"] = (
            len(chunks)
        )

        # Index in Vector Database
        self.vector_store.index_chunks(
            chunks
        )

        return {
            "doc_id":
                doc_id,

            "filename":
                filename,

            "word_count":
                doc_info["word_count"],

            "page_count":
                doc_info["page_count"],

            "chunk_count":
                len(chunks),

            "status":
                "indexed"
        }

    def remove_document(
        self,
        doc_id: str
    ):
        if doc_id in self.documents:

            del self.documents[
                doc_id
            ]

            self.vector_store.delete_document(
                doc_id
            )

    def ask(
        self,
        query: str,
        doc_filter: Optional[str] = None
    ) -> Dict[str, Any]:

        # Search vector store for relevant chunks
        retrieved_chunks = (
            self.vector_store.search(
                query,
                top_k=4
            )
        )

        if doc_filter:
            retrieved_chunks = [
                c
                for c in retrieved_chunks
                if c["doc_id"] == doc_filter
            ]

        if not retrieved_chunks:
            return {
                "answer":
                    "I couldn't find any relevant "
                    "information in your uploaded "
                    "documents. Try uploading notes "
                    "or broadening your question!",

                "citations": [],

                "retrieved_count": 0
            }

        # Build context prompt
        context_str = "\n\n".join([
            (
                f"[Source: {c['filename']}, "
                f"Page {c['page']}]\n"
                f"{c['text']}"
            )
            for c in retrieved_chunks
        ])

        answer = self._generate_response(
            query,
            context_str,
            retrieved_chunks
        )

        citations = [
            {
                "chunk_id":
                    c["chunk_id"],

                "filename":
                    c["filename"],

                "page":
                    c["page"],

                "score":
                    c.get(
                        "similarity_score",
                        0.0
                    ),

                "snippet":
                    (
                        c["text"][:220]
                        + "..."
                        if len(c["text"]) > 220
                        else c["text"]
                    )
            }

            for c in retrieved_chunks
        ]

        return {
            "answer":
                answer,

            "citations":
                citations,

            "retrieved_count":
                len(retrieved_chunks)
        }

    # ======================================================================
    # NEW: CLEAN SOURCE TEXT
    # ======================================================================

    def _clean_source_text(
        self,
        text: str
    ) -> str:

        """
        Removes page markers, Markdown headings and
        unnecessary source formatting before creating
        the final answer.
        """

        # Remove page markers
        text = re.sub(
            r'---\s*Page\s*\d+\s*---',
            ' ',
            text,
            flags=re.IGNORECASE
        )

        # Remove Markdown heading markers
        text = re.sub(
            r'#+\s*',
            '',
            text
        )

        # Remove common study-note title patterns
        text = re.sub(
            r'High[- ]Performance\s+Retrieval[- ]Augmented\s+Generation\s*\(RAG\)\s*Study\s+Notes',
            '',
            text,
            flags=re.IGNORECASE
        )

        # Remove section headings such as:
        # Introduction to RAG
        # 1. Introduction to RAG
        text = re.sub(
            r'(?:^|\s)'
            r'(?:\d+\.\s*)?'
            r'Introduction\s+to\s+RAG'
            r'(?=\s|$)',
            ' ',
            text,
            flags=re.IGNORECASE
        )

        # Remove duplicate whitespace
        text = re.sub(
            r'\s+',
            ' ',
            text
        )

        return text.strip()

    # ======================================================================
    # NEW: EXTRACT CLEAN SENTENCES
    # ======================================================================

    def _get_clean_sentences(
        self,
        text: str
    ) -> List[str]:

        text = self._clean_source_text(
            text
        )

        if not text:
            return []

        sentences = re.split(
            r'(?<=[.!?])\s+',
            text
        )

        cleaned = []

        for sentence in sentences:

            sentence = sentence.strip()

            if not sentence:
                continue

            # Remove remaining heading-like fragments
            sentence = re.sub(
                r'^(?:\d+\.\s*)?'
                r'Introduction\s+to\s+RAG\s*',
                '',
                sentence,
                flags=re.IGNORECASE
            ).strip()

            # Remove separator characters
            sentence = re.sub(
                r'^[-_*#=]+\s*',
                '',
                sentence
            ).strip()

            if sentence:
                cleaned.append(
                    sentence
                )

        return cleaned

    # ======================================================================
    # NEW: DETECT DEFINITION QUESTIONS
    # ======================================================================

    def _is_definition_question(
        self,
        query: str
    ) -> bool:

        q = query.strip().lower()

        q = re.sub(
            r'[?!.]+$',
            '',
            q
        ).strip()

        patterns = [
            r'^what\s+is\s+.+$',
            r'^what\s+are\s+.+$',
            r'^what\s+does\s+.+\s+mean$',
            r'^define\s+.+$',
            r'^definition\s+of\s+.+$',
            r'^meaning\s+of\s+.+$'
        ]

        return any(
            re.match(
                pattern,
                q
            )
            for pattern in patterns
        )

    # ======================================================================
    # NEW: EXTRACT TERM FROM DEFINITION QUESTION
    # ======================================================================

    def _extract_question_term(
        self,
        query: str
    ) -> str:

        q = query.strip()

        patterns = [
            r'^what\s+is\s+(.+?)\??$',
            r'^what\s+are\s+(.+?)\??$',
            r'^what\s+does\s+(.+?)\s+mean\??$',
            r'^define\s+(.+?)\??$',
            r'^definition\s+of\s+(.+?)\??$',
            r'^meaning\s+of\s+(.+?)\??$'
        ]

        for pattern in patterns:

            match = re.match(
                pattern,
                q,
                flags=re.IGNORECASE
            )

            if match:
                return (
                    match.group(1)
                    .strip()
                    .strip("?")
                )

        return ""

    # ======================================================================
    # NEW: GET CLEAN DEFINITION
    # ======================================================================

    def _extract_clean_definition(
        self,
        query: str,
        chunks: List[Dict[str, Any]]
    ) -> Optional[str]:

        term = self._extract_question_term(
            query
        )

        if not term:
            return None

        # Escape the term safely
        escaped_term = re.escape(
            term
        )

        # Definition patterns
        definition_patterns = [
            rf'\b{escaped_term}\s*\([^)]*\)\s+is\s+(.+?)(?=\.\s|$)',
            rf'\b{escaped_term}\s+is\s+(.+?)(?=\.\s|$)',
            rf'\b{escaped_term}\s+refers\s+to\s+(.+?)(?=\.\s|$)',
            rf'\b{escaped_term}\s+means\s+(.+?)(?=\.\s|$)',
            rf'\b{escaped_term}\s+is\s+defined\s+as\s+(.+?)(?=\.\s|$)'
        ]

        candidates = []

        for chunk in chunks:

            clean_text = (
                self._clean_source_text(
                    chunk["text"]
                )
            )

            for pattern in definition_patterns:

                matches = re.findall(
                    pattern,
                    clean_text,
                    flags=re.IGNORECASE
                )

                for match in matches:

                    definition = (
                        match.strip()
                    )

                    if not definition:
                        continue

                    # Remove trailing junk
                    definition = re.sub(
                        r'\s+',
                        ' ',
                        definition
                    ).strip()

                    # If extraction stopped before
                    # punctuation, add it back.
                    if not definition.endswith(
                        "."
                    ):
                        definition += "."

                    candidates.append(
                        (
                            chunk.get(
                                "similarity_score",
                                0.0
                            ),
                            definition
                        )
                    )

        if not candidates:
            return None

        # Highest retrieval score first
        candidates.sort(
            key=lambda x: x[0],
            reverse=True
        )

        definition = candidates[0][1]

        # Avoid extremely long definitions
        if len(definition) > 500:

            definition = (
                definition[:500]
            )

            last_period = (
                definition.rfind(".")
            )

            if last_period > 150:
                definition = (
                    definition[
                        :last_period + 1
                    ]
                )

        # Build a polished answer
        clean_term = term.strip()

        # Preserve acronym form if source has it.
        if "(" not in clean_term:
            title = clean_term

        else:
            title = clean_term

        return (
            f"{title} is {definition}"
        )

    # ======================================================================
    # NEW: CLEAN GENERATED GEMINI ANSWER
    # ======================================================================

    def _clean_generated_answer(
        self,
        answer: str
    ) -> str:

        if not answer:
            return ""

        answer = answer.strip()

        # Remove code fences
        answer = re.sub(
            r'^```(?:markdown|md|text)?\s*',
            '',
            answer,
            flags=re.IGNORECASE
        )

        answer = re.sub(
            r'\s*```$',
            '',
            answer
        )

        # Remove assistant-generated title
        answer = re.sub(
            r'^#+\s*'
            r'(?:💡\s*)?'
            r"(?:Alexa['’]s\s+Study\s+Answer)"
            r'\s*:?\s*',
            '',
            answer,
            flags=re.IGNORECASE
        )

        # Remove "Introduction to RAG" if the model
        # accidentally repeats the heading.
        answer = re.sub(
            r'^(?:\d+\.\s*)?'
            r'Introduction\s+to\s+RAG\s*',
            '',
            answer,
            flags=re.IGNORECASE
        )

        # Remove raw source markers from the answer.
        # Citations are handled separately by ask().
        answer = re.sub(
            r'\[Source:[^\]]+\]',
            '',
            answer,
            flags=re.IGNORECASE
        )

        # Remove source footer if Gemini generates one.
        answer = re.split(
            r'\n\s*(?:---+|'
            r'📌\s*)'
            r'(?:Sources?|Key Context Breakdown)',
            answer,
            maxsplit=1,
            flags=re.IGNORECASE
        )[0]

        # Remove excessive Markdown headings
        answer = re.sub(
            r'^#+\s*',
            '',
            answer,
            flags=re.MULTILINE
        )

        # Remove excessive blank lines
        answer = re.sub(
            r'\n{3,}',
            '\n\n',
            answer
        )

        # Remove excessive spaces
        answer = re.sub(
            r'[ \t]{2,}',
            ' ',
            answer
        )

        return answer.strip()

    # ======================================================================
    # UPDATED RESPONSE GENERATION
    # ======================================================================

    def _generate_response(
        self,
        query: str,
        context: str,
        chunks: List[Dict[str, Any]]
    ) -> str:

        # ==============================================================
        # 1. GEMINI RESPONSE
        # ==============================================================

        if self.gemini_api_key:

            try:
                import requests

                url = (
                    "https://generativelanguage.googleapis.com/"
                    "v1beta/models/gemini-2.5-flash:"
                    "generateContent"
                    f"?key={self.gemini_api_key}"
                )

                prompt = (
                    "You are Alexa, an AI-powered study "
                    "assistant.\n\n"

                    "Answer the student's question using "
                    "ONLY the provided study context.\n\n"

                    "IMPORTANT RESPONSE RULES:\n"
                    "1. Give a direct and concise answer.\n"
                    "2. Do not repeat the question.\n"
                    "3. Do not reproduce the raw source text.\n"
                    "4. Do not include document titles "
                    "or section headings unless they are "
                    "necessary to answer the question.\n"
                    "5. Do not include citations or a "
                    "Sources section in the answer. "
                    "The application displays citations "
                    "separately.\n"
                    "6. Do not write 'Alexa's Study Answer'.\n"
                    "7. Do not add a Key Context Breakdown.\n"
                    "8. For 'What is X?' questions, give "
                    "a clear 1-3 sentence definition.\n"
                    "9. Do not add information that is not "
                    "supported by the context.\n"
                    "10. Keep the answer natural and easy "
                    "for a student to understand.\n\n"

                    f"STUDY CONTEXT:\n{context}\n\n"
                    f"STUDENT QUESTION:\n{query}\n\n"
                    "FINAL ANSWER:"
                )

                headers = {
                    "Content-Type":
                        "application/json"
                }

                payload = {
                    "contents": [
                        {
                            "parts": [
                                {
                                    "text":
                                        prompt
                                }
                            ]
                        }
                    ],

                    "generationConfig": {
                        "temperature": 0.2,
                        "maxOutputTokens": 250
                    }
                }

                resp = requests.post(
                    url,
                    headers=headers,
                    json=payload,
                    timeout=12
                )

                if resp.status_code == 200:

                    res_json = (
                        resp.json()
                    )

                    candidates = (
                        res_json.get(
                            "candidates",
                            []
                        )
                    )

                    if candidates:

                        parts = (
                            candidates[0]
                            .get(
                                "content",
                                {}
                            )
                            .get(
                                "parts",
                                []
                            )
                        )

                        if parts:

                            generated = (
                                parts[0]
                                .get(
                                    "text",
                                    ""
                                )
                            )

                            generated = (
                                self._clean_generated_answer(
                                    generated
                                )
                            )

                            if generated:
                                return generated

            except Exception as e:
                print(
                    f"Gemini API request error: {e}"
                )

        # ==============================================================
        # 2. SMART OFFLINE RESPONSE
        # ==============================================================

        # For definition questions, extract only the
        # actual definition instead of returning the
        # complete retrieved chunk.
        if self._is_definition_question(
            query
        ):

            clean_definition = (
                self._extract_clean_definition(
                    query,
                    chunks
                )
            )

            if clean_definition:

                return clean_definition

        # ==============================================================
        # 3. GENERAL QUESTION FALLBACK
        # ==============================================================

        all_sentences = []

        for chunk in chunks:

            sentences = (
                self._get_clean_sentences(
                    chunk["text"]
                )
            )

            for sentence in sentences:

                all_sentences.append(
                    (
                        chunk.get(
                            "similarity_score",
                            0.0
                        ),
                        sentence
                    )
                )

        # Score sentences based on query relevance
        q_words = set(
            re.findall(
                r'\w+',
                query.lower()
            )
        )

        # Remove generic question words
        q_words -= {
            "what",
            "is",
            "are",
            "the",
            "a",
            "an",
            "how",
            "why",
            "when",
            "where",
            "which",
            "who",
            "does",
            "do",
            "can",
            "could",
            "would",
            "should",
            "tell",
            "me",
            "about",
            "explain"
        }

        scored_sentences = []

        for vector_score, sentence in all_sentences:

            sentence_words = set(
                re.findall(
                    r'\w+',
                    sentence.lower()
                )
            )

            overlap = (
                q_words.intersection(
                    sentence_words
                )
            )

            relevance = len(
                overlap
            )

            score = (
                relevance
                + vector_score * 2
            )

            if score > 0:
                scored_sentences.append(
                    (
                        score,
                        sentence
                    )
                )

        scored_sentences.sort(
            key=lambda x: x[0],
            reverse=True
        )

        selected = []
        seen = set()

        for _, sentence in scored_sentences:

            normalized = (
                sentence.lower().strip()
            )

            if normalized in seen:
                continue

            seen.add(
                normalized
            )

            selected.append(
                sentence
            )

            if len(selected) >= 3:
                break

        # Final fallback
        if not selected:

            for _, sentence in all_sentences[:3]:

                if sentence not in selected:
                    selected.append(
                        sentence
                    )

        answer = " ".join(
            selected
        ).strip()

        # Keep general answers concise
        if len(answer) > 700:

            answer = answer[:700]

            last_period = (
                answer.rfind(".")
            )

            if last_period > 200:

                answer = (
                    answer[
                        :last_period + 1
                    ]
                )

        return answer

    def generate_summary(
        self,
        doc_id: Optional[str] = None
    ) -> Dict[str, Any]:

        target_texts = []
        doc_names = []

        if (
            doc_id
            and doc_id in self.documents
        ):

            target_texts.append(
                self.documents[
                    doc_id
                ]["content"]
            )

            doc_names.append(
                self.documents[
                    doc_id
                ]["filename"]
            )

        else:

            for d in self.documents.values():

                target_texts.append(
                    d["content"]
                )

                doc_names.append(
                    d["filename"]
                )

        if not target_texts:

            return {
                "summary":
                    "No documents uploaded yet "
                    "to summarize.",

                "key_takeaways":
                    []
            }

        full_text = "\n".join(
            target_texts
        )

        paras = [
            p.strip()
            for p in full_text.split(
                "\n"
            )
            if len(p.strip()) > 30
        ]

        # Select key paragraphs for executive summary
        summary_paras = (
            paras[:3]
            if paras
            else
            [
                "No substantial text found."
            ]
        )

        executive_summary = (
            "\n\n".join(
                summary_paras[:2]
            )
        )

        # Extract key bullet points
        takeaways = []

        for p in paras[2:8]:

            sents = re.split(
                r'(?<=[.!?])\s+',
                p
            )

            if (
                sents
                and len(sents[0]) > 20
            ):
                takeaways.append(
                    sents[0]
                )

        if not takeaways:

            takeaways = [
                "Extracted core concepts "
                "from study documents.",

                "Review document flashcards "
                "for active recall."
            ]

        return {
            "documents":
                doc_names,

            "executive_summary":
                executive_summary,

            "key_takeaways":
                takeaways[:5]
        }

    def generate_flashcards(
        self,
        count: int = 6
    ) -> List[Dict[str, str]]:

        if not self.documents:

            return [
                {
                    "question":
                        "What is Retrieval-Augmented "
                        "Generation (RAG)?",

                    "answer":
                        "RAG is an AI technique that "
                        "combines vector document "
                        "retrieval with generative "
                        "LLMs to provide accurate, "
                        "grounded answers."
                },

                {
                    "question":
                        "Why is vector embedding "
                        "essential for study assistants?",

                    "answer":
                        "Embeddings turn text into "
                        "mathematical vectors, allowing "
                        "instant semantic searching "
                        "based on meaning rather than "
                        "exact keywords."
                }
            ]

        cards = []

        full_text = "\n".join(
            [
                d["content"]
                for d in self.documents.values()
            ]
        )

        # Regex search for definitions and key patterns
        patterns = [
            r'([A-Z][A-Za-z0-9\s]{3,30})\s+'
            r'(?:is|are|refers to|is defined as|means)\s+'
            r'([^.!\n]{15,120}[.!])',

            r'([A-Z][A-Za-z0-9\s]{3,30}):\s+'
            r'([^.!\n]{15,120}[.!])'
        ]

        for pat in patterns:

            matches = re.findall(
                pat,
                full_text
            )

            for term, defn in matches:

                term = term.strip()
                defn = defn.strip()

                if (
                    len(term) < 40
                    and len(defn) > 15
                ):

                    cards.append({
                        "question":
                            f"What is **{term}**?",

                        "answer":
                            defn
                    })

        # Fallback if few cards found
        if len(cards) < count:

            paras = [
                p.strip()
                for p in full_text.split(
                    "\n"
                )
                if len(p.strip()) > 50
            ]

            for idx, p in enumerate(
                paras[
                    :count - len(cards)
                ]
            ):

                sents = re.split(
                    r'(?<=[.!?])\s+',
                    p
                )

                if len(sents) >= 2:

                    cards.append({
                        "question":
                            (
                                f"Key concept in "
                                f"section {idx + 1}: "
                                f"{sents[0][:60]}...?"
                            ),

                        "answer":
                            " ".join(
                                sents[1:3]
                            )
                    })

        return cards[:count]

    def generate_quiz(
        self,
        count: int = 4
    ) -> List[Dict[str, Any]]:

        flashcards = (
            self.generate_flashcards(
                count=count * 2
            )
        )

        quizzes = []

        distractor_pool = [
            "A static database storage mechanism without vector searching.",
            "An outdated machine learning classification model.",
            "A hardware component used to accelerate GPU matrix operations.",
            "A standard HTTP request status protocol.",
            "An algorithm designed purely for image compression."
        ]

        for idx, card in enumerate(
            flashcards[:count]
        ):

            correct_ans = (
                card["answer"]
            )

            opts = [
                correct_ans
            ]

            # Add distractors
            other_answers = [
                c["answer"]
                for i, c
                in enumerate(flashcards)
                if i != idx
            ]

            if other_answers:
                opts.append(
                    other_answers[0]
                )

            opts.extend(
                distractor_pool[
                    :4 - len(opts)
                ]
            )

            # Shuffle options deterministically for UI
            np.random.seed(
                idx + 42
            )

            np.random.shuffle(
                opts
            )

            quizzes.append({
                "id":
                    idx + 1,

                "question":
                    card["question"],

                "options":
                    opts,

                "correct":
                    opts.index(
                        correct_ans
                    ),

                "explanation":
                    f"Correct! {correct_ans}"
            })

        return quizzes

    def get_key_concepts(
        self
    ) -> List[Dict[str, Any]]:

        if not self.documents:

            return [
                {
                    "name":
                        "Retrieval-Augmented Generation",

                    "frequency":
                        12,

                    "category":
                        "AI Core"
                },

                {
                    "name":
                        "Vector Embeddings",

                    "frequency":
                        9,

                    "category":
                        "NLP"
                },

                {
                    "name":
                        "Cosine Similarity",

                    "frequency":
                        7,

                    "category":
                        "Math"
                },

                {
                    "name":
                        "Semantic Chunking",

                    "frequency":
                        5,

                    "category":
                        "Data Prep"
                }
            ]

        full_text = "\n".join(
            [
                d["content"]
                for d in self.documents.values()
            ]
        )

        words = re.findall(
            r'\b[A-Z][a-z]{3,}\b',
            full_text
        )

        freqs: Dict[str, int] = {}

        for w in words:

            if w.lower() not in {
                "this",
                "that",
                "with",
                "from",
                "have",
                "they",
                "were",
                "what",
                "when",
                "where",
                "page"
            }:

                freqs[w] = (
                    freqs.get(
                        w,
                        0
                    )
                    + 1
                )

        sorted_freqs = sorted(
            freqs.items(),
            key=lambda x: x[1],
            reverse=True
        )[:8]

        categories = [
            "Concept",
            "Definition",
            "Key Metric",
            "Topic",
            "Formula"
        ]

        return [
            {
                "name":
                    name,

                "frequency":
                    count,

                "category":
                    categories[
                        i % len(categories)
                    ]
            }

            for i, (
                name,
                count
            ) in enumerate(
                sorted_freqs
            )
        ]