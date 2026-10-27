import argparse
import csv
import json
import random
from collections import Counter
from pathlib import Path

from ultralytics import YOLO


# ============================================================
# 1. CONFIGURATION
# ============================================================

LOW_CONFIDENCE = 0.50
HIGH_CONFIDENCE = 0.75

IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".bmp",
    ".webp",
    ".tif",
    ".tiff",
}


# ============================================================
# 2. CLASSIFY EACH IMAGE
# ============================================================

def classify_image(detections):
    """
    Categorize an image according to its highest detection
    confidence.

    Categories:
        no_detections
        low_confidence
        medium_confidence
        high_confidence
    """

    if not detections:
        return "no_detections"

    max_confidence = max(
        detection["confidence"]
        for detection in detections
    )

    if max_confidence < LOW_CONFIDENCE:
        return "low_confidence"

    if max_confidence < HIGH_CONFIDENCE:
        return "medium_confidence"

    return "high_confidence"


# ============================================================
# 3. SIMULATE THE CURRENT FORGESIGHT ROUTER AND POLICY
# ============================================================

def simulate_forgesight_decision(detections):
    """
    Mirror the routing and policy rules currently discussed
    for ForgeSight.

    This does not execute LangGraph or modify MySQL.
    """

    if not detections:
        return "fast_path", "ACCEPT"

    confidences = [
        detection["confidence"]
        for detection in detections
    ]

    # Match route_after_vision()
    if all(
        confidence >= HIGH_CONFIDENCE
        for confidence in confidences
    ):
        route = "fast_path"
    else:
        route = "agentic_path"

    # Match policy_engine_node()
    # The low-confidence check occurs before the high-confidence
    # rejection check in the current implementation.
    if any(
        confidence < LOW_CONFIDENCE
        for confidence in confidences
    ):
        action = "HUMAN_REVIEW"

    elif any(
        confidence >= HIGH_CONFIDENCE
        for confidence in confidences
    ):
        action = "REJECT"

    else:
        action = "HUMAN_REVIEW"

    return route, action


# ============================================================
# 4. EXTRACT DETECTIONS FROM YOLO RESULTS
# ============================================================

def extract_detections(result):
    """
    Convert YOLO's output into ordinary Python dictionaries.
    """

    detections = []

    if result.boxes is None:
        return detections

    for box in result.boxes:
        class_id = int(box.cls.item())
        confidence = float(box.conf.item())

        coordinates = [
            float(value)
            for value in box.xyxy[0].tolist()
        ]

        detections.append({
            "class_name": result.names[class_id],
            "confidence": round(confidence, 6),
            "bbox": coordinates,
        })

    return detections


# ============================================================
# 5. MAIN DATASET ANALYSIS
# ============================================================

