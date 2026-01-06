"""Preset loading and parsing logic for book image generation styles."""

import os
import yaml
from pathlib import Path
from typing import Dict, Optional


def load_preset(style_name: str, presets_dir: str = "presets") -> Dict:
    """
    Load and parse a preset YAML file from the presets directory.

    Args:
        style_name: Name of the preset style. Can be:
            - Just the name: "gulag_winter_realism"
            - With extension: "gulag_winter_realism.yaml"
            - With path: "presets/gulag_winter_realism.yaml"
        presets_dir: Directory containing preset files (default: "presets")

    Returns:
        Dictionary containing preset data with keys: name, prompt (base, lighting, color_palette, camera)

    Raises:
        FileNotFoundError: If preset file doesn't exist
        yaml.YAMLError: If preset file is invalid YAML
    """
    # Normalize the style_name: remove path and extension
    style_path = Path(style_name)

    # If the input is a direct file path that exists, use it
    if style_path.exists() and style_path.is_file():
        preset_path = style_path
    else:
        # Otherwise, treat it as a style name and look in presets_dir
        # Remove .yaml extension if present, and remove any directory path
        normalized_name = style_path.stem
        preset_path = Path(presets_dir) / f"{normalized_name}.yaml"

        if not preset_path.exists():
            raise FileNotFoundError(f"Preset file not found: {preset_path}")

    with open(preset_path, "r", encoding="utf-8") as f:
        preset_data = yaml.safe_load(f)

    if not preset_data:
        raise ValueError(f"Preset file is empty: {preset_path}")

    # Validate structure
    if "name" not in preset_data:
        raise ValueError(f"Preset missing 'name' field: {preset_path}")

    if "prompt" not in preset_data:
        raise ValueError(f"Preset missing 'prompt' field: {preset_path}")

    return preset_data


def get_preset_components(preset: Dict) -> Dict[str, str]:
    """
    Extract prompt components from a preset dictionary.

    Args:
        preset: Preset dictionary from load_preset()

    Returns:
        Dictionary with keys: base, lighting, color_palette, camera, accents
        Missing components will have empty string values
    """
    prompt = preset.get("prompt", {})

    # Handle color_palette as either string or list
    color_palette = prompt.get("color_palette", "")
    if isinstance(color_palette, list):
        color_palette = ", ".join(str(item) for item in color_palette)
    else:
        color_palette = str(color_palette) if color_palette else ""

    # Handle accents as either string or list
    accents = prompt.get("accents", "")
    if isinstance(accents, list):
        accents = ", ".join(str(item) for item in accents)
    else:
        accents = str(accents) if accents else ""

    return {
        "base": prompt.get("base", "").strip(),
        "lighting": prompt.get("lighting", "").strip(),
        "color_palette": color_palette.strip(),
        "camera": prompt.get("camera", "").strip(),
        "accents": accents.strip(),
    }
