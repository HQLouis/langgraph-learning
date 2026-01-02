"""
Data loading functions for games and child profiles.
"""
from langgraph.prebuilt import InjectedState
import logging
import time
from typing import Annotated, Optional, Dict
from pathlib import Path
import sys

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from backend.core.config import get_settings
from states import State

class DataCache:
    """Simple in-memory cache with TTL support."""

    def __init__(self, ttl: int = 300):
        self._cache: Dict[str, tuple[str, float]] = {}
        self._ttl = ttl

    def get(self, key: str) -> Optional[str]:
        if key in self._cache:
            value, timestamp = self._cache[key]
            if time.time() - timestamp < self._ttl:
                logger.debug(f"Cache HIT for key: {key}")
                return value
            else:
                logger.debug(f"Cache EXPIRED for key: {key}")
                del self._cache[key]
        return None

    def set(self, key: str, value: str) -> None:
        self._cache[key] = (value, time.time())
        logger.debug(f"Cache SET for key: {key}")

    def clear(self) -> None:
        self._cache.clear()
        logger.info("Cache cleared")


class DataRepository:
    """Repository for managing data loading from S3 with fallback support."""

    _instance: Optional['DataRepository'] = None

    # Data file names mapping
    DATA_FILES = {
        'audio_book': 'audio_book.txt',
        'child_profile': 'child_profile.txt',
    }

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._settings = get_settings()
        self._cache = DataCache(ttl=self._settings.prompts_cache_ttl)
        self._s3_client = None
        self._initialized = True

        logger.info(f"DataRepository initialized with USE_S3_PROMPTS={self._settings.use_s3_prompts}")

    def _get_s3_client(self):
        if self._s3_client is not None:
            return self._s3_client

        if not self._settings.use_s3_prompts:
            logger.info("S3 data loading disabled via configuration")
            return None

        try:
            import boto3
            from botocore import UNSIGNED
            from botocore.config import Config

            if not self._settings.aws_s3_bucket_name:
                logger.warning("AWS_S3_BUCKET_NAME not configured, falling back to local data")
                return None

            # Create client with unsigned requests for public bucket access
            self._s3_client = boto3.client(
                's3',
                region_name=self._settings.aws_region,
                config=Config(signature_version=UNSIGNED)
            )

            logger.info(f"S3 client initialized for public bucket: {self._settings.aws_s3_bucket_name}")
            return self._s3_client

        except Exception as e:
            logger.error(f"Failed to initialize S3 client: {e}")
            return None


    def _fetch_from_s3(self, data_key: str, item_id: str) -> Optional[str]:
        s3_client = self._get_s3_client()
        if s3_client is None:
            return None

        if data_key not in self.DATA_FILES:
            logger.error(f"Unknown data key: {data_key}")
            return None

        file_name = self.DATA_FILES[data_key]
        # Changed: removed item_id from path
        s3_key = f"{self._settings.aws_s3_prompts_prefix}{file_name}"

        try:
            logger.info(f"Fetching data from S3: s3://{self._settings.aws_s3_bucket_name}/{s3_key}")

            response = s3_client.get_object(
                Bucket=self._settings.aws_s3_bucket_name,
                Key=s3_key
            )

            content = response['Body'].read().decode('utf-8')
            logger.info(f"Successfully fetched data from S3: {data_key} ({len(content)} bytes)")
            return content

        except s3_client.exceptions.NoSuchKey:
            logger.error(f"Data file not found in S3: {s3_key}")
            return None
        except Exception as e:
            logger.error(f"Error fetching data from S3: {e}")
            return None


    def get_data(self, data_key: str, item_id: str, fallback: str) -> str:
        cache_key = f"{data_key}"

        # Try cache first
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        # Try S3 if enabled
        if self._settings.use_s3_prompts:
            s3_content = self._fetch_from_s3(data_key, item_id)
            if s3_content is not None:
                self._cache.set(cache_key, s3_content)
                return s3_content
            logger.warning(f"Failed to fetch from S3, using fallback for: {cache_key}")

        # Return fallback
        logger.info(f"Using fallback data for: {cache_key}")
        return fallback


# Global repository instance
_data_repository = DataRepository()


def get_data_repository() -> DataRepository:
    """Get the global data repository instance."""
    return _data_repository

