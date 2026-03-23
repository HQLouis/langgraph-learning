"""
Test script for beat system - demonstrates creating and using beatpacks.
"""
import logging
from pathlib import Path
from beat_pipeline import BeatPipeline
from beats import BeatPackManager, EntityInfo

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_example_beatpack():
    """Create an example beatpack for testing."""

    # Example German children's story
    example_text = """
    Es war einmal ein kleines Mädchen namens Mia. Mia lebte in einem kleinen Dorf am Waldrand.
    Jeden Tag schaute sie aus ihrem Fenster und träumte davon, den Wald zu erkunden.
    
    Eines Morgens beschloss Mia, in den Wald zu gehen, um Beeren zu sammeln. Sie nahm einen kleinen Korb mit.
    Der Wald war dunkel und geheimnisvoll. Hohe Bäume ragten in den Himmel.
    
    Plötzlich hörte sie ein Rascheln im Gebüsch. Mia blieb stehen und lauschte aufmerksam.
    "Wer ist da?", fragte Mia mutig. Ihre Stimme klang fest, aber ihr Herz klopfte schnell.
    
    Ein kleiner Fuchs sprang aus dem Gebüsch hervor. Seine Augen funkelten neugierig.
    "Keine Angst", sagte der Fuchs freundlich. "Ich bin Leo und ich bin nur auf der Suche nach meinem Abendessen."
    
    Mia lächelte erleichtert. "Ich heiße Mia", antwortete sie. "Ich sammle Beeren. Möchtest du mir helfen?"
    Der Fuchs nickte eifrig. "Gerne! Ich kenne die besten Stellen im Wald."
    
    Gemeinsam gingen Mia und Leo tiefer in den Wald hinein. Leo zeigte ihr einen versteckten Platz voller Himbeeren.
    Die Beeren waren rot und saftig. Mia füllte ihren Korb bis zum Rand.
    
    "Danke für deine Hilfe, Leo", sagte Mia glücklich. Sie gab dem Fuchs ein paar Beeren.
    "Gern geschehen", antwortete Leo und knabberte genüsslich an den Beeren.
    
    Als die Sonne langsam unterging, färbte sich der Himmel orange und rosa. Es wurde Zeit, nach Hause zu gehen.
    "Wir sehen uns morgen wieder?", fragte Leo hoffnungsvoll.
    
    "Auf jeden Fall!", versprach Mia. Sie winkte zum Abschied und machte sich auf den Heimweg.
    Mit ihrem vollen Korb und einem neuen Freund im Herzen ging Mia fröhlich nach Hause zurück.
    """

    # Define entities and their aliases
    entity_registry = {
        "Mia": EntityInfo(
            aliases=["sie", "das Mädchen", "ihr"],
            entity_type="character"
        ),
        "Leo": EntityInfo(
            aliases=["der Fuchs", "er", "ihm"],
            entity_type="character"
        ),
        "Wald": EntityInfo(
            aliases=["im Wald", "den Wald", "des Waldes"],
            entity_type="location"
        ),
        "Dorf": EntityInfo(
            aliases=["das Dorf", "dem Dorf"],
            entity_type="location"
        ),
        "Korb": EntityInfo(
            aliases=["einen Korb", "den Korb", "ihren Korb"],
            entity_type="object"
        )
    }

    # Create pipeline
    logger.info("Creating beat pipeline...")
    pipeline = BeatPipeline(
        story_id="mia_und_leo",
        chapter_id="chapter_01",
        chapter_text=example_text,
        min_beat_length=40,
        max_beat_length=200
    )

    # Create beatpack
    logger.info("Generating beatpack...")
    beatpack = pipeline.create_beatpack(entity_registry=entity_registry)

    # Save beatpack
    output_dir = Path(__file__).parent / "content"
    beatpack.save(output_dir / "stories" / "mia_und_leo" / "chapter_01" / "beatpack.v1.json")

    logger.info(f"Created beatpack with {len(beatpack.beats)} beats")

    # Print beat summary
    print("\n" + "="*80)
    print("BEATPACK SUMMARY")
    print("="*80)
    print(f"Story: {beatpack.story_id}")
    print(f"Chapter: {beatpack.chapter_id}")
    print(f"Version: {beatpack.beatpack_version}")
    print(f"Number of beats: {len(beatpack.beats)}")
    print(f"Chapter hash: {beatpack.chapter_hash[:32]}...")
    print("\nBeats:")
    print("-"*80)

    for beat in beatpack.beats:
        print(f"\nBeat {beat.beat_id} (Order: {beat.order})")
        print(f"Text: {beat.text}")
        if beat.entities:
            print(f"Entities: {', '.join(beat.entities)}")
        if beat.tags:
            print(f"Tags: {', '.join(beat.tags)}")

    print("\n" + "="*80)
    print("ENTITY REGISTRY")
    print("="*80)
    for entity, info in beatpack.entity_registry.items():
        aliases_str = ", ".join(info.aliases) if info.aliases else "none"
        print(f"{entity} ({info.entity_type}): {aliases_str}")

    return beatpack


