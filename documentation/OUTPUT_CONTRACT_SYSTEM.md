# Output Contract System - Messbares Halluzinationsmanagement

## Überblick

Das Output Contract System macht KI-Antworten messbar und validierbar, indem es neben der gesprochenen Antwort automatisch maschinenprüfbare Belege und Claims extrahiert.

## Kernprinzip

**Der zentrale Trick**: Statt das LLM zu bitten, JSON zu generieren, generiert es nur die **natürliche Antwort**. Der Rest wird **programmatisch** aus dem Kontext konstruiert.

### Warum dieser Ansatz besser ist:

1. **LLM macht was es am besten kann**: Natürliche, kindgerechte Antworten generieren
2. **Code macht was er am besten kann**: Strukturierte Daten aus bekanntem Kontext extrahieren
3. **Keine JSON-Parsing-Fehler**: LLM muss kein perfektes JSON produzieren
4. **Konsistente Qualität**: Evidence und Claims werden deterministisch aus dem Beat-Kontext extrahiert

## Architektur

```
┌─────────────────────────────────────────────────────────────┐
│                    Master Chatbot Node                       │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  1. LLM generiert natürliche Antwort                 │  │
│  │     "Mia ist nach Hause gegangen, weil es dunkel     │  │
│  │      wurde."                                          │  │
│  └──────────────────────────────────────────────────────┘  │
│                            ↓                                 │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  2. Output Contract Builder (Code)                    │  │
│  │     ├─ Detektiert Answer Type (ANSWER/QUESTION/...)  │  │
│  │     ├─ Extrahiert Task Type aus aufgaben             │  │
│  │     ├─ Findet Evidence via Fuzzy Match in Beats      │  │
│  │     ├─ Baut Claims aus Sätzen                        │  │
│  │     └─ Berechnet Confidence Score                    │  │
│  └──────────────────────────────────────────────────────┘  │
│                            ↓                                 │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  3. Output: Response Contract                        │  │
│  │     {                                                 │  │
│  │       "spoken_text": "...",                          │  │
│  │       "answer_type": "ANSWER",                       │  │
│  │       "grounding": {                                 │  │
│  │         "evidence": [...],                           │  │
│  │         "claims": [...]                              │  │
│  │       }                                              │  │
│  │     }                                                │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## Output Contract Struktur

```typescript
{
  "answer_type": "ANSWER" | "QUESTION" | "STATEMENT" | "TASK_INSTRUCTION",
  "spoken_text": string,  // Der eigentliche Text für das Kind
  "task": {
    "task_type": "COMPREHENSION_QUESTION" | "GRAMMAR_EXERCISE" | ...,
    "prompt_spoken": string,  // Die gestellte Frage/Aufgabe
    "expected_child_response_type": "FREE_TEXT" | "YES_NO" | ...,
    "learning_goal": string  // Nicht gesprochen, nur für Validierung
  } | null,
  "grounding": {
    "story_id": string,
    "chapter_id": string,
    "evidence": [
      {
        "beat_id": number,
        "quote": string,  // EXAKTES Zitat aus dem Beat
        "source": string
      }
    ],
    "claims": [
      {
        "claim": string,  // Einzelne Behauptung aus der Antwort
        "supported_by": number[]  // Indices der Evidence-Items
      }
    ]
  },
  "confidence": number  // 0.0-1.0
}
```

## Komponenten

### 1. Output Contract Builder (`output_contract_builder.py`)

**Automatische Contract-Konstruktion aus Kontext**

#### Funktionen:

- **`detect_answer_type()`**: Klassifiziert Antworttyp aus Textmustern
  - Fragezeichen → QUESTION
  - Task-Keywords → TASK_INSTRUCTION
  - Antwort-Indikatoren → ANSWER

- **`detect_task_type()`**: Extrahiert Task-Type aus `aufgaben` State
  - Keyword-Matching für verschiedene Task-Typen
  - Learning Goals automatisch zuordnen

- **`fuzzy_match_quote_to_beat()`**: Findet Quotes in Beats
  - Zuerst exaktes Matching
  - Dann Fuzzy Matching (SequenceMatcher)
  - Threshold-basiert (default: 0.6)

- **`build_output_contract()`**: Hauptfunktion
  - Kombiniert alle Komponenten
  - Baut vollständigen Contract
  - Berechnet Confidence Score

#### Beispiel:

```python
contract = build_output_contract(
    response="Mia ging nach Hause, weil es dunkel wurde.",
    active_beats=[beat1, beat2, beat3],
    story_id="mia_und_leo",
    chapter_id="chapter_01",
    aufgaben="Stelle Verständnisfragen..."
)
```

### 2. Output Contract Validator (`output_contract_validator.py`)

**Validierung gegen tatsächlichen Story-Content**

#### Validierungsschritte:

1. **Evidence Validation**:
   - Quote MUSS exakt im Beat-Content vorkommen
   - Falls nicht: Normalized Whitespace Matching
   - Sonst: ERROR

2. **Claims Validation**:
   - Jeder Claim MUSS mindestens einen Evidence-Index haben
   - Alle Indices müssen gültig sein
   - Support-Chain nachvollziehbar

#### Beispiel:

```python
from services.output_contract_validator import validate_response_contract

result = validate_response_contract(
    contract=response_contract,
    beat_manager=beat_manager,
    story_id="mia_und_leo",
    chapter_id="chapter_01"
)

if result.is_valid:
    print("✓ Contract validated")
else:
    print(f"✗ Errors: {result.errors}")