def get_audio_book_by_id(state: Annotated[State, InjectedState]) -> str:
    """
    Return the audio book whose ID lives in state['audio_book_id'].

    :param state: state containing audio_book_id
    :return: description of game
    """

    audio_book_id = state.get("audio_book_id", "0")
    fallback_content = {
        "0": "Du bist Lino, ein Teddybär und Erklärbär. Ein Erklärbar ist ganz schlau und kann Kindern ganz viele Sachen erklären. Immer wenn ein Kind eine Frage hat, kann das Kind mit der Frage zu dir kommen. Dann schaut ihr gemeinsam, ob ihr die Frage beantworten könnt.",
        "game-abc": "Der keine Drache Kokosnuss und der große Zauberer\n“"
                    "Kapitel 1\n"
                    "\n"
                    "Begegnung im Klippenwald\n"
                    "\n"
                    "Einmal im Jahr, wenn es Herbst wird auf der Dracheninsel und die Blätter der Bäume sich rot und gelb färben, gehen Kokosnuss und Matilda in den Klippenwald, um Pilze zu suchen. Heute sammeln sie den ganzen Tag über, bis ihre Körbe bis obenhin gefüllt sind mit den herrlichsten Pilzen. Gerade wollen sie sich auf den Rückweg machen, da hält Matilda ihre Nase in die Luft und schnüffelt.\n"
                    "»Was schnüffelst du denn?«, fragt Kokosnuss.\n"
                    "»Ich rieche Ziege«, antwortet Matilda.\n"
                    "Kokosnuss grinst: »Was ist denn mit deiner Nase los? Im Klippenwald gibt’s doch keine Ziegen!«\n"
                    "Matilda aber lässt ihren Korb stehen und marschiert in Richtung Ziegengeruch.\n"
                    "»Warte auf mich!«, ruft Kokosnuss.\n"
                    "Bald steigt auch ihm Ziegengeruch in die Nase. Die beiden bleiben wie angewurzelt stehen.\n"
                    "»Gibt’s ja nicht!«, flüstert Kokosnuss. »Eine echte Ziege, hier im Klippenwald!«\n"
                    "Durch ein paar Büsche hindurch sehen sie eine weiße Ziege, die verzweifelt versucht, eine Flasche zu öffnen. Die Flasche steckt im Wurzelwerk eines mächtigen Baumes.\n"
                    "»Verflixt noch mal!«, flucht die Ziege. »Dieser blöde Korken, diese bescheuerten Ziegenfüße!«\n"
                    "Kokosnuss und Matilda treten hinter dem Busch hervor: »Können wir dir helfen?«\n"
                    "Vor Schreck fällt die Ziege auf ihren Ziegenpopo: »Äh, wo kommt ihr denn her?«\n"
                    "»Vom Pilzesuchen«, antwortet Matilda. »Und wo kommst du her?«\n"
                    "Die Ziege mustert erst den jungen Feuerdrachen und dann das kleine Stachelschwein. Verstohlen blickt sie sich um.\n"
                    "»Könnt ihr ein Geheimnis für euch behalten?«\n"
                    "»Können wir.«\n"
                    "Ich bin in Wirklichkeit keine Ziege, sondern ein großer Zauberer.«\n"
                    "Kokosnuss und Matilda blicken sich an. Dann brechen sie in schallendes Gelächter aus. Sie müssen so lachen, dass sie sich am Waldboden kugeln.\n"
                    "Die Ziege ist empört: »Wenn ihr mir nicht glaubt, dann erzähle ich euch überhaupt nichts!«\n"
                    "Kokosnuss betrachtet die Ziege. Plötzlich kriegt er einen Schreck: »Bist du etwa der Zauberer Ziegenbart?«\n"
                    "»Ziegenbart? Bei allen Magiern des Erdkreises, ich doch nicht! Ich bin Holunder, Herr über das Flaschenland.\n"
                    "»Das Flaschenland?«\n"
                    "Da deutet die Ziege auf die Flasche: »Wenn ihr ganz genau hineinschaut, dann könnt ihr das Flaschenland sehen.«\n"
                    "Kokosnuss und Matilda blicken durch das grüne Glas ins Innere der Flasche. Und tatsächlich, wenn sie ganz nah heranrücken, erkennen sie, was die Ziege meint: ein winziges Land in einer Flasche!\n"
                    "»Bitte«, sagt Kokosnuss, »erzähl uns dein Geheimnis!«"
    }.get(audio_book_id, "This is an open world game. You can do anything you want.")
    repository = get_data_repository()
    return repository.get_data('audio_book', audio_book_id, fallback_content)


def get_child_profile(state: Annotated[State, InjectedState]) -> str:
    """
    Return the profile of the child whose ID lives in state['child_id'].

    :param state: state containing child_id
    :return: profile of child
    """
    child_id = state.get("child_id", "1")
    fallback_profile = {
        "1": "Das Kind ist 5 Jahre alt, mag Dinosaurier und Raketen. Es lernt gerade lesen und schreiben.",
        "2": "Das Kind ist 8 Jahre alt, mag Fussball und Videospiele. Es liest gerne Abenteuerbücher.",
        "3": "Das Kind ist 10 Jahre alt, mag Programmieren und Robotik. Es liest gerne Science-Fiction-Bücher.",
        "child-123": "Das Kind ist 7 Jahre alt, liebt Tiere und Natur. Es interessiert sich für Umweltschutz und liest gerne Sachbücher über Tiere.",
    }.get(child_id, "This is a child with no specific profile.")
    repository = get_data_repository()
    return repository.get_data('child_profile', child_id, fallback_profile)
