"""
STEG2_VALIDERING - Kvalitetsvalidering av JSON-filer i hamlet_rag/data
========================================================================
Går igenom alla JSON-filer och genererar en rapport över datakvaliteten.

ANVÄNDNING:
    python3 steg2_validering.py

KRAV:
    Python 3.9+
    JSON-filer i ./data/

RAPPORT INNEHÅLLER:
    - Totalt antal filer och chunks
    - Andel ofullständiga chunks
    - Saknade obligatoriska fält
    - Misstänkt korta chunks
    - [oläsligt]-markeringar
    - Dubbletter (via notering-fältet)
    - Sammanfattning per publikation
"""

import json
import os
from pathlib import Path
from collections import defaultdict

# ─── Konfiguration ─────────────────────────────────────────────────────────────

DATA_MAPP = "./data"
OBLIGATORISKA_FÄLT = ["publikation", "datum", "pjäs", "dokumenttyp", "rubrik"]
MIN_TEXT_LÄNGD = 80

# ─── Hjälpfunktioner ───────────────────────────────────────────────────────────

def läs_json(filepath: Path):
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        return None


def kontrollera_chunk(chunk: dict) -> dict:
    """Returnerar en dict med alla kvalitetsproblem för ett chunk."""
    problem = []
    kontext = chunk.get("kontext", {})
    text = chunk.get("text", "")

    # Saknade obligatoriska fält
    saknade = [fält for fält in OBLIGATORISKA_FÄLT if not kontext.get(fält)]
    if saknade:
        problem.append(f"Saknar fält: {', '.join(saknade)}")

    # Ofullständig status
    if kontext.get("status") == "ofullständig":
        problem.append("status: ofullständig")

    # För kort text
    if len(text.strip()) < MIN_TEXT_LÄNGD:
        problem.append(f"Kort text ({len(text.strip())} tecken)")

    # Oläsligt-markeringar
    antal_oläsligt = text.lower().count("[oläsligt]")
    if antal_oläsligt > 0:
        problem.append(f"[oläsligt] x{antal_oläsligt}")

    # Misstänkta OCR-tecken
    ocr_tecken = [c for c in ["□", "■", "▪", "ï", "ü", "â"] if c in text]
    if ocr_tecken:
        problem.append(f"OCR-tecken: {''.join(ocr_tecken)}")

    # Ovanligt långa ord (hopslagna OCR-fel)
    långa_ord = [w for w in text.split() if len(w) > 25]
    if len(långa_ord) > 2:
        problem.append(f"Långa ord: {len(långa_ord)} st")

    # Är en dubblett
    notering = kontext.get("notering", "")
    är_dubblett = "kopia av" in notering.lower() or "samma artikel" in notering.lower()
    if är_dubblett:
        problem.append(f"Dubblett: {notering}")

    return {
        "chunk_id": chunk.get("chunk_id", "okänt"),
        "publikation": kontext.get("publikation", "okänd"),
        "datum": kontext.get("datum", "okänt"),
        "rubrik": kontext.get("rubrik", ""),
        "dokumenttyp": kontext.get("dokumenttyp", ""),
        "text_längd": len(text.strip()),
        "problem": problem,
        "är_dubblett": är_dubblett,
    }


# ─── Huvudlogik ────────────────────────────────────────────────────────────────

