"""
STEG 1 - Vektorisering och lagring i ChromaDB
=============================================
Detta skript:
1. Läser in alla JSON-filer från er mapp
2. Extraherar varje chunk med sin kontext
3. Omvandlar texten till vektorer via en flerspråkig embedding-modell
4. Lagrar allt i en lokal ChromaDB-databas

ANVÄNDNING:
    Kör skriptet: python steg1_vektorisering.py
"""

import json
import os
from pathlib import Path

# ============================================================
# KONFIGURATION
# ============================================================

# Sökväg till mappen med era JSON-filer
JSON_MAPP = "./data"

# Namn på ChromaDB-samlingen
SAMLING_NAMN = "hamlet_arkiv"

# Sökväg där ChromaDB-databasen sparas lokalt
DB_SÖKVÄG = "./hamlet_chroma_db"

# ============================================================
# SKRIPT
# ============================================================

def las_json_filer(mapp: str) -> list:
    """Läser in alla JSON-filer och returnerar en lista med chunks."""
    alla_chunks = []
    json_filer = list(Path(mapp).glob("*.json"))
    
    print(f"Hittade {len(json_filer)} JSON-filer")
    
    for fil in json_filer:
        with open(fil, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        dokument_id = data.get("dokument_id", fil.stem)
        chunks = data.get("chunks", [])
        
        for chunk in chunks:
            chunk_id = chunk.get("chunk_id", "")
            text = chunk.get("text", "")
            kontext = chunk.get("kontext", {})
            
            if not text.strip():
                continue
            
            publikation = kontext.get("publikation", "")
            datum = kontext.get("datum", "")
            rubrik = kontext.get("rubrik", "")
            
            forbattrad_text = f"{rubrik}. {publikation} {datum}. {text}"
            
            alla_chunks.append({
                "chunk_id": chunk_id,
                "text": text,
                "forbattrad_text": forbattrad_text,
                "dokument_id": dokument_id,
                "metadata": {
                    "publikation": kontext.get("publikation", ""),
                    "datum": kontext.get("datum", ""),
                    "pjas": kontext.get("pjäs", "Hamlet"),
                    "regissör": kontext.get("regissör", "Ingmar Bergman"),
                    "dokumenttyp": kontext.get("dokumenttyp", ""),
                    "rubrik": kontext.get("rubrik", ""),
                    "plats": kontext.get("plats", ""),
                    "recensent": kontext.get("recensent", ""),
                    "journalist": kontext.get("journalist", ""),
                    "dokument_id": dokument_id,
                }
            })
    
    print(f"Totalt {len(alla_chunks)} chunks inlasta")
    return alla_chunks


def lagra_i_chromadb(chunks: list, db_sokväg: str, samling_namn: str):
    """Vektoriserar chunks och lagrar dem i ChromaDB."""
    import chromadb
    from sentence_transformers import SentenceTransformer
    
    print("Laddar embedding-modell (paraphrase-multilingual-mpnet-base-v2)...")
    modell = SentenceTransformer("paraphrase-multilingual-mpnet-base-v2")
    
    print(f"Skapar ChromaDB-databas i {db_sokväg}...")
    klient = chromadb.PersistentClient(path=db_sokväg)
    
    try:
        klient.delete_collection(samling_namn)
        print(f"Tog bort gammal samling '{samling_namn}'")
    except Exception:
        pass
    
    samling = klient.create_collection(
        name=samling_namn,
        metadata={"hnsw:space": "cosine"}
    )
    
    batch_storlek = 50
    totalt = len(chunks)
    
    for i in range(0, totalt, batch_storlek):
        batch = chunks[i:i + batch_storlek]
        
        texter = [c["forbattrad_text"] for c in batch]
        ids = [c["chunk_id"] for c in batch]
        metadata = [c["metadata"] for c in batch]
        original_texter = [c["text"] for c in batch]
        
        vektorer = modell.encode(texter).tolist()
        
        samling.add(
            embeddings=vektorer,
            documents=original_texter,
            metadatas=metadata,
            ids=ids
        )
        
        print(f"  Lagrat {min(i + batch_storlek, totalt)}/{totalt} chunks...")
    
    print(f"\nKlart! {totalt} chunks lagrade i ChromaDB.")
    print(f"Databas sparad i: {db_sokväg}")
    return samling


def testa_sokning(db_sokväg: str, samling_namn: str):
    """Kör ett enkelt söktest för att verifiera att allt fungerar."""
    import chromadb
    from sentence_transformers import SentenceTransformer
    
    print("\n--- SOKTEST ---")
    modell = SentenceTransformer("paraphrase-multilingual-mpnet-base-v2")
    klient = chromadb.PersistentClient(path=db_sokväg)
    samling = klient.get_collection(samling_namn)
    
    testfraga = "Vad tyckte kritikerna om Peter Stormare som Hamlet?"
    print(f"Testfraga: {testfraga}")
    
    fraga_vektor = modell.encode([testfraga]).tolist()
    
    resultat = samling.query(
        query_embeddings=fraga_vektor,
        n_results=3
    )
    
    print("\nTopp 3 traffar:")
    for j, (doc, meta) in enumerate(zip(
        resultat["documents"][0],
        resultat["metadatas"][0]
    )):
        print(f"\n[{j+1}] {meta['publikation']} ({meta['datum']})")
        print(f"    Rubrik: {meta['rubrik']}")
        print(f"    Text: {doc[:200]}...")


# ============================================================
# KOR SKRIPTET
# ============================================================

if __name__ == "__main__":
    chunks = las_json_filer(JSON_MAPP)
    
    if not chunks:
        print("Inga chunks hittades! Kontrollera sökvägen till JSON-mappen.")
        exit(1)
    
    lagra_i_chromadb(chunks, DB_SÖKVÄG, SAMLING_NAMN)
    
    testa_sokning(DB_SÖKVÄG, SAMLING_NAMN)