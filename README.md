# Dramaten Arkivet — AI-driven sökning i teaterhistoria

> En RAG-baserad söklösning som tillgängliggör Kungliga Dramatiska Teaterns historiska arkivmaterial via ett AI-drivet chattgränssnitt.

![Dramaten Arkivet](https://img.shields.io/badge/Dramaten-Arkivet-8b5e1a?style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![React](https://img.shields.io/badge/React-18-61DAFB?style=for-the-badge&logo=react&logoColor=black)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?style=for-the-badge&logo=fastapi&logoColor=white)

---

## Om projektet

Detta projekt är ett examensarbete vid Stockholms universitet som undersöker hur digitalisering av arkivmaterial kan öka tillgängligheten till kulturarvsinstitutioners historiska samlingar.

Som fallstudie används **Ingmar Bergmans uppsättning av Hamlet på Dramaten 1986** — en av svensk teaterhistorias mest uppmärksammade produktioner. Materialet består av inskannade tidningsrecensioner och programblad som transkriberats, vektoriserats och gjorts sökbara via ett AI-drivet gränssnitt.

### Systemet i korthet

Användaren ställer en fråga i naturligt språk → systemet hämtar relevanta källtexter från ChromaDB → Gemma 2B genererar ett svar på svenska med källhänvisningar.

---

## Teknisk stack

| Komponent | Teknologi |
|-----------|-----------|
| Frontend | React 18 + Vite |
| Backend | FastAPI (Python) |
| Vektordatabas | ChromaDB |
| Embeddingmodell | `paraphrase-multilingual-mpnet-base-v2` |
| Språkmodell | Gemma 2B (Google, via Ollama) |
| Sökning | Semantisk RAG-sökning |

---

## Mappstruktur

```
HAMLET_RAG/
├── api.py                    # FastAPI-server, exponerar RAG som HTTP-API
├── steg1_vektorisering.py    # Transkriberar och indexerar källmaterial i ChromaDB
├── steg1_soktest.py          # Testar sökning i ChromaDB
├── steg2_validering.py       # Validerar indexerat material
├── steg3_rag.py              # RAG-sökning via terminalen
├── hamlet_chroma_db/         # Lokal vektordatabas (genereras av steg1)
├── data/                     # Källmaterial (transkriberade recensioner)
├── .venv/                    # Python virtual environment
└── frontend/                 # React-app
    ├── src/
    │   ├── DramatenArkiv.jsx # Huvudkomponent
    │   └── main.jsx
    ├── package.json
    └── vite.config.js
```

---

## Kom igång

### Krav

- Python 3.11+
- Node.js 18+
- [Ollama](https://ollama.com) installerat med Gemma 2B

### 1. Klona repot

```bash
git clone https://github.com/ditt-repo/hamlet-rag.git
cd hamlet-rag
```

### 2. Sätt upp Ollama och Gemma 2B

```bash
ollama pull gemma2:2b
ollama serve
```

### 3. Sätt upp backend

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install fastapi uvicorn chromadb sentence-transformers requests
```

Indexera källmaterialet (behöver bara göras en gång):

```bash
python steg1_vektorisering.py
```

Starta API-servern:

```bash
uvicorn api:app --reload --port 8000
```

### 4. Sätt upp frontend

```bash
cd frontend
npm install
npm run dev
```

Öppna [http://localhost:5173](http://localhost:5173) i webbläsaren.

---

## API-dokumentation

När servern körs finns automatisk dokumentation på:

```
http://localhost:8000/docs
```

### Endpoints

| Method | Endpoint | Beskrivning |
|--------|----------|-------------|
| `POST` | `/fraga` | Ställ en fråga till arkivet |
| `GET` | `/halsa` | Kontrollera serverstatus |
| `GET` | `/statistik` | Visa indexerat material per publikation |

### Exempelanrop

```bash
curl -X POST http://localhost:8000/fraga \
  -H "Content-Type: application/json" \
  -d '{"fraga": "Vad tyckte kritikerna om Peter Stormare?"}'
```

### Exempelsvar

```json
{
  "svar": "Kritikerna var blandade i sin bedömning av Peter Stormares tolkning av Hamlet...",
  "kallor": [
    {
      "publikation": "Aftonbladet",
      "datum": "1986-12-21",
      "rubrik": "Poff! Wham!"
    }
  ],
  "query": "Vad tyckte kritikerna om Peter Stormare?",
  "modell": "gemma2:2b",
  "ai_genererat": true
}
```

---

## Källmaterial

Systemet baseras på digitaliserade tidningsrecensioner från Dramatens fysiska arkiv. Materialet täcker:

- Svenska dagstidningar (Aftonbladet, Expressen, Svenska Dagbladet, Dagens Nyheter m.fl.)
- Regionala tidningar (Sydsvenska Dagbladet, Göteborgs-Posten m.fl.)
- Internationell press (The Times, Daily Telegraph, New York Daily News m.fl.)

---

## Transparens och AI-användning

Systemet klassificeras som **minimal risk** enligt EU:s AI-förordning. Alla svar är märkta som AI-genererade och baseras uteslutande på det indexerade källmaterialet — modellen instrueras explicit att inte hitta på information som saknas i källorna.

---

## Begränsningar

- Systemet svarar endast på frågor om Hamlet 1986
- Gemma 2B har begränsat stöd för svenska vilket kan ge ojämn språkkvalitet i svaren
- Svaren är beroende av kvaliteten på transkriberingarna
- Faktauppgifter bör verifieras mot originalkällorna

---

## Framtida utveckling

- [ ] Byta språkmodell till Claude Haiku eller GPT-4o-mini för bättre svenska
- [ ] Klickbara källdokument med inskannade originalsidor
- [ ] Utökad databas med fler Hamlet-uppsättningar
- [ ] Jämförande sökning mellan olika produktioner
- [ ] Integration med Dramatens rollbok
- [ ] Stöd för bildsökning i fotoarkivet

---

## Licens

Detta projekt är utvecklat som ett akademiskt examensarbete. Allt källmaterial tillhör Kungliga Dramatiska Teatern.