def validera_alla_filer(data_mapp: str) -> None:
    mapp = Path(data_mapp)
    json_filer = sorted(mapp.glob("*.json"))

    if not json_filer:
        print(f"Inga JSON-filer hittades i {data_mapp}")
        return

    # Räknare
    totalt_filer = 0
    fel_filer = []
    totalt_chunks = 0
    chunks_med_problem = []
    publikation_stats = defaultdict(lambda: {
        "chunks": 0,
        "ofullständiga": 0,
        "dubbletter": 0,
        "oläsligt": 0,
    })

    print("=" * 70)
    print("HAMLET RAG — DATAKVALITETSRAPPORT")
    print("=" * 70)
    print(f"Mapp: {mapp.resolve()}")
    print(f"Datum: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print()

    for filepath in json_filer:
        data = läs_json(filepath)
        if data is None:
            fel_filer.append(filepath.name)
            continue

        totalt_filer += 1
        chunks = data.get("chunks", [])

        for chunk in chunks:
            totalt_chunks += 1
            resultat = kontrollera_chunk(chunk)
            pub = resultat["publikation"]

            publikation_stats[pub]["chunks"] += 1

            if "status: ofullständig" in resultat["problem"]:
                publikation_stats[pub]["ofullständiga"] += 1

            if resultat["är_dubblett"]:
                publikation_stats[pub]["dubbletter"] += 1

            if any("[oläsligt]" in p for p in resultat["problem"]):
                publikation_stats[pub]["oläsligt"] += 1

            if resultat["problem"]:
                chunks_med_problem.append({**resultat, "fil": filepath.name})

    # ─── Sammanfattning ────────────────────────────────────────────────────────

    chunks_utan_problem = totalt_chunks - len(set(r["chunk_id"] for r in chunks_med_problem))
    ofullständiga = sum(1 for r in chunks_med_problem if "status: ofullständig" in r["problem"])
    dubbletter = sum(1 for r in chunks_med_problem if r["är_dubblett"])
    oläsligt = sum(1 for r in chunks_med_problem if any("[oläsligt]" in p for p in r["problem"]))
    korta = sum(1 for r in chunks_med_problem if any("Kort text" in p for p in r["problem"]))
    saknar_fält = sum(1 for r in chunks_med_problem if any("Saknar fält" in p for p in r["problem"]))

    print("─── ÖVERSIKT " + "─" * 57)
    print(f"  Filer analyserade:        {totalt_filer}")
    print(f"  Filer med läsfel:         {len(fel_filer)}")
    print(f"  Chunks totalt:            {totalt_chunks}")
    print(f"  Chunks utan problem:      {chunks_utan_problem} ({round(chunks_utan_problem/totalt_chunks*100, 1) if totalt_chunks else 0}%)")
    print(f"  Chunks med problem:       {len(set(r['chunk_id'] for r in chunks_med_problem))}")
    print()
    print("─── PROBLEMTYPER " + "─" * 53)
    print(f"  Status 'ofullständig':    {ofullständiga} chunks")
    print(f"  Dubbletter:               {dubbletter} chunks")
    print(f"  [oläsligt]-markeringar:   {oläsligt} chunks")
    print(f"  Korta chunks (<80 t):     {korta} chunks")
    print(f"  Saknar obligatoriska fält:{saknar_fält} chunks")
    print()

    if fel_filer:
        print("─── FILER MED LÄSFEL " + "─" * 49)
        for f in fel_filer:
            print(f"  ⚠  {f}")
        print()

    # ─── Per publikation ───────────────────────────────────────────────────────

    print("─── PER PUBLIKATION " + "─" * 50)
    print(f"  {'Publikation':<30} {'Chunks':>6} {'Ofullst.':>8} {'Dubl.':>6} {'Oläsl.':>7}")
    print("  " + "─" * 60)
    for pub, stats in sorted(publikation_stats.items()):
        print(f"  {pub:<30} {stats['chunks']:>6} {stats['ofullständiga']:>8} "
              f"{stats['dubbletter']:>6} {stats['oläsligt']:>7}")
    print()

    # ─── Detaljlista: chunks med problem ──────────────────────────────────────

    print("─── DETALJLISTA: CHUNKS MED PROBLEM " + "─" * 34)
    unika = {r["chunk_id"]: r for r in chunks_med_problem}
    for chunk_id, r in sorted(unika.items()):
        print(f"\n  [{r['fil']}]")
        print(f"  Chunk:  {chunk_id}")
        print(f"  Rubrik: {r['rubrik'][:70]}")
        print(f"  Längd:  {r['text_längd']} tecken")
        for p in r["problem"]:
            print(f"  ⚠  {p}")

    print()
    print("=" * 70)
    print("RAPPORT KLAR")
    print("=" * 70)


# ─── Kör ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    validera_alla_filer(DATA_MAPP)