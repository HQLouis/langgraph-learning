"""
Example: How to integrate the Beat System into your application

This demonstrates the minimal changes needed to activate the beat system.
"""

# ============================================================================
# 1. Initialize Beat Manager (at application startup)
# ============================================================================

# In chat.py or backend/main.py - add this BEFORE creating graphs:

from pathlib import Path
from nodes import initialize_beat_manager

# Initialize beat manager with content directory
content_dir = Path(__file__).parent / "content"
initialize_beat_manager(content_dir)
print(f"✓ Beat Manager initialized with {content_dir}")


# ============================================================================
# 2. Create BeatPacks for your content (one-time setup)
# ============================================================================

# Run this as a separate script to generate beatpacks for your stories:

from beat_pipeline import create_beatpack_from_file
from beats import EntityInfo

def generate_beatpacks():
    """Generate beatpacks for all your story chapters."""

    # Example: Create beatpack for a chapter
    story_id = "die_kleine_raupe_nimmersatt"
    chapter_id = "chapter_01"

    # Define entities and aliases for better retrieval
    entity_registry = {
        "Raupe": EntityInfo(
            aliases=["die Raupe", "sie", "ihr"],
            entity_type="character"
        ),
        "Blatt": EntityInfo(
            aliases=["das Blatt", "ein Blatt"],
            entity_type="object"
        ),
        # Add more entities...
    }

    # Create beatpack
    beatpack = create_beatpack_from_file(
        story_id=story_id,
        chapter_id=chapter_id,
        chapter_file=Path(f"raw_content/{story_id}/{chapter_id}.txt"),
        output_dir=Path("content")
    )

    print(f"✓ Created beatpack with {len(beatpack.beats)} beats")
    print(f"  Saved to: content/stories/{story_id}/{chapter_id}/beatpack.v1.json")

# Run once to generate all beatpacks
# generate_beatpacks()


# ============================================================================
# 3. Update your API endpoint to pass beat information
# ============================================================================

# In your FastAPI endpoint or graph invocation:

def handle_chat_request(
    child_id: str,
    audio_book_id: str,
    message: str,
    story_id: str = None,  # NEW
    chapter_id: str = None,  # NEW
):
    """
    Handle chat request with optional beat system support.

    If story_id and chapter_id are provided, the beat system will be used.
    Otherwise, falls back to full audio_book context.
    """

    # Build initial state
    initial_state = {
        "child_id": child_id,
        "audio_book_id": audio_book_id,
        "messages": [HumanMessage(content=message)],
    }

    # Add beat system parameters if available
    if story_id and chapter_id:
        initial_state["story_id"] = story_id
        initial_state["chapter_id"] = chapter_id
        initial_state["num_planned_tasks"] = 5  # Optional, defaults to 5
        print(f"✓ Using beat system for {story_id}/{chapter_id}")
    else:
        print("⚠ No beat info provided, using full audio_book context")

    # Invoke graph (no changes needed here!)
    response = immediate_graph.invoke(initial_state, config)

    # Optional: Return beat evidence for debugging/validation
    if "active_beat_ids" in response:
        print(f"  Used beats: {response['active_beat_ids']}")

    return response


# ============================================================================
# 4. Example API Request with Beat System
# ============================================================================

"""
POST /chat
{
    "child_id": "child_123",
    "audio_book_id": "raupe_01",
    "message": "Was hat die Raupe gegessen?",
    "story_id": "die_kleine_raupe_nimmersatt",  // NEW
    "chapter_id": "chapter_01"                   // NEW
}

Response includes:
- Normal chat response
- beat_context: formatted beat content (in state)
- active_beat_ids: [1, 3, 5, 7, 9] (beats used)
"""


# ============================================================================
# 5. Gradual Rollout Strategy
# ============================================================================

def should_use_beats(child_id: str, audio_book_id: str) -> bool:
    """
    Decide whether to use beat system for this request.

    Strategies:
    1. A/B Testing: 50% of users get beats
    2. Feature Flag: Enable for specific stories only
    3. Progressive Rollout: Start with new content
    """

    # Example: A/B testing (hash-based)
    import hashlib
    user_hash = int(hashlib.md5(child_id.encode()).hexdigest(), 16)
    use_beats = (user_hash % 100) < 50  # 50% of users

    # Example: Feature flag for specific stories
    BEAT_ENABLED_STORIES = ["die_kleine_raupe_nimmersatt", "mia_und_leo"]
    story_id = extract_story_id_from_audio_book_id(audio_book_id)
    use_beats = story_id in BEAT_ENABLED_STORIES

    return use_beats


# ============================================================================
# 6. Monitoring & Validation
# ============================================================================

def log_beat_usage(response):
    """Log beat system usage for monitoring."""

    if "beat_context" in response:
        import logging
        logger = logging.getLogger(__name__)

        logger.info(f"Beat System Used", extra={
            "story_id": response.get("story_id"),
            "chapter_id": response.get("chapter_id"),
            "num_beats": len(response.get("active_beat_ids", [])),
            "beat_ids": response.get("active_beat_ids"),
            "context_length": len(response.get("beat_context", ""))
        })


# ============================================================================
# 7. Background Worker Integration (optional)
# ============================================================================

# The aufgabenWorker can also access beat information:

def aufgabenWorker(state: BackgroundState, config, llm):
    """
    Create tasks based on beat content.
    """
    system_message = SystemMessage(content=getAufgabenWorker_prompt())

    # Access beat information
    beat_context = state.get('beat_context', '')
    active_beat_ids = state.get('active_beat_ids', [])

    # Enhanced prompt with beat context
    analysis_message = HumanMessage(
        content=f"""
        Förderfokus: {state.get('foerderfokus', '')}
        Child profile: {state.get('child_profile', '')}
        
        Erstelle 5 Aufgaben basierend auf folgenden Story-Beats:
        {beat_context}
        
        Jede Aufgabe soll sich auf einen spezifischen Beat beziehen.
        Beat IDs verfügbar: {active_beat_ids}
        """
    )

    response = llm.invoke([system_message, analysis_message])
    return Command(update={"aufgaben": response.content})


# ============================================================================
# Summary: What You Need to Do
# ============================================================================

"""
SCHRITT 1: Beat Manager initialisieren
  → In chat.py: initialize_beat_manager(Path("content"))

SCHRITT 2: BeatPacks erstellen
  → Für jedes Kapitel: create_beatpack_from_file(...)

SCHRITT 3: API erweitern
  → story_id und chapter_id Parameter hinzufügen
  → In initial_state übergeben

SCHRITT 4: Testen
  → Mit story_id/chapter_id → Beat System aktiv
  → Ohne → Fallback zu audio_book (wie bisher)

SCHRITT 5: Monitoren
  → active_beat_ids loggen
  → Qualität vergleichen (mit/ohne Beats)

SCHRITT 6: Rollout
  → Schrittweise für einzelne Stories aktivieren
  → Nach Validierung: Standard für alle neuen Inhalte
"""

print(__doc__)

