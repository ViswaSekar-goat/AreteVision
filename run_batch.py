import argparse
import uuid
from pathlib import Path

from app.graph import graph
from app.database import image_already_inspected


# --------------------------------------------------
# 1. CONFIGURATION
# --------------------------------------------------

SUPPORTED_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".bmp",
    ".webp",
    ".tif",
    ".tiff",
}


# --------------------------------------------------
# 2. FIND ALL IMAGES
# --------------------------------------------------

def find_images(folder: Path) -> list[Path]:
    """Recursively find supported image files."""

    if not folder.exists():
        raise FileNotFoundError(
            f"Dataset folder does not exist: {folder}"
        )

    if not folder.is_dir():
        raise NotADirectoryError(
            f"Expected a directory: {folder}"
        )

    images = sorted(
        path.resolve()
        for path in folder.rglob("*")
        if path.is_file()
        and path.suffix.lower() in SUPPORTED_EXTENSIONS
    )

    return images


# --------------------------------------------------
# 3. INSPECT ONE IMAGE
# --------------------------------------------------

def inspect_image(image_path: Path, index: int, total: int):
    """Run the existing ForgeSight graph for one image."""

    # Every image gets its own workflow thread.
    thread_id = str(uuid.uuid4())

    config = {
        "configurable": {
            "thread_id": thread_id,
        }
    }

    initial_state = {
        "image_path": str(image_path),
        "thread_id": thread_id,
        "detections": [],
        "inspection_history": [],
        "inspection_id": "",
        "defect_analysis": {},
        "quality_assessment": {},
        "decision": {},
        "policy_decision": {},
        "pattern_analysis": {},
    }

    print("\n" + "=" * 65)
    print(f"[{index}/{total}] Inspecting: {image_path.name}")
    print(f"Path: {image_path}")
    print("=" * 65)

        # Skip images that already exist in MySQL.
    try:
        if image_already_inspected(str(image_path)):
            print("Status: SKIPPED — already inspected in MySQL")

            return {
                "image": str(image_path),
                "inspection_id": None,
                "thread_id": None,
                "status": "SKIPPED",
                "error": None,
            }

    except Exception as error:
        # Stop rather than risk processing duplicates when
        # the database check cannot be completed.
        print(f"Database check failed: {error}")
        raise

    try:
        result = graph.invoke(
            initial_state,
            config=config,
        )

        inspection_id = result.get("inspection_id", "Unknown")

        # Human review required: leave this workflow paused.
        if result.get("__interrupt__"):
            print("Status: PENDING HUMAN REVIEW")
            print(f"Inspection ID: {inspection_id}")
            print(f"Thread ID: {thread_id}")
            print("Review this inspection in the ForgeSight dashboard.")

            return {
                "image": str(image_path),
                "inspection_id": inspection_id,
                "thread_id": thread_id,
                "status": "PENDING HUMAN REVIEW",
                "error": None,
            }

        # The graph completed without requiring human review.
        policy_decision = result.get("policy_decision", {})
        action = policy_decision.get("action", "UNKNOWN")

        print(f"Status: COMPLETED")
        print(f"Inspection ID: {inspection_id}")
        print(f"Policy decision: {action}")
        print(f"Detections: {len(result.get('detections', []))}")

        return {
            "image": str(image_path),
            "inspection_id": inspection_id,
            "thread_id": thread_id,
            "status": action,
            "error": None,
        }

    except Exception as error:
        # Log the failure and continue to the next image.
        print(f"ERROR processing {image_path.name}: {error}")

        return {
            "image": str(image_path),
            "inspection_id": None,
            "thread_id": thread_id,
            "status": "ERROR",
            "error": str(error),
        }


# --------------------------------------------------
# 4. PROCESS THE ENTIRE DATASET
# --------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Run ForgeSight on every image in a folder."
    )

    parser.add_argument(
        "--folder",
        type=Path,
        default=Path("data/NEU-DET/train/images"),
        help="Folder containing images, including nested folders.",
    )

    args = parser.parse_args()

    image_folder = args.folder.resolve()

    print("\nForgeSight Batch Inspection")
    print(f"Dataset folder: {image_folder}")

    images = find_images(image_folder)

    if not images:
        print("No supported images found.")
        return

    total = len(images)

    print(f"Images found: {total}")
    print("Starting inspections...\n")

    results = []

    for index, image_path in enumerate(images, start=1):
        result = inspect_image(
            image_path=image_path,
            index=index,
            total=total,
        )

        results.append(result)

    # --------------------------------------------------
    # 5. FINAL SUMMARY
    # --------------------------------------------------

    completed = sum(
        result["status"] in {"ACCEPT", "REJECT"}
        for result in results
    )

    pending = sum(
        result["status"] == "PENDING HUMAN REVIEW"
        for result in results
    )

    skipped = sum(
        result["status"] == "SKIPPED"
        for result in results
    )

    failed = sum(
        result["status"] == "ERROR"
        for result in results
    )

    print("\n" + "=" * 65)
    print("BATCH INSPECTION SUMMARY")
    print("=" * 65)
    print(f"Total images:       {total}")
    print(f"Completed:          {completed}")
    print(f"Pending review:     {pending}")
    print(f"Skipped:            {skipped}")
    print(f"Failed:             {failed}")
    print("=" * 65)

    if failed:
        print("\nImages that failed:")
        for result in results:
            if result["status"] == "ERROR":
                print(f"- {result['image']}: {result['error']}")

    print("\nOpen the ForgeSight dashboard to review pending inspections.")


if __name__ == "__main__":
    main()