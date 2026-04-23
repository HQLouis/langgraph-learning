# Beat System Architecture Diagram

## System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        BEAT SYSTEM ARCHITECTURE                      │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                         1. CONTENT PREPARATION                       │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  Raw Chapter Text                                                     │
│  ┌─────────────────────────────────────────────────┐                │
│  │ Es war einmal ein kleines Mädchen namens Mia.  │                │
│  │ Mia lebte in einem kleinen Dorf am Waldrand... │                │
│  └─────────────────────────────────────────────────┘                │
│                          ↓                                            │
│                  BeatPipeline.create_beatpack()                      │
│                          ↓                                            │
│  ┌─────────────────────────────────────────────────┐                │
│  │ 1. Text Normalization (Unicode, Whitespace)     │                │
│  │ 2. Segmentation (Sentences, Transitions)        │                │
│  │ 3. Entity Extraction (Characters, Locations)    │                │
│  │ 4. Fact Extraction (Optional: S-P-O triples)    │                │
│  │ 5. Index Building (BM25-style)                  │                │
│  │ 6. Versioning (Hash, Timestamp)                 │                │
│  └─────────────────────────────────────────────────┘                │
│                          ↓                                            │
│  BeatPack (JSON)                                                     │
│  ┌─────────────────────────────────────────────────┐                │
│  │ {                                                │                │
│  │   "story_id": "mia_und_leo",                    │                │
│  │   "chapter_id": "chapter_01",                   │                │
│  │   "beats": [                                     │                │
│  │     {beat_id: 1, text: "...", entities: [...]}  │                │
│  │   ],                                             │                │
│  │   "entity_registry": {...}                      │                │
│  │ }                                                │                │
│  └─────────────────────────────────────────────────┘                │
│                          ↓                                            │
│  Saved to: content/stories/{story_id}/{chapter_id}/beatpack.v1.json │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘


┌─────────────────────────────────────────────────────────────────────┐
│                         2. RUNTIME FLOW                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  User Request                                                         │
│  ┌─────────────────────────────────────────────────┐                │
│  │ {                                                │                │
│  │   "message": "Wer ist Leo?",                    │                │
│  │   "story_id": "mia_und_leo",      ◄── NEW      │                │
│  │   "chapter_id": "chapter_01"      ◄── NEW      │                │
│  │ }                                                │                │
│  └─────────────────────────────────────────────────┘                │
│                          ↓                                            │
│                                                                       │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │                    IMMEDIATE GRAPH                             │  │
│  │                                                                 │  │
│  │  START                                                          │  │
│  │    ↓                                                            │  │
│  │  initialStateLoader                                             │  │
│  │    ↓                                                            │  │
│  │  load_analysis                                                  │  │
│  │    ↓                                                            │  │
│  │  load_beat_context ◄─────────────── NEW NODE                  │  │
│  │    │                                                            │  │
│  │    ├─► Check: story_id + chapter_id present?                   │  │
│  │    │                                                            │  │
│  │    ├─► Load BeatPack from BeatPackManager                      │  │
│  │    │   (cached for performance)                                │  │
│  │    │                                                            │  │
│  │    ├─► Strategy Decision:                                      │  │
│  │    │   • First interaction? → get_beats_for_tasks(5)           │  │
│  │    │   • Follow-up? → retrieve_beats(query, top_k=5)           │  │
│  │    │                                                            │  │
│  │    ├─► Format beats as context                                 │  │
│  │    │                                                            │  │
│  │    └─► Update state:                                           │  │
│  │        • beat_context: formatted string                        │  │
│  │        • active_beat_ids: [1, 3, 5, 7, 9]                     │  │
│  │    ↓                                                            │  │
│  │  masterChatbot ◄─────────────────── UPDATED                   │  │
│  │    │                                                            │  │
│  │    ├─► IF beat_context present:                                │  │
│  │    │     system_prompt = "[GESCHLOSSENES WELTWISSEN]"          │  │
│  │    │                     + beat_context                        │  │
│  │    │                                                            │  │
│  │    └─► ELSE (fallback):                                        │  │
│  │          system_prompt = "Buchkontext: " + audio_book          │  │
│  │    ↓                                                            │  │
│  │  END                                                            │  │
│  │                                                                 │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                          ↓                                            │
│  Response                                                             │
│  ┌─────────────────────────────────────────────────┐                │
│  │ {                                                │                │
│  │   "messages": [...],                             │                │
│  │   "beat_context": "...",                         │                │
│  │   "active_beat_ids": [1, 3, 5, 7, 9]            │                │
│  │ }                                                │                │
│  └─────────────────────────────────────────────────┘                │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘


