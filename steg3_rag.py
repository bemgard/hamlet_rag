"""
STEG3_RAG - RAG-sökning med Gemma 2B via Ollama
=================================================
Hämtar relevanta chunks från ChromaDB och genererar
svar via Gemma 2B lokalt. Inkluderar deduplicering
så att samma publikation/datum inte dominerar svaret.

ANVÄNDNING:
    python3 steg3_rag.py

KRAV:
    pip install chromadb sentence-transformers requests
    Ollama igång med gemma 2:b
"""

import requests
import chromadb
from sentence_transformers import SentenceTransformer

DB_SOKVÄG = "./hamlet_chroma_db"
SAMLING_NAMN = "hamlet_arkiv"
OLLAMA_URL = "http://localhost:11434/api/generate"
MODELL = "gemma2:2b"
ANTAL_CHUNKS = 5
HÄMTA_KANDIDATER = 15

print("Laddar modell och databas...")
modell = SentenceTransformer("paraphrase-multilingual-mpnet-base-v2")
klient = chromadb.PersistentClient(path=DB_SOKVÄG)
samling = klient.get_collection(SAMLING_NAMN)
print(f"Klar! {samling.count()} chunks tillgängliga.")
print("-" * 60)


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
                "text": doc,
                "publikation": meta.get("publikation", "okänd"),
                "datum": meta.get("datum", "okänt"),
                "rubrik": meta.get("rubrik", "")
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
    response = requests.post(OLLAMA_URL, json={
        "model": MODELL,
        "prompt": prompt,
        "stream": False
    })
    return response.json().get("response", "Inget svar mottaget.")


while True:
    fraga = input("\nFråga (eller 'avsluta'): ").strip()
    if fraga.lower() in ["avsluta", "exit", "quit"]:
        print("Avslutar...")
        break
    if not fraga:
        continue

    print("\nSöker i arkivet...")
    chunks = hämta_chunks(fraga)

    print("Genererar svar med Gemma 2B...")
    prompt = bygg_prompt(fraga, chunks)
    svar = fråga_gemma(prompt)

    print("\n" + "=" * 60)
    print("SVAR:")
    print(svar)
    print("\nKällor:")
    for i, chunk in enumerate(chunks, 1):
        print(f"  [{i}] {chunk['publikation']} ({chunk['datum']}) — {chunk['rubrik']}")
    print("=" * 60)