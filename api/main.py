from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from rag.pipeline import ask

app = FastAPI(
    title="La Bibliothèque d'Alexandrie",
    description="Assistant qui répond à des questions à partir d'une documentation, en citant ses sources.",
)


# ---------- Ce qu'on reçoit ----------
class QuestionIn(BaseModel):
    question: str = Field(..., min_length=3, max_length=500, description="La question de l'étudiant")


# ---------- Ce qu'on renvoie ----------
class Source(BaseModel):
    num: int
    url: str
    page_title: str
    section: str


class AnswerOut(BaseModel):
    answer: str
    sources: list[Source]
    response_time: float
    is_idk: bool


# ---------- Les routes ----------
@app.get("/health")
def health():
    """Vérifie que l'API est en marche."""
    return {"status": "ok"}


@app.post("/question", response_model=AnswerOut)
def post_question(payload: QuestionIn):
    """Pose une question à l'assistant : renvoie la réponse, les sources et le temps de réponse."""
    try:
        result = ask(payload.question)
    except RuntimeError as error:  # par exemple : OpenAI saturé (erreur 429)
        raise HTTPException(status_code=503, detail=str(error))

    return AnswerOut(
        answer=result["answer"],
        sources=result["sources"],
        response_time=result["duration"],
        is_idk=result["is_idk"],
    )