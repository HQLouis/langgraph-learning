# Beat System Documentation

## Überblick

Das Beat-System ist eine Implementierung des "Closed-World Content Management" für storybasierte Dialogsysteme. Es stellt sicher, dass der Chatbot nur über Inhalte spricht, die tatsächlich in der Geschichte vorkommen.

## Kernkonzepte

### Was sind Beats?

Beats sind die **kleinste stabile inhaltliche Einheit** einer Geschichte innerhalb eines Kapitels. Sie erfüllen folgende Prinzipien:

- **Closed-World**: Nur Inhalte verwenden, die im Kapitel existieren
- **Scene-Integrity**: Keine Szenen vermischen
- **No-New-Facts**: Keine Details erfinden
- **Evidence**: Maschinenprüfbare Verweise für Regression ohne LLM-Judge

Ein Beat besteht typischerweise aus 1-3 Sätzen und beschreibt:
- Ein kleines Ereignis
- Ein Setting-Detail
- Einen kurzen Dialog-Austausch

### Warum Beats?

1. **Stabilität**: Konsistente Antworten basierend auf definierten Inhalten
2. **Prüfbarkeit**: Jede Antwort kann auf konkrete Beats zurückgeführt werden
3. **Token-Effizienz**: Nur relevante Beats werden als Kontext geladen
4. **Qualitätssicherung**: Verhindert Halluzinationen und inhaltliche Drift

## Architektur

### Datenmodell

```
BeatPack (pro Kapitel)
├── story_id: "mia_und_leo"
├── chapter_id: "chapter_01"
├── content_version: "2026-02-12T10:15:00Z"
├── beatpack_version: "v1"
├── chapter_hash: "sha256:..."
├── chapter_text: "Vollständiger Kapiteltext..."
├── beats: [Beat]
│   ├── beat_id: int (1, 2, 3, ...)
│   ├── order: int (sequenzielle Reihenfolge)
│   ├── span: {start_char, end_char}
│   ├── text: "Beat-Inhalt"
│   ├── entities: ["Mia", "Wald", ...]
│   ├── facts: [{s, p, o}, ...]
│   ├── tags: ["dialogue", "action", ...]
│   └── safety_tags: []
└── entity_registry: {Entity: EntityInfo}
    ├── "Mia": {aliases: ["sie", "das Mädchen"], type: "character"}
    └── "Leo": {aliases: ["der Fuchs", "er"], type: "character"}
```

### Verzeichnisstruktur

```
content/
└── stories/
    └── <story_id>/
        └── <chapter_id>/
            ├── chapter.txt              # Originaler Kapiteltext
            ├── beatpack.v1.json         # Haupt-Beatpack
            ├── beatpack.v1.index.json   # Suchindex (optional)
            └── beatpack.v1.meta.json    # Metadaten (optional)
```

## Komponenten

### 1. Beat Pipeline (`beat_pipeline.py`)

Die Pipeline erstellt BeatPacks aus Rohtext:

```python
from beat_pipeline import BeatPipeline, EntityInfo

# Pipeline initialisieren
pipeline = BeatPipeline(
    story_id="mia_und_leo",
    chapter_id="chapter_01",
    chapter_text=raw_text,
    min_beat_length=50,
    max_beat_length=300
)

# Entity Registry definieren
entity_registry = {
    "Mia": EntityInfo(
        aliases=["sie", "das Mädchen"],
        entity_type="character"
    )
}

# BeatPack erstellen
beatpack = pipeline.create_beatpack(entity_registry)
beatpack.save(output_path)
```

**Pipeline-Schritte:**

1. **Text Normalisierung**: Unicode, Whitespace, Anführungszeichen
2. **Kandidaten-Segmentierung**: 
   - Satzgrenzen erkennen
   - Sprecherwechsel identifizieren
   - Übergangswörter ("dann", "plötzlich") nutzen
3. **Entity Extraction**: Figuren, Orte, Objekte identifizieren
4. **Fact Extraction**: Strukturierte Facts (optional, 80/20 Prinzip)
5. **Index Building**: BM25-ähnlicher Suchindex
6. **Versioning & Hashing**: Integrität sicherstellen

### 2. Beat Runtime (`beats.py`)

Laufzeit-Komponenten für Beat-Retrieval:

