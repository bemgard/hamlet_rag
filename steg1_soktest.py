"""
SOKTEST - Interaktiv sokning i ChromaDB
========================================
Kör skriptet och skriv in egna frågor för att testa träffsäkerheten.
Skriv 'avsluta' för att stänga programmet.

KOMMANDON:
    avsluta         Stänger programmet
    läge            Växlar mellan normalt läge och transkriberings-testläge
    hjälp           Visar tillgängliga kommandon

LÄGEN:
    Normalt läge    Rankad sökning med scoring och deduplicering
    Testläge        Visar råtext utan scoring – används för att utvärdera transkriberingskvalitet

ANVÄNDNING:
    python3 steg1_soktest.py

KRAV:
    Python 3.9+
    pip install chromadb sentence-transformers
"""

import chromadb
from sentence_transformers import SentenceTransformer
from datetime import datetime
from typing import Optional, Tuple, List, Dict

DB_SOKVÄG = "./hamlet_chroma_db"
SAMLING_NAMN = "hamlet_arkiv"

ANTAL_TRÄFFAR = 10
ANTAL_ATT_VISA = 3

# Datumfönster per plats
DATUMFÖNSTER = {
    "none":     (datetime(1986, 12, 20), datetime(1987, 1, 15)),
    "london":   (datetime(1987, 6,  1),  datetime(1987, 6, 30)),
    "new_york": (datetime(1988, 1,  1),  datetime(1988, 3, 31)),
    "tokyo":    (datetime(1988, 6,  1),  datetime(1988, 8, 31)),
}


# ─── Klassificering ────────────────────────────────────────────────────────────

def classify_query(query: str) -> Tuple[str, Optional[str]]:
    q = query.lower()

    plats = None
    if "london" in q:
        plats = "london"
    elif any(word in q for word in ["new york", "broadway", "usa", "amerikanska"]):
        plats = "new_york"
    elif any(word in q for word in ["tokyo", "japan", "japanska"]):
        plats = "tokyo"

    if any(word in q for word in [
        "kritiker", "kritik", "recension", "recensioner",
        "tycker", "mest negativ", "mottagande", "tyckte"
    ]):
        return "kritik", plats

    if any(word in q for word in [
        "scenografi", "ljus", "kostym", "scenbild", "dekoration"
    ]):
        return "produktion", plats

    if any(word in q for word in [
        "ofelia", "karaktär", "personlighet", "rollfigur", "roll"
    ]):
        return "karaktär", plats

    if any(word in q for word in [
        "fotograf", "foto", "bild", "scenfoton", "scenfoto"
    ]):
        return "foto", plats

    return "default", plats


def parse_date_safe(date_str: str) -> Optional[datetime]:
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except Exception:
        return None


# ─── Scoring ───────────────────────────────────────────────────────────────────

def score_result(result: Dict, query_type: str, plats: Optional[str]) -> float:
    score = result.get("relevans", 0.0)
    meta = result.get("metadata", {})

    dokumenttyp = (meta.get("dokumenttyp") or "").lower()
    datum_str = meta.get("datum") or ""
    meta_plats = (meta.get("plats") or "").lower()
    text = (result.get("text") or "").lower()

    # 1. Dokumenttyp-viktning
    if query_type == "kritik":
        if dokumenttyp == "tidningsrecension":
            score += 20
        elif dokumenttyp in ["tidningsartikel", "notis"]:
            score -= 10
        elif dokumenttyp in ["bildtext", "faktaruta"]:
            score -= 20

    elif query_type == "produktion":
        if dokumenttyp == "tidningsrecension":
            score += 10
        elif dokumenttyp in ["bildtext", "faktaruta"]:
            score -= 10

    elif query_type == "karaktär":
        if dokumenttyp == "tidningsrecension":
            score += 10
        elif dokumenttyp in ["bildtext", "faktaruta", "notis"]:
            score -= 10

    elif query_type == "foto":
        if dokumenttyp == "programblad":
            score += 25
        elif dokumenttyp == "tidningsrecension":
            score -= 10

    # 2. Platsmatchning
    if plats is not None:
        platsord = {
            "london":   ["london"],
            "new_york": ["new york", "new-york", "broadway"],
            "tokyo":    ["tokyo", "japan"],
        }
        om_platsmatch = any(p in meta_plats for p in platsord.get(plats, []))
        if om_platsmatch:
            score += 15
        else:
            score -= 15 if query_type == "kritik" else 8

    # 3. Datumfönster
    if query_type == "kritik":
        d = parse_date_safe(datum_str)
        if d:
            fönster_nyckel = plats if plats is not None else "none"
            start, slut = DATUMFÖNSTER.get(fönster_nyckel, DATUMFÖNSTER["none"])
            if start <= d <= slut:
                score += 15
            else:
                score -= 12

    # 4. Straffa korta chunks
    if len(text) < 120:
        score -= 8

    return score


def deduplicate_by_document(results: List[Dict]) -> List[Dict]:
    seen = set()
    unique = []
    for result in results:
        chunk_id = result.get("chunk_id", "")
        dokument_id = chunk_id.split("_chunk-")[0] if "_chunk-" in chunk_id else chunk_id
        if dokument_id not in seen:
            seen.add(dokument_id)
            unique.append(result)
    return unique


def postprocess_results(results: List[Dict], query: str) -> List[Dict]:
    query_type, plats = classify_query(query)
    for result in results:
        result["adjusted_score"] = score_result(result, query_type, plats)
        result["query_type"] = query_type
        result["detected_plats"] = plats
    results = sorted(results, key=lambda x: x["adjusted_score"], reverse=True)
    results = deduplicate_by_document(results)
    return results


