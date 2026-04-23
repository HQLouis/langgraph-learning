"""
Single entry point for the Phase-0 pipelines.

Run with::

    PYTHONPATH=tests/feature-testing python -m _pipelines.run

It:
1. Parses ``Dialogbeispiele für die Eigenschaften.md`` once.
2. Writes ``_registry/examples.jsonl`` (Pipeline A).
3. Writes ``_registry/requirements.yaml`` (Pipeline B, draft-only entries).
4. Writes ``_registry/extraction_log.md`` (diff vs previously-committed files).

The script is idempotent. Re-running on an unchanged MD produces byte-
stable artefacts (except ``generated_at`` timestamps — see
``--stable-timestamps`` to suppress them for tests).
"""

from __future__ import annotations

import argparse
import logging
import shutil
import tempfile
from pathlib import Path

from _pipelines.extract_examples import build_subexamples, write_examples_jsonl
from _pipelines.extract_requirements import build_requirements, write_requirements_yaml
from _pipelines.parse_dialogbeispiele import parse_markdown
from _pipelines.regen_diff import write_diff_report

logger = logging.getLogger(__name__)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    parser = argparse.ArgumentParser(description="Run all Phase-0 pipelines against the Dialogbeispiele MD.")
    parser.add_argument(
        "--md",
        default="tests/feature-testing/Dialogbeispiele für die Eigenschaften.md",
    )
    parser.add_argument(
        "--registry",
        default="tests/feature-testing/_registry",
        help="Directory that holds examples.jsonl, requirements.yaml, extraction_log.md",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse and compute diffs but do not overwrite the committed artefacts.",
    )
    args = parser.parse_args()

    md_path = Path(args.md)
    registry_dir = Path(args.registry)
    examples_path = registry_dir / "examples.jsonl"
    requirements_path = registry_dir / "requirements.yaml"
    log_path = registry_dir / "extraction_log.md"

    logger.info("parsing %s", md_path)
    eigenschaften, report = parse_markdown(md_path)
    logger.info(
        "parsed %d Eigenschaften, %d Beispiele, %d turns, %d warnings",
        report.eigenschaft_count,
        report.beispiel_count,
        report.turn_count,
        len(report.warnings),
    )
    for w in report.warnings[:10]:
        logger.warning("  - %s", w)

    subexamples, skip_reasons = build_subexamples(eigenschaften)
    requirements = build_requirements(eigenschaften)
    logger.info(
        "produced %d SubExamples (%d skipped), %d Requirements",
        len(subexamples),
        len(skip_reasons),
        len(requirements),
    )

    # Write new artefacts to a temp location so the diff step can compare
    # against the committed state without racing.
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        tmp_examples = tmp / "examples.jsonl"
        tmp_requirements = tmp / "requirements.yaml"
        write_examples_jsonl(subexamples, tmp_examples)
        write_requirements_yaml(requirements, tmp_requirements)

        ex_diff, rq_diff = write_diff_report(
            examples_path=examples_path,
            examples_new_path=tmp_examples,
            requirements_path=requirements_path,
            requirements_new_path=tmp_requirements,
            log_path=log_path if not args.dry_run else (tmp / "extraction_log.md"),
        )
        logger.info(
            "diff — examples: +%d / -%d / ~%d   requirements: +%d / -%d / ~%d",
            len(ex_diff.added_ids), len(ex_diff.removed_ids), len(ex_diff.modified_ids),
            len(rq_diff.added_ids), len(rq_diff.removed_ids), len(rq_diff.modified_ids),
        )

        if args.dry_run:
            logger.info("dry-run: leaving %s untouched", registry_dir)
            return

        registry_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(tmp_examples, examples_path)
        shutil.copy2(tmp_requirements, requirements_path)
        logger.info("wrote %s", examples_path)
        logger.info("wrote %s", requirements_path)
        logger.info("wrote %s", log_path)


if __name__ == "__main__":
    main()