```python
from beats import BeatPackManager, BeatRetriever

# Manager initialisieren
manager = BeatPackManager(content_dir=Path("content"))

# Retriever für spezifisches Kapitel
retriever = manager.get_retriever("mia_und_leo", "chapter_01")

# Beats abrufen (query-basiert)
beats = retriever.retrieve_beats("Wer ist Leo?", top_k=5)

# Beats für Tasks (chronologisch verteilt)
task_beats = retriever.get_beats_for_tasks(num_tasks=5)

# Als Kontext formatieren
context = retriever.format_beats_for_context(beats, include_entities=True)
```

**Retrieval-Strategien:**

1. **Query-basiert**: BM25-style Keyword-Matching für relevante Beats
2. **Task-basiert**: Chronologisch verteilte Beats für geplante Aufgaben
3. **Hybrid**: Kombination aus beiden (für zukünftige Erweiterung)

### 3. Integration in Dialogsystem (`nodes.py`, `immediate_graph.py`)

**State-Erweiterungen:**

```python
# states.py
class State(TypedDict):
    # ... bestehende Felder ...
    story_id: Optional[str]
    chapter_id: Optional[str]
    beat_context: Optional[str]
    active_beat_ids: Optional[list]
    num_planned_tasks: Optional[int]
```

**Beat Loading Node:**

```python
def load_beat_context(state: State) -> dict:
    """
    Lädt relevante Beats basierend auf Konversationsstatus.
    
    Strategie:
    - Erste Interaktion: Chronologisch verteilte Beats für Tasks
    - Folge-Interaktionen: Query-basierte Retrieval
    """
    retriever = beat_manager.get_retriever(
        state["story_id"], 
        state["chapter_id"]
    )
    
    if is_first_interaction:
        beats = retriever.get_beats_for_tasks(num_tasks=5)
    else:
        last_message = get_last_user_message(state)
        beats = retriever.retrieve_beats(last_message, top_k=5)
    
    return {
        "beat_context": format_beats(beats),
        "active_beat_ids": [b.beat_id for b in beats]
    }
```

**Graph-Integration:**

```
START → initialStateLoader → load_analysis → load_beat_context → masterChatbot → END
```

Der `load_beat_context` Node:
1. Prüft ob `story_id` und `chapter_id` gesetzt sind
2. Lädt BeatPack über `BeatPackManager`
3. Wählt relevante Beats basierend auf Interaktionsstatus
4. Formatiert Beats als strukturierten Kontext
5. Speichert `beat_context` und `active_beat_ids` im State

**MasterChatbot Nutzung:**

```python
def masterChatbot(state: State, llm):
    # Beat-Kontext bevorzugen
    if state.get('beat_context'):
        system_context = f"""
        [GESCHLOSSENES WELTWISSEN]
        Verwende AUSSCHLIESSLICH die folgenden Beat-Inhalte:
        
        {state['beat_context']}
        
        Erfinde KEINE neuen Fakten außerhalb dieser Beats.
        """
    else:
        # Fallback: Vollständiger audio_book Text
        system_context = f"Buchkontext: {state['audio_book']}"
```

## Verwendung

### 1. BeatPack erstellen

```bash
# Test-Script ausführen
cd agentic-system
python test_beat_system.py
```

Oder programmatisch:

```python
from beat_pipeline import create_beatpack_from_file

beatpack = create_beatpack_from_file(
    story_id="my_story",
    chapter_id="chapter_01",
    chapter_file=Path("chapter01.txt"),
    output_dir=Path("content")
)
```

### 2. Beat Manager initialisieren

In `chat.py` oder Hauptanwendung:

```python
from nodes import initialize_beat_manager
from pathlib import Path

# Vor Graph-Erstellung
initialize_beat_manager(Path("content"))
```

### 3. State mit Beat-Informationen füllen

Beim Starten einer neuen Conversation:

```python
initial_state = {
    "child_id": "child_123",
    "audio_book_id": "mia_und_leo_01",
    "story_id": "mia_und_leo",        # NEU
    "chapter_id": "chapter_01",       # NEU
    "num_planned_tasks": 5,           # NEU (optional, default=5)
    "messages": []
}

response = immediate_graph.invoke(initial_state, config)
```

### 4. Beat-Kontext wird automatisch geladen