```

### 3. API Endpoint (`/conversations/{thread_id}/contract`)

**Zugriff auf Output Contracts über REST API**

```bash
# Contract ohne Validierung abrufen
GET /api/conversations/{thread_id}/contract

# Contract mit Validierung abrufen
GET /api/conversations/{thread_id}/contract?validate=true
```

**Response Beispiel:**

```json
{
  "thread_id": "conv_abc123",
  "contract": {
    "answer_type": "ANSWER",
    "spoken_text": "Mia ist nach Hause gegangen...",
    "grounding": {
      "evidence": [...],
      "claims": [...]
    },
    "confidence": 0.85
  },
  "validation": {
    "is_valid": true,
    "errors": [],
    "warnings": [],
    "evidence_validation": [...],
    "claims_validation": [...]
  }
}
```

## Integration in Master Node

Der `masterChatbot` Node wurde angepasst:

### Vorher (LLM generiert JSON):
```python
# LLM musste JSON mit allem generieren
response = llm.invoke(messages)  # Erwartet komplexes JSON
```

### Nachher (LLM generiert nur Text):
```python
# LLM generiert nur natürliche Antwort
response = llm.invoke(messages)
spoken_text = response.content

# Code baut Contract
contract = build_output_contract(
    response=spoken_text,
    active_beats=active_beats,
    story_id=state.get('story_id'),
    chapter_id=state.get('chapter_id'),
    aufgaben=state.get('aufgaben')
)

return {
    "messages": [AIMessage(content=spoken_text)],
    "response_contract": contract
}
```

## Vorteile des Systems

### 1. Messbarkeit
- **Hard Validation**: Evidence-Quotes müssen exakt existieren
- **Claims-Tracking**: Jede Behauptung hat Quellennachweis
- **Confidence Score**: Automatisch basierend auf Evidence-Qualität

### 2. Debugging
- **Transparenz**: Sofort sichtbar, welche Beats verwendet wurden
- **Nachvollziehbarkeit**: Claims zu Evidence-Mapping
- **Fehlerdiagnose**: Validation errors zeigen genau, was fehlt

### 3. Qualitätssicherung
- **Halluzination Detection**: Fehlende Evidence = potenzielle Halluzination
- **A/B Testing**: Confidence Scores vergleichen
- **Monitoring**: Contract-Qualität über Zeit tracken

### 4. Flexibilität
- **Beat-basiert**: Nutzt bestehende Beat-Infrastruktur
- **Fallback**: Funktioniert auch ohne Beats (niedrigere Confidence)
- **Erweiterbar**: Neue Validierungsregeln einfach hinzufügbar

## Testing

Test-Suite verfügbar in `test_output_contract.py`:

```bash
python test_output_contract.py
```

**Tests:**
1. Basic contract ohne Beats
2. Contract mit Beat evidence
3. Question detection
4. Fuzzy matching

## Zukunftserweiterungen

### Geplant:
- [ ] NLP-basierte Sentence Splitting (statt Regex)
- [ ] Semantic Similarity für besseres Matching
- [ ] Multi-Evidence Support (mehrere Beats pro Claim)
- [ ] Confidence-Tuning basierend auf Produktionsdaten
- [ ] LLM-Judge Integration für Claim-Validation
- [ ] Metrics Dashboard für Contract-Qualität

### Möglich:
- Auto-Correction bei niedrigem Confidence
- Proaktive Warnung bei fehlenden Evidence
- Learning-Analytics aus Task-Types
- Evidence-Caching für Performance

## Best Practices

### Für Entwickler:
1. **Immer validate=true bei Tests**: Finde Probleme früh
2. **Confidence < 0.7 = Review**: Niedrige Scores prüfen
3. **Claims ohne Evidence = Bug**: Sollte nicht vorkommen
4. **Beat-Context aktuell halten**: Stale Beats = schlechte Matches

### Für Prompt-Engineering:
1. **Klarheit über Komplexität**: Einfache, direkte Antworten
2. **Beat-Nähe**: Formulierungen nah am Beat-Text
3. **Fokus auf Fakten**: Claims sollten faktisch sein
4. **Keine Spekulationen**: Nur was in Beats steht

## Beispiel-Workflow

```python
# 1. Conversation erstellen mit Beat-System
conversation = service.create_conversation(
    child_id="1",
    game_id="0",
    story_id="mia_und_leo",
    chapter_id="chapter_01",
    num_planned_tasks=5
)

# 2. Nachricht senden (generiert automatisch Contract)
response = await service.send_message_stream(
    thread_id=conversation.thread_id,
    message="Warum ist Mia nach Hause gegangen?"
)

# 3. Contract abrufen und validieren
contract_data = service.get_last_response_contract(
    thread_id=conversation.thread_id,
    validate=True
)

# 4. Validierung prüfen
if contract_data['validation']['is_valid']:
    print("✓ Response ist durch Evidence belegt")
    print(f"Confidence: {contract_data['contract']['confidence']}")
else:
    print("✗ Validierungsfehler:")
    for error in contract_data['validation']['errors']:
        print(f"  - {error}")
```

## Zusammenfassung

Das Output Contract System macht LLM-Outputs **messbar**, **validierbar** und **nachvollziehbar** - ohne die Qualität der natürlichen Antworten zu beeinträchtigen. Es trennt klar zwischen:

- **Was das LLM tut**: Natürliche, kindgerechte Sprache generieren
- **Was der Code tut**: Struktur, Evidence und Claims aus Kontext extrahieren
- **Was validiert wird**: Exakte Übereinstimmung zwischen Antwort und Quelle

Dies ist der Schlüssel zu vertrauenswürdigen, pädagogisch wertvollen Dialogen.

