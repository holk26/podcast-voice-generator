from fastapi import APIRouter
from web_api.services.llm_provider import check_ollama

router = APIRouter()


@router.get("/status")
def llm_status():
    return check_ollama()