Der `load_beat_context` Node läuft automatisch bei jeder Interaktion:
- **Erste Nachricht**: 5 chronologisch verteilte Beats für Tasks
- **Folge-Nachrichten**: Top-5 relevante Beats basierend auf letzter User-Message

## Task-Integration

Das Beat-System unterstützt die 5-Aufgaben-Strategie:

```python
# Bei initialer Conversation (erstes Mal nach Kapitel-Ende)
num_planned_tasks = 5
beats = retriever.get_beats_for_tasks(num_tasks=num_planned_tasks)

# Dies liefert 5 chronologisch verteilte Beats:
# Beat 2 (Anfang), Beat 5 (frühes Mittel), Beat 8 (Mitte), 
# Beat 11 (spätes Mittel), Beat 14 (Ende)
```

**Aufgaben-Worker Integration:**

Der `aufgabenWorker` kann die `active_beat_ids` nutzen:

```python
def aufgabenWorker(state: BackgroundState, config, llm):
    active_beats = state.get('active_beat_ids', [])
    beat_context = state.get('beat_context', '')
    
    system_prompt = f"""
    Erstelle 5 Aufgaben basierend auf folgenden Beats:
    {beat_context}
    
    Jede Aufgabe soll sich auf einen der Beats beziehen.
    """
```

## Integritätsprüfung

### Automatische Verifikation

Jedes BeatPack kann seine Integrität prüfen:

```python
is_valid, errors = beatpack.verify_integrity()

if not is_valid:
    for error in errors:
        logger.error(f"Beat integrity error: {error}")
```

**Geprüft wird:**
- Hash des Kapiteltexts stimmt überein
- Jeder Beat-Text kann exakt aus dem Kapitel extrahiert werden (via span)
- Keine Beat-Drift oder Text-Manipulationen

### Regression Testing

Für automatisierte Tests:

```python
# test_beat_regression.py
def test_beat_based_responses():
    """Test that responses only use beat content."""
    
    # Lade Konversation
    response = chatbot.invoke(
        {"messages": [HumanMessage("Wer ist Mia?")]},
        config
    )
    
    # Extrahiere verwendete Beat-IDs
    active_beats = response['active_beat_ids']
    
    # Verifiziere: Antwort referenziert nur erlaubte Beats
    beatpack = load_beatpack("mia_und_leo", "chapter_01")
    allowed_content = [beatpack.get_beat_by_id(bid).text for bid in active_beats]
    
    # Prüfe: Keine neuen Facts in Antwort
    assert not contains_new_facts(response['messages'][-1], allowed_content)
```

## Best Practices

### Beat-Größe

- **Minimum**: 50-80 Zeichen (ca. 1 Satz)
- **Maximum**: 200-300 Zeichen (ca. 2-3 Sätze)
- **Optimal für Kinder-Stories**: 100-150 Zeichen

### Entity Registry

Pflegen Sie Aliases sorgfältig:

```python
entity_registry = {
    "Mia": EntityInfo(
        aliases=["sie", "ihr", "das Mädchen", "Mias"],
        entity_type="character"
    ),
    "Oma": EntityInfo(
        aliases=["Großmutter", "sie", "ihr"],  # Kontext-abhängig!
        entity_type="character"
    )
}
```

⚠️ **Achtung**: Pronomen wie "sie" sind mehrdeutig - für Produktions-Systeme empfohlen: Co-Reference Resolution.

### Versionierung

Bei Kapitel-Änderungen:

```python
# Alte Version
beatpack_v1 = BeatPack(
    content_version="2026-02-12T10:00:00Z",
    chapter_hash="sha256:abc123..."
)

# Nach Textänderungen
beatpack_v2 = BeatPack(
    content_version="2026-02-12T14:30:00Z",  # NEU
    chapter_hash="sha256:def456..."          # NEU
)
```

Beide Versionen können parallel existieren für Regression-Tests.

### Performance

**Caching:**
- `BeatPackManager` cached geladene BeatPacks
- Retriever wird pro Request neu erstellt (leichtgewichtig)

**Index-Building:**
- BM25-Index ist in-memory (schnell)
- Für größere Datenmengen: Persistierte Indizes (`beatpack.v1.index.json`)

**Embedding-basierte Suche (optional):**
```python
# Für semantische Suche
from sentence_transformers import SentenceTransformer

model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
embeddings = model.encode([beat.text for beat in beats])
# Speichern in beatpack.v1.embeddings.bin
```

