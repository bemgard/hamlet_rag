"""
API.PY - FastAPI-server för Dramaten RAG-system
================================================
Exponerar steg3_rag.py som ett HTTP-API så att
Dramatens webbsida kan ställa frågor till arkivet.

STARTA SERVERN:
    uvicorn api:app --reload --port 8000

TESTA I WEBBLÄSAREN:
    http://localhost:8000/docs   ← automatisk API-dokumentation

KRAV:
    pip install fastapi uvicorn
    Ollama igång med gemma2:2b
    ChromaDB redan indexerad (kör steg1_vektorisering.py först)
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests
import chromadb
from sentence_transformers import SentenceTransformer

# ── KONFIGURATION (samma som steg3_rag.py) ────────────────────────────────────

DB_SOKVÄG    = "./hamlet_chroma_db"
SAMLING_NAMN = "hamlet_arkiv"
OLLAMA_URL   = "http://localhost:11434/api/generate"
MODELL       = "gemma2:2b"
ANTAL_CHUNKS = 5
HÄMTA_KANDIDATER = 15

# ── LADDA MODELL OCH DATABAS VID UPPSTART ─────────────────────────────────────

print("Laddar embedding-modell...")
modell = SentenceTransformer("paraphrase-multilingual-mpnet-base-v2")

print("Ansluter till ChromaDB...")
klient = chromadb.PersistentClient(path=DB_SOKVÄG)
samling = klient.get_collection(SAMLING_NAMN)
print(f"Klar! {samling.count()} chunks tillgängliga.\n")

# ── FASTAPI-APP ───────────────────────────────────────────────────────────────

app = FastAPI(
    title="Dramaten Arkiv API",
    description="RAG-baserad sökning i Kungliga Dramatiska Teaterns historiska material.",
    version="1.0.0"
)

# CORS — tillåter anrop från Dramatens webbsida
# I produktion: byt ["*"] till ["https://www.dramaten.se"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── DATAMODELLER ──────────────────────────────────────────────────────────────

class FragaInput(BaseModel):
    fraga: str

class Kalla(BaseModel):
    publikation: str
    datum: str
    rubrik: str

class SvarOutput(BaseModel):
    svar: str
    kallor: list[Kalla]
    query: str
    modell: str
    ai_genererat: bool = True   # Transparenskrav enligt AI-förordningen

# ── HJÄLPFUNKTIONER (identiska med steg3_rag.py) ─────────────────────────────

def hämta_chunks(fraga: str) -> list:
    vektor = modell.encode([fraga]).tolist()
    resultat = samling.query(query_embeddings=vektor, n_results=HÄMTA_KANDIDATER)

    seen = set()
    chunks = []
    for doc, meta in zip(resultat["documents"][0], resultat["metadatas"][0]):
        dokument_id = meta.get("publikation", "") + meta.get("datum", "")
        if dokument_id not in seen:
            seen.add(dokument_id)
            chunks.append({
                "text":        doc,
                "publikation": meta.get("publikation", "okänd"),
                "datum":       meta.get("datum", "okänt"),
                "rubrik":      meta.get("rubrik", "")
            })
        if len(chunks) == ANTAL_CHUNKS:
            break
    return chunks


def bygg_prompt(fraga: str, chunks: list) -> str:
    kontext = ""
    for i, chunk in enumerate(chunks, 1):
        kontext += f"[Källa {i}: {chunk['publikation']}, {chunk['datum']}]\n"
        kontext += f"{chunk['text']}\n\n"

    return f"""Du är en hjälpsam assistent som svarar på frågor om Ingmar Bergmans uppsättning av Hamlet på Dramaten 1986.
Svara på svenska. Basera ditt svar enbart på de källor som anges nedan.
Om svaret inte finns i källorna, säg det tydligt.
Hitta inte på information som inte finns i källorna.

KÄLLOR:
{kontext}
FRÅGA: {fraga}

SVAR:"""


def fråga_gemma(prompt: str) -> str:
    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model":  MODELL,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.5}
            },
            timeout=120
        )
        response.raise_for_status()
        return response.json().get("response", "Inget svar mottaget.").strip()
    except requests.exceptions.ConnectionError:
        raise HTTPException(
            status_code=503,
            detail="Kan inte ansluta till Ollama. Kontrollera att 'ollama serve' körs."
        )
    except requests.exceptions.Timeout:
        raise HTTPException(
            status_code=504,
            detail="Modellen tog för lång tid att svara. Försök igen."
        )

# ── ENDPOINTS ─────────────────────────────────────────────────────────────────

@app.post("/fraga", response_model=SvarOutput)
async def stall_fraga(body: FragaInput):
    """
    Ställ en fråga om Dramatens Hamlet-uppsättning 1986.
    Returnerar ett AI-genererat svar med källhänvisningar.
    """
    if not body.fraga.strip():
        raise HTTPException(status_code=400, detail="Frågan får inte vara tom.")
    if len(body.fraga) > 1000:
        raise HTTPException(status_code=400, detail="Frågan är för lång (max 1000 tecken).")

    chunks = hämta_chunks(body.fraga)
    prompt = bygg_prompt(body.fraga, chunks)
    svar   = fråga_gemma(prompt)

    return SvarOutput(
        svar=svar,
        kallor=[Kalla(
            publikation=c["publikation"],
            datum=c["datum"],
            rubrik=c["rubrik"]
        ) for c in chunks],
        query=body.fraga,
        modell=MODELL,
        ai_genererat=True
    )


@app.get("/halsa")
async def halsa():
    """Kontrollerar att servern, databasen och Ollama fungerar."""
    # Testa Ollama
    try:
        requests.get("http://localhost:11434", timeout=3)
        ollama_status = "ok"
    except Exception:
        ollama_status = "ej nåbar — kör 'ollama serve'"

    return {
        "status":            "ok",
        "chunks_indexerade": samling.count(),
        "modell":            MODELL,
        "ollama":            ollama_status
    }


@app.get("/statistik")
async def statistik():
    """Visar fördelning av indexerat material per publikation."""
    alla = samling.get(include=["metadatas"])
    publikationer = {}
    for m in alla.get("metadatas", []):
        pub = m.get("publikation", "Okänd")
        publikationer[pub] = publikationer.get(pub, 0) + 1

    return {
        "totalt_chunks":      samling.count(),
        "antal_publikationer": len(publikationer),
        "publikationer":      dict(sorted(
            publikationer.items(), key=lambda x: x[1], reverse=True
        ))
    }


@app.get("/")
async def rot():
    return {
        "meddelande": "Dramaten Arkiv API — se /docs för dokumentation",
        "endpoints":  ["/fraga", "/halsa", "/statistik", "/docs"]
    }