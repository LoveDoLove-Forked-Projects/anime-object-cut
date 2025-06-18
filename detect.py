from pathlib import Path
from imgutils import detect


def head(
    img_path: Path,
) -> list[tuple[tuple[int, int, int, int], str, float]] | None:
    results = detect.detect_heads(img_path)
    if not results:
        return None
    return results


def eyes(
    img_path: Path,
) -> list[tuple[tuple[int, int, int, int], str, float]] | None:
    results = detect.detect_eyes(img_path)
    if not results:
        return None
    return results


def faces(
    img_path: Path,
) -> list[tuple[tuple[int, int, int, int], str, float]] | None:
    results = detect.detect_faces(img_path)
    if not results:
        return None
    return results


def censors(
    img_path: Path,
) -> list[tuple[tuple[int, int, int, int], str, float]] | None:
    results = detect.detect_censors(img_path)
    if not results:
        return None
    return results


def nudenet(
    img_path: Path,
) -> list[tuple[tuple[int, int, int, int], str, float]] | None:
    results = detect.detect_with_nudenet(img_path)
    if not results:
        return None
    """
all_labels = [
    "FEMALE_GENITALIA_COVERED",
    "FACE_FEMALE",
    "BUTTOCKS_EXPOSED",
    "FEMALE_BREAST_EXPOSED",
    "FEMALE_GENITALIA_EXPOSED",
    "MALE_BREAST_EXPOSED",
    "ANUS_EXPOSED",
    "FEET_EXPOSED",
    "BELLY_COVERED",
    "FEET_COVERED",
    "ARMPITS_COVERED",
    "ARMPITS_EXPOSED",
    "FACE_MALE",
    "BELLY_EXPOSED",
    "MALE_GENITALIA_EXPOSED",
    "ANUS_COVERED",
    "FEMALE_BREAST_COVERED",
    "BUTTOCKS_COVERED",
]
    """
    return results


def nudenet_mongo(
    img_path: Path,
) -> list[tuple[tuple[int, int, int, int], str, float]] | None:
    results = detect.detect_with_nudenet(img_path)
    if not results:
        return None
    return [result for result in results if result[1].startswith("FEMALE_GENITALIA")]


def nudenet_opai(
    img_path: Path,
) -> list[tuple[tuple[int, int, int, int], str, float]] | None:
    results = detect.detect_with_nudenet(img_path)
    if not results:
        return None
    return [result for result in results if result[1].startswith("FEMALE_BREAST")]


def nudenet_armpits(
    img_path: Path,
) -> list[tuple[tuple[int, int, int, int], str, float]] | None:
    results = detect.detect_with_nudenet(img_path)
    if not results:
        return None
    return [result for result in results if result[1].startswith("ARMPITS")]


def nudenet_feet(
    img_path: Path,
) -> list[tuple[tuple[int, int, int, int], str, float]] | None:
    results = detect.detect_with_nudenet(img_path)
    if not results:
        return None
    return [result for result in results if result[1].startswith("FEET")]
