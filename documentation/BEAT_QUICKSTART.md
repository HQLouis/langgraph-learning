# 🚀 Beat System - Quick Start Guide

## Schnellstart in 5 Minuten

### 1. Beat Manager initialisieren (1 Zeile)

In `chat.py` oder `backend/main.py`:

```python
from nodes import initialize_beat_manager
from pathlib import Path

initialize_beat_manager(Path("agentic-system/content"))
```

### 2. BeatPack erstellen (Test-Beispiel ausführen)

```bash
cd agentic-system
python test_beat_system.py
```

**Output:**
```
✓ Created beatpack with 10 beats
✓ Saved to: content/stories/mia_und_leo/chapter_01/beatpack.v1.json
```

### 3. API-Request mit Beat-System

```python
# Bei Chat-Request
state = {
    "child_id": "child_123",
    "audio_book_id": "mia_leo_01",
    "story_id": "mia_und_leo",      # ← Aktiviert Beat-System
    "chapter_id": "chapter_01",     # ← Aktiviert Beat-System
    "messages": [HumanMessage("Wer ist Leo?")]
}

response = immediate_graph.invoke(state, config)
```

**Das war's!** Das System nutzt jetzt automatisch Beats. 🎉

---

## Wie erkenne ich, dass es funktioniert?

### Im Log:

```
INFO: load_beat_context: Loaded 5 beats: [1, 3, 5, 7, 9]
INFO: masterChatbot: Using beat-based context (closed-world)
```

### Im Response:

```python
{
    "beat_context": "[GESCHICHTSKONTEXT]...",
    "active_beat_ids": [5, 7, 8],
    "messages": [AIMessage("Leo ist ein freundlicher Fuchs...")]
}
```

---

## Eigene Story hinzufügen

### Schritt 1: Text vorbereiten

`my_story.txt`:
```
Es war einmal ein kleines Mädchen namens Anna.
Anna wohnte in einem großen Haus am See...
```

### Schritt 2: BeatPack erstellen

```python
from beat_pipeline import create_beatpack_from_file
from beats import EntityInfo

entity_registry = {
    "Anna": EntityInfo(aliases=["sie", "das Mädchen"], entity_type="character"),
    "See": EntityInfo(aliases=["am See", "den See"], entity_type="location")
}

create_beatpack_from_file(
    story_id="anna_am_see",
    chapter_id="chapter_01",
    chapter_file=Path("my_story.txt"),
    output_dir=Path("agentic-system/content")
)
```

### Schritt 3: Verwenden

```python
state = {
    "story_id": "anna_am_see",
    "chapter_id": "chapter_01",
    # ...
}
```

---

## Ohne Beat-System (Fallback)

Einfach `story_id` und `chapter_id` **weglassen**:

```python
state = {
    "child_id": "child_123",
    "audio_book_id": "some_book",
    # Kein story_id / chapter_id
    "messages": [...]
}
```

→ System nutzt automatisch `audio_book` (wie bisher)

---

## Troubleshooting

### "Beat manager not initialized"

```python
# Lösung: Einmal beim App-Start aufrufen
initialize_beat_manager(Path("agentic-system/content"))
```

### "No beatpack found"

```bash
# Lösung: BeatPack erstellen
cd agentic-system
python test_beat_system.py  # Für Test-Story
# oder
python your_beatpack_generator.py  # Für eigene Stories
```

### "Integrity check failed"

→ Normal bei Whitespace-Unterschieden. Nicht kritisch.

---

## Nächste Schritte

- 📖 **Details**: Siehe `BEAT_SYSTEM_README.md`
- 💻 **Code-Beispiele**: Siehe `BEAT_INTEGRATION_EXAMPLE.py`
- 🏗️ **Architektur**: Siehe `BEAT_ARCHITECTURE.md`
- ✅ **Status**: Siehe `BEAT_SYSTEM_COMPLETE.md`

---

**Happy Coding!** 🚀