def test_beat_retrieval():
    """Test beat retrieval functionality."""

    # Create example beatpack first
    beatpack = create_example_beatpack()

    print("\n" + "="*80)
    print("TESTING BEAT RETRIEVAL")
    print("="*80)

    # Initialize beat manager
    content_dir = Path(__file__).parent / "content"
    manager = BeatPackManager(content_dir)

    # Get retriever
    retriever = manager.get_retriever("mia_und_leo", "chapter_01")

    if not retriever:
        logger.error("Failed to load retriever")
        return

    # Test 1: Retrieve beats for first interaction (task distribution)
    print("\n--- Test 1: First interaction (5 tasks) ---")
    task_beats = retriever.get_beats_for_tasks(num_tasks=5)
    print(f"Selected {len(task_beats)} beats for 5 tasks:")
    for beat in task_beats:
        print(f"  Beat {beat.beat_id}: {beat.text[:60]}...")

    # Test 2: Retrieve beats based on query
    print("\n--- Test 2: Query-based retrieval ---")
    queries = [
        "Wer ist Leo?",
        "Was hat Mia gesammelt?",
        "Wo waren sie im Wald?",
        "Wie war der Abschied?"
    ]

    for query in queries:
        print(f"\nQuery: {query}")
        beats = retriever.retrieve_beats(query, top_k=3)
        print(f"Retrieved {len(beats)} beats:")
        for beat in beats:
            print(f"  Beat {beat.beat_id}: {beat.text[:60]}...")

    # Test 3: Format beats as context
    print("\n--- Test 3: Formatted context ---")
    beats = retriever.retrieve_beats("Mia und Leo im Wald", top_k=3)
    context = retriever.format_beats_for_context(beats, include_entities=True)
    print(context)

    print("\n" + "="*80)
    print("TESTING COMPLETE")
    print("="*80)


def test_beat_integrity():
    """Test beat integrity verification."""

    print("\n" + "="*80)
    print("TESTING BEAT INTEGRITY")
    print("="*80)

    content_dir = Path(__file__).parent / "content"
    beatpack_path = content_dir / "stories" / "mia_und_leo" / "chapter_01" / "beatpack.v1.json"

    if not beatpack_path.exists():
        logger.warning("Beatpack not found, creating it first...")
        create_example_beatpack()

    from beats import BeatPack
    beatpack = BeatPack.load(beatpack_path)

    is_valid, errors = beatpack.verify_integrity()

    if is_valid:
        print("✓ Beat integrity check PASSED")
        print(f"  All {len(beatpack.beats)} beats verified successfully")
    else:
        print("✗ Beat integrity check FAILED")
        for error in errors:
            print(f"  - {error}")

    print("="*80)


if __name__ == "__main__":
    print("BEAT SYSTEM TEST SUITE")
    print("="*80)

    # Run tests
    try:
        create_example_beatpack()
        test_beat_retrieval()
        test_beat_integrity()

        print("\n✓ All tests completed successfully!")

    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        print(f"\n✗ Test failed: {e}")


def test_list_available_stories(tmp_path):
    """Test that list_available_stories scans filesystem correctly."""
    stories_dir = tmp_path / "stories"
    # story_a has two chapter dirs, but only ch_01 has a beatpack
    (stories_dir / "story_a" / "ch_01").mkdir(parents=True)
    (stories_dir / "story_a" / "ch_01" / "beatpack.v1.json").write_text("{}")
    (stories_dir / "story_a" / "ch_02").mkdir(parents=True)
    # story_b has one chapter with a beatpack
    (stories_dir / "story_b" / "ch_01").mkdir(parents=True)
    (stories_dir / "story_b" / "ch_01" / "beatpack.v1.json").write_text("{}")

    manager = BeatPackManager(tmp_path)
    result = manager.list_available_stories()

    assert result == {
        "story_a": ["ch_01"],  # ch_02 excluded (no beatpack)
        "story_b": ["ch_01"],
    }


def test_list_available_stories_empty(tmp_path):
    """Test with no stories directory."""
    manager = BeatPackManager(tmp_path)
    assert manager.list_available_stories() == {}

