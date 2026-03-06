from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

class AskResponse(BaseModel):
    answer: str
    sources: list = []

@router.get("/test-ask", response_model=AskResponse)
def test_ask():
    # Tämä palauttaa demovastauksen, jossa on KaTeX/LaTeX -kaavoja
    return AskResponse(
        answer="Tässä on esimerkki laskentakaavojeni näyttämisestä:\n\nLämmitystarpeen kaava on $P = \\frac{m \\cdot c \\cdot \\Delta T}{t}$, missä $m$ on massa ja $\\Delta T$ on lämpötilaero.\n\nEsimerkkilaskun tulos on:\n$$ E = \\int_{0}^{t} P(t) dt \\approx 45.2 \\text{ kWh} $$"
    )