def main():

    parser = argparse.ArgumentParser(
        description=(
            "Run ForgeSight YOLO over a dataset and collect "
            "representative images by detection confidence."
        )
    )

    parser.add_argument(
        "--model",
        default="models/forgeSight_yolo.pt",
        help="Path to trained YOLO weights.",
    )

    parser.add_argument(
        "--dataset",
        required=True,
        help="Dataset directory containing images.",
    )

    parser.add_argument(
        "--output",
        default="outputs/confidence_analysis",
        help="Directory for reports and sample images.",
    )

    parser.add_argument(
        "--samples-per-category",
        type=int,
        default=10,
        help="Maximum number of annotated samples per category.",
    )

    parser.add_argument(
        "--inference-conf",
        type=float,
        default=0.001,
        help="YOLO detection threshold during inference.",
    )

    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducible sample selection.",
    )

    parser.add_argument(
        "--device",
        default=None,
        help="Inference device, e.g. 0 for GPU or cpu for CPU.",
    )

    args = parser.parse_args()

    if args.samples_per_category < 1:
        parser.error("--samples-per-category must be at least 1.")

    if not 0 < args.inference_conf < 1:
        parser.error("--inference-conf must be between 0 and 1.")

    model_path = Path(args.model).resolve()
    dataset_dir = Path(args.dataset).resolve()
    output_dir = Path(args.output).resolve()

    if not model_path.is_file():
        parser.error(f"Model weights not found: {model_path}")

    if not dataset_dir.is_dir():
        parser.error(f"Dataset directory not found: {dataset_dir}")

    if output_dir == dataset_dir or output_dir in dataset_dir.parents:
        parser.error(
            "Choose an output directory outside the dataset directory."
        )

    output_dir.mkdir(parents=True, exist_ok=True)

    # --------------------------------------------------------
    # Find all supported images recursively.
    # --------------------------------------------------------

    images = [
        path
        for path in dataset_dir.rglob("*")
        if path.is_file()
        and path.suffix.lower() in IMAGE_EXTENSIONS
        and output_dir not in path.resolve().parents
    ]

    if not images:
        parser.error(f"No supported images found in {dataset_dir}")

    # Shuffle before inference so samples are not simply
    # the first images in filesystem order.
    images.sort()
    random.Random(args.seed).shuffle(images)

    print(f"\nDataset: {dataset_dir}")
    print(f"Model:   {model_path}")
    print(f"Images:  {len(images)}")
    print(f"Output:  {output_dir}\n")

    # --------------------------------------------------------
    # Load the trained YOLO model.
    # --------------------------------------------------------

    model = YOLO(str(model_path))

    categories = [
        "no_detections",
        "low_confidence",
        "medium_confidence",
        "high_confidence",
    ]

    counts = Counter()
    sample_counts = Counter()
    csv_rows = []

    sample_dir = output_dir / "samples"

    for category in categories:
        (sample_dir / category).mkdir(
            parents=True,
            exist_ok=True,
        )

    # --------------------------------------------------------
    # Run inference on every image.
    # --------------------------------------------------------

    for index, image_path in enumerate(images, start=1):

        prediction_args = {
            "source": str(image_path),
            "conf": args.inference_conf,
            "verbose": False,
        }

        if args.device is not None:
            prediction_args["device"] = args.device

        results = model.predict(**prediction_args)
        result = results[0]

        detections = extract_detections(result)

        category = classify_image(detections)
        route, action = simulate_forgesight_decision(detections)

        counts[category] += 1

        confidences = [
            detection["confidence"]
            for detection in detections
        ]

        max_confidence = (
            max(confidences)
            if confidences
            else None
        )

        # Store every image in the CSV, even if it is not
        # selected as a presentation sample.
        csv_rows.append({
            "image_path": str(image_path),
            "category": category,
            "detection_count": len(detections),
            "max_confidence": max_confidence,
            "all_confidences": json.dumps(confidences),
            "detections": json.dumps(detections),
            "simulated_route": route,
            "simulated_policy_action": action,
        })

        # Save a limited number of annotated samples per category.
        # Save original images without annotations.
        if sample_counts[category] < args.samples_per_category:

            relative_path = image_path.relative_to(dataset_dir)

            output_name = "__".join(relative_path.parts)

            sample_path = (
                sample_dir
                / category
                / f"{output_name}"
            )

            # Copy the original image without drawing bounding boxes.
            import shutil
            shutil.copy2(image_path, sample_path)

            sample_counts[category] += 1

        if index % 25 == 0 or index == len(images):
            print(
                f"Processed {index}/{len(images)} images"
            )

    # --------------------------------------------------------
    # Save the complete CSV report.
    # --------------------------------------------------------

    csv_path = output_dir / "dataset_analysis.csv"

    fieldnames = [
        "image_path",
        "category",
        "detection_count",
        "max_confidence",
        "all_confidences",
        "detections",
        "simulated_route",
        "simulated_policy_action",
    ]

    with csv_path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
        )

        writer.writeheader()
        writer.writerows(csv_rows)

    # --------------------------------------------------------
    # Print the summary.
    # --------------------------------------------------------

    print("\n" + "=" * 60)
    print("FORGESIGHT DATASET CONFIDENCE ANALYSIS")
    print("=" * 60)

    print(f"Total images analysed: {len(images)}\n")

    for category in categories:
        print(
            f"{category:20s}: "
            f"{counts[category]:5d} images | "
            f"{sample_counts[category]:2d} samples saved"
        )

    print("\nConfidence thresholds:")
    print(f"  Low:    max confidence < {LOW_CONFIDENCE}")
    print(
        f"  Medium: {LOW_CONFIDENCE} <= max confidence "
        f"< {HIGH_CONFIDENCE}"
    )
    print(f"  High:   max confidence >= {HIGH_CONFIDENCE}")

    print("\nOutput files:")
    print(f"  CSV report: {csv_path}")
    print(f"  Samples:    {sample_dir}")

    print("\nAnalysis completed.")


if __name__ == "__main__":
    main()