## Erweiterungen

### LLM-assistierte Beat-Refinement

```python
def refine_beats_with_llm(beats: List[Beat], llm) -> List[Beat]:
    """Use LLM to improve beat segmentation."""
    
    prompt = f"""
    Überprüfe folgende Beat-Segmentierung:
    {format_beats(beats)}
    
    Vorschläge für Merge/Split?
    """
    
    suggestions = llm.invoke(prompt)
    # Implementiere Merge/Split basierend auf Vorschlägen
```

### Multi-Chapter Beats

```python
# Für Kontext über Kapitelgrenzen hinweg
def get_cross_chapter_context(story_id: str, chapter_range: range):
    """Get beats from multiple chapters."""
    
    all_beats = []
    for chapter_num in chapter_range:
        chapter_id = f"chapter_{chapter_num:02d}"
        retriever = manager.get_retriever(story_id, chapter_id)
        # ... merge beats ...
```

### Fact-basierte Antwort-Validierung

```python
def validate_response_facts(response: str, active_beats: List[Beat]) -> bool:
    """Check if response only uses facts from active beats."""
    
    allowed_facts = []
    for beat in active_beats:
        allowed_facts.extend(beat.facts)
    
    # Extract facts from response (NLP pipeline)
    response_facts = extract_facts(response)
    
    # Verify: All response facts are in allowed_facts
    for fact in response_facts:
        if not is_fact_supported(fact, allowed_facts):
            return False
    
    return True
```

## Troubleshooting

### Problem: Beat Manager nicht initialisiert

```
WARNING: load_beat_context: Beat manager not initialized
```

**Lösung:**
```python
from nodes import initialize_beat_manager
initialize_beat_manager(Path("content"))
```

### Problem: BeatPack nicht gefunden

```
WARNING: No beatpack found for story_x/chapter_y
```

**Lösung:**
1. BeatPack erstellen: `python test_beat_system.py`
2. Pfad prüfen: `content/stories/story_x/chapter_y/beatpack.v1.json`
3. `story_id` und `chapter_id` im State prüfen

### Problem: Integrity Check schlägt fehl

```
ERROR: Beat integrity check failed: Beat 5 text mismatch
```

**Lösung:**
1. BeatPack neu generieren mit aktuellem Text
2. Hash-Algorithmus konsistent verwenden
3. Text-Normalisierung vor Pipeline prüfen

## Testing

```bash
# Alle Beat-System Tests
cd agentic-system
python test_beat_system.py

# Einzelne Tests
python -m pytest test_beat_system.py::test_beat_retrieval -v
```

**Test Coverage:**
- ✓ Beat-Segmentierung
- ✓ Entity Extraction
- ✓ Retrieval (query-based)
- ✓ Retrieval (task-based)
- ✓ Integrity Verification
- ✓ Context Formatting

## Migration

### Von audio_book zu Beats

**Alt:**
```python
system_context = f"Buchkontext: {state['audio_book']}"
```

**Neu:**
```python
# Opt-in: Nur wenn story_id/chapter_id gesetzt
if state.get('beat_context'):
    system_context = state['beat_context']
else:
    system_context = f"Buchkontext: {state['audio_book']}"
```

**Rollout-Strategie:**
1. Beat-System parallel aktivieren (wie implementiert)
2. A/B Testing: Mit/Ohne Beats
3. Metriken: Halluzination-Rate, Antwort-Qualität
4. Nach Validierung: Beats als Standard

## Zusammenfassung

Das Beat-System bietet:

✅ **Closed-World Content**: Keine Halluzinationen  
✅ **Granulare Kontrolle**: Beat-level Kontext-Management  
✅ **Prüfbarkeit**: Verifiable Evidence Chain  
✅ **Task-Integration**: 5-Aufgaben-Strategie unterstützt  
✅ **Performance**: Effizientes Retrieval & Caching  
✅ **Erweiterbar**: LLM-Refinement, Embeddings, Multi-Chapter  

**Next Steps:**
1. BeatPacks für alle Kapitel erstellen
2. Beat Manager in Produktion initialisieren
3. State mit `story_id`/`chapter_id` befüllen
4. Monitoring & Regression Tests aufsetzen