┌─────────────────────────────────────────────────────────────────────┐
│                      3. BEAT RETRIEVAL STRATEGIES                    │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  Strategy A: First Interaction (Task-based)                          │
│  ┌─────────────────────────────────────────────────┐                │
│  │                                                  │                │
│  │  num_planned_tasks = 5                          │                │
│  │                                                  │                │
│  │  Chapter with 14 beats:                         │                │
│  │  [1] [2] [3] [4] [5] [6] [7] [8] [9] [10] ... [14]              │
│  │   ↑       ↑       ↑       ↑       ↑                              │
│  │   │       │       │       │       │                              │
│  │  Beat 1  Beat 3  Beat 5  Beat 7  Beat 9                         │
│  │  (Start) (Early) (Mid)   (Late)  (Near End)                     │
│  │                                                  │                │
│  │  → Chronologically distributed for tasks        │                │
│  │                                                  │                │
│  └─────────────────────────────────────────────────┘                │
│                                                                       │
│  Strategy B: Follow-up Interaction (Query-based)                     │
│  ┌─────────────────────────────────────────────────┐                │
│  │                                                  │                │
│  │  User Query: "Wer ist Leo?"                     │                │
│  │       ↓                                          │                │
│  │  Tokenize: ["wer", "ist", "leo"]                │                │
│  │       ↓                                          │                │
│  │  BM25-style scoring against all beats            │                │
│  │       ↓                                          │                │
│  │  Beats mentioning "Leo":                         │                │
│  │  - Beat 5: "...Leo...Fuchs..." (score: 2)       │                │
│  │  - Beat 7: "Leo zeigte..." (score: 1)           │                │
│  │  - Beat 8: "...Leo..." (score: 1)               │                │
│  │       ↓                                          │                │
│  │  Sort by relevance + chronological order         │                │
│  │       ↓                                          │                │
│  │  Return top-5 beats                              │                │
│  │                                                  │                │
│  └─────────────────────────────────────────────────┘                │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘


┌─────────────────────────────────────────────────────────────────────┐
│                      4. CONTEXT FORMATTING                           │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  Input: [Beat 5, Beat 7, Beat 8]                                    │
│         ↓                                                             │
│  Output:                                                              │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │ [GESCHICHTSKONTEXT - NUR DIESE INHALTE VERWENDEN]          │    │
│  │                                                              │    │
│  │ [Beat 5]: Seine Augen funkelten neugierig. "Keine Angst",  │    │
│  │ sagte der Fuchs freundlich. "Ich bin Leo..."               │    │
│  │   → Figuren/Orte: Leo, Fuchs, Augen                        │    │
│  │                                                              │    │
│  │ [Beat 7]: Ich kenne die besten Stellen im Wald. Gemeinsam  │    │
│  │ gingen Mia und Leo tiefer in den Wald hinein...            │    │
│  │   → Figuren/Orte: Mia, Leo, Wald, Himbeeren                │    │
│  │                                                              │    │
│  │ [Beat 8]: Mia füllte ihren Korb bis zum Rand. "Danke für   │    │
│  │ deine Hilfe, Leo", sagte Mia glücklich...                  │    │
│  │   → Figuren/Orte: Mia, Leo, Korb, Beeren                   │    │
│  │                                                              │    │
│  │ [BEKANNTE FIGUREN/ORTE]                                     │    │
│  │   • Mia (auch: sie, das Mädchen, ihr)                      │    │
│  │   • Leo (auch: der Fuchs, er, ihm)                         │    │
│  │   • Wald (auch: im Wald, den Wald)                         │    │
│  │                                                              │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘


┌─────────────────────────────────────────────────────────────────────┐
│                      5. CLOSED-WORLD PRINCIPLE                       │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  WITHOUT Beat System:                                                 │
│  ┌──────────────────────────────────────────────────────┐            │
│  │ LLM receives full chapter (2000+ tokens)              │            │
│  │   ↓                                                    │            │
│  │ May hallucinate or mix scenes                         │            │
│  │ No evidence trail                                      │            │
│  └──────────────────────────────────────────────────────┘            │
│                                                                       │
│  WITH Beat System:                                                    │
│  ┌──────────────────────────────────────────────────────┐            │
│  │ LLM receives only 5 relevant beats (~500 tokens)      │            │
│  │   ↓                                                    │            │
│  │ [STRICT INSTRUCTION]                                   │            │
│  │ "Use ONLY these beats. Do not invent facts."          │            │
│  │   ↓                                                    │            │
│  │ Response stays within beat boundaries                  │            │
│  │   ↓                                                    │            │
│  │ Evidence: active_beat_ids = [5, 7, 8]                │            │
│  │   ↓                                                    │            │
│  │ ✓ Verifiable, stable, no hallucinations               │            │
│  └──────────────────────────────────────────────────────┘            │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘


┌─────────────────────────────────────────────────────────────────────┐
│                      6. DATA FLOW SUMMARY                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  Offline (One-time):                                                  │
│    Chapter Text → BeatPipeline → BeatPack.json                      │
│                                                                       │
│  Runtime (Per Request):                                               │
│    User Query → load_beat_context → BeatRetriever →                 │
│    → Select Beats → Format Context → masterChatbot → Response        │
│                                                                       │
│  Evidence Chain:                                                      │
│    active_beat_ids → BeatPack → Specific text spans →               │
│    → Verifiable against chapter_hash                                 │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

## Key Benefits Visualization

```
┌─────────────────────────────────────────────────────────────────┐
│                    BEAT SYSTEM BENEFITS                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  🎯 Closed-World          │  Only uses actual story content      │
│  🔒 Scene-Integrity       │  Doesn't mix unrelated scenes        │
│  🚫 No-New-Facts          │  Prevents hallucinations             │
│  📊 Evidence              │  Machine-verifiable beat IDs         │
│  ⚡ Token-Efficient       │  ~500 tokens vs 2000+ tokens         │
│  🎓 Task-Integration      │  5 distributed beats = 5 tasks       │
│  🔄 Verifiable            │  Hash-based integrity checks         │
│  📈 Testable              │  Regression without LLM judge        │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