# ─── Utskrift: normalt läge ────────────────────────────────────────────────────

def skriv_normalt(träffar: List[Dict], fraga: str) -> None:
    if träffar:
        print(f"\n  [Debug] Typ: {träffar[0]['query_type']} | "
              f"Plats: {träffar[0]['detected_plats'] or 'ingen'}")

    print(f"\nTopp {len(träffar)} träffar för: '{fraga}'")
    print("-" * 60)

    for j, träff in enumerate(träffar, 1):
        meta = träff["metadata"]
        print(f"\n[{j}] {meta.get('publikation', 'Okänd')} ({meta.get('datum', 'okänt datum')})")
        print(f"    Rubrik:    {meta.get('rubrik', '')}")
        print(f"    Typ:       {meta.get('dokumenttyp', '')}")
        if meta.get("recensent"):
            print(f"    Recensent: {meta.get('recensent')}")
        if meta.get("plats"):
            print(f"    Plats:     {meta.get('plats')}")
        print(f"    Relevans:  {träff['relevans']}%")
        print(f"    Justerad:  {round(träff['adjusted_score'], 1)}")
        print(f"    Text:      {träff['text'][:500]}...")
        print()


# ─── Utskrift: transkriberings-testläge ───────────────────────────────────────

def skriv_testläge(träffar: List[Dict], fraga: str) -> None:
    print(f"\n[TESTLÄGE] Råtext för: '{fraga}'")
    print("=" * 60)
    print("OBS: Ingen scoring eller deduplicering. Bedöm textkvaliteten manuellt.")
    print("=" * 60)

    for j, träff in enumerate(träffar, 1):
        meta = träff["metadata"]
        text = träff.get("text", "")

        print(f"\n{'─' * 60}")
        print(f"[{j}] {meta.get('publikation', 'Okänd')} – {meta.get('datum', 'okänt datum')}")
        print(f"     Rubrik:  {meta.get('rubrik', '')}")
        print(f"     Typ:     {meta.get('dokumenttyp', '')}")
        print(f"     Chunk:   {träff.get('chunk_id', '')}")
        print(f"     Relevans (grund): {träff['relevans']}%")
        print()
        print("  RÅTEXT:")
        print("  " + text.replace("\n", "\n  "))
        print()

        # Automatisk kvalitetsbedömning
        varningar = []
        if len(text) < 80:
            varningar.append("⚠  Mycket kort chunk – kan vara ett transkriberingsproblem")
        if text.count("?") > 5:
            varningar.append("⚠  Många frågetecken – kan indikera OCR-fel på okända tecken")
        if any(c in text for c in ["□", "■", "▪", "ï", "ü", "â"]):
            varningar.append("⚠  Misstänkta specialtecken – troligt OCR-fel")
        if len([w for w in text.split() if len(w) > 25]) > 2:
            varningar.append("⚠  Ovanligt långa ord – kan vara hopslagna OCR-fel")

        if varningar:
            for v in varningar:
                print(f"  {v}")
        else:
            print("  ✓ Inga uppenbara kvalitetsproblem detekterade")
        print()


# ─── Uppstart ──────────────────────────────────────────────────────────────────

print("Laddar modell och databas...")
modell = SentenceTransformer("paraphrase-multilingual-mpnet-base-v2")
klient = chromadb.PersistentClient(path=DB_SOKVÄG)
samling = klient.get_collection(SAMLING_NAMN)

print(f"Databas laddad! {samling.count()} chunks tillgängliga.")
print("-" * 60)
print("Kommandon: 'läge' (växla testläge), 'hjälp', 'avsluta'")
print("-" * 60)

testläge = False

while True:
    läge_indikator = " [TESTLÄGE]" if testläge else ""
    fraga = input(f"\nFråga{läge_indikator}: ").strip()

    if fraga.lower() in ["avsluta", "exit", "quit"]:
        print("Avslutar...")
        break

    if fraga.lower() == "läge":
        testläge = not testläge
        status = "PÅ – visar råtext för transkriberingsutvärdering" if testläge else "AV – normalt sökläge"
        print(f"Testläge: {status}")
        continue

    if fraga.lower() == "hjälp":
        print("\nKommandon:")
        print("  läge      Växlar mellan normalt läge och transkriberings-testläge")
        print("  avsluta   Stänger programmet")
        print("\nI testläge visas:")
        print("  - Fullständig råtext per chunk (utan trunkering)")
        print("  - Chunk-ID för spårbarhet till JSON-fil")
        print("  - Automatiska varningar för möjliga OCR-fel")
        print("  - Ingen scoring eller deduplicering")
        continue

    if not fraga:
        continue

    fraga_vektor = modell.encode([fraga]).tolist()

    resultat = samling.query(
        query_embeddings=fraga_vektor,
        n_results=ANTAL_TRÄFFAR
    )

    träffar = []
    for chunk_id, doc, meta, distance in zip(
        resultat["ids"][0],
        resultat["documents"][0],
        resultat["metadatas"][0],
        resultat["distances"][0]
    ):
        relevans = round((1 - distance) * 100, 1)
        träffar.append({
            "chunk_id": chunk_id,
            "text": doc,
            "metadata": meta,
            "relevans": relevans
        })

    if testläge:
        skriv_testläge(träffar, fraga)
    else:
        träffar = postprocess_results(träffar, fraga)
        träffar = träffar[:ANTAL_ATT_VISA]
        skriv_normalt(träffar, fraga)