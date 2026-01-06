"""Book Image Generator CLI - Generate visualizations of book pages."""

import mimetypes
import os
import re
from datetime import datetime

import click
from dotenv import load_dotenv
from google import genai
from google.genai import types

from keywords import extract_keywords
from presets import load_preset, get_preset_components

# Load environment variables from .env file
load_dotenv()


# Supported aspect ratios and sizes for Gemini API
SUPPORTED_ASPECT_RATIOS = ["1:1", "2:3", "3:2", "3:4", "4:3", "4:5", "16:9"]
SUPPORTED_SIZES = ["1K", "2K", "4K"]


def validate_aspect_ratio(ctx, param, value):
    """Validate aspect ratio is supported by Gemini API."""
    if value not in SUPPORTED_ASPECT_RATIOS:
        valid_options = ", ".join(SUPPORTED_ASPECT_RATIOS)
        raise click.BadParameter(
            f"Invalid aspect ratio '{value}'. Must be one of: {valid_options}"
        )
    return value


def validate_image_size(ctx, param, value):
    """Validate image size is supported by Gemini API."""
    if value not in SUPPORTED_SIZES:
        valid_options = ", ".join(SUPPORTED_SIZES)
        raise click.BadParameter(
            f"Invalid image size '{value}'. Must be one of: {valid_options}"
        )
    return value


def sanitize_title(title: str) -> str:
    """Sanitize book title for use in filename."""
    # Convert to lowercase
    title = title.lower()
    # Replace spaces and special characters with underscores
    title = re.sub(r"[^a-z0-9]+", "_", title)
    # Remove leading/trailing underscores
    title = title.strip("_")
    return title


def generate_filename_base(book_title: str) -> str:
    """
    Generate base output filename (without extension) from book title and timestamp.

    Args:
        book_title: The book title

    Returns:
        Base filename: {sanitized_title}_{timestamp}
    """
    sanitized = sanitize_title(book_title)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{sanitized}_{timestamp}"


def build_prompt(
    book_title: str,
    text_content: str,
    preset_components: dict,
    keywords: list,
) -> str:
    """
    Build descriptive narrative prompt from book title, text, preset, and keywords.

    Args:
        book_title: The book title
        text_content: Text content from the book page
        preset_components: Dictionary with base, lighting, color_palette, camera
        keywords: List of extracted keywords

    Returns:
        Narrative prompt string
    """
    # Start with book context
    prompt_parts = [f"Based on '{book_title}'"]

    # Add keywords context naturally
    if keywords:
        keywords_text = ", ".join(keywords[:10])  # Limit to first 10 keywords
        prompt_parts.append(f"with themes of {keywords_text}")

    # Add text content descriptively
    if text_content.strip():
        # Include the full text content
        text_snippet = text_content.strip()
        prompt_parts.append(f"The scene depicts: {text_snippet}")

    # Apply preset style guidelines
    style_parts = []
    if preset_components.get("base"):
        style_parts.append(preset_components["base"])
    if preset_components.get("lighting"):
        style_parts.append(f"lighting: {preset_components['lighting']}")
    if preset_components.get("color_palette"):
        style_parts.append(f"color palette: {preset_components['color_palette']}")
    if preset_components.get("accents"):
        style_parts.append(f"accents: {preset_components['accents']}")
    if preset_components.get("camera"):
        style_parts.append(f"camera: {preset_components['camera']}")

    if style_parts:
        prompt_parts.append(" ".join(style_parts))

    # Combine into narrative paragraph
    prompt = ". ".join(prompt_parts) + "."

    return prompt


def build_system_instruction(preset_components: dict) -> str:
    """
    Build system instruction from preset components for style context.

    Args:
        preset_components: Dictionary with base, lighting, color_palette, camera

    Returns:
        System instruction string
    """
    parts = []

    if preset_components.get("base"):
        parts.append(preset_components["base"])

    if preset_components.get("lighting"):
        parts.append(f"Use {preset_components['lighting']}")

    if preset_components.get("color_palette"):
        parts.append(f"Apply {preset_components['color_palette']}")

    if preset_components.get("accents"):
        parts.append(f"Include accents of {preset_components['accents']}")

    if preset_components.get("camera"):
        parts.append(f"Frame as {preset_components['camera']}")

    if parts:
        return ". ".join(parts) + "."

    return "Create a visually compelling illustration that captures the essence of the scene."


@click.group()
def cli():
    """Book Image Generator - Generate visualizations of book pages."""
    pass


@cli.command()
@click.option(
    "--title",
    required=True,
    help="Book title",
)
@click.option(
    "--text-file",
    required=True,
    type=click.Path(exists=True, readable=True),
    help="Path to text content file",
)
@click.option(
    "--style",
    default="watercolor",
    help="Preset style name (default: watercolor)",
)
@click.option(
    "--skip-keywords",
    is_flag=True,
    help="Skip keyword extraction step",
)
@click.option(
    "--aspect-ratio",
    default="3:4",
    callback=validate_aspect_ratio,
    help="Image aspect ratio. Supported: 1:1, 2:3, 3:2, 3:4, 4:3, 4:5, 16:9 (default: 3:4)",
)
@click.option(
    "--size",
    default="1K",
    callback=validate_image_size,
    help="Image size. Supported: 1K, 2K, 4K (default: 1K)",
)
def generate(
    title: str,
    text_file: str,
    style: str,
    skip_keywords: bool,
    aspect_ratio: str,
    size: str,
):
    """Generate an image visualization for a book page."""

    # Load API key
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        click.echo(
            "Error: GEMINI_API_KEY not found in environment or .env file", err=True
        )
        return

    # Load preset
    try:
        preset = load_preset(style)
        preset_components = get_preset_components(preset)
    except FileNotFoundError as e:
        click.echo(f"Error: {e}", err=True)
        return
    except Exception as e:
        click.echo(f"Error loading preset: {e}", err=True)
        return

    # Read text file
    try:
        with open(text_file, "r", encoding="utf-8") as f:
            text_content = f.read()
    except Exception as e:
        click.echo(f"Error reading text file: {e}", err=True)
        return

    # Extract keywords (unless skipped)
    keywords = []
    if not skip_keywords:
        click.echo("Extracting keywords from book title...")
        try:
            keywords = extract_keywords(title, api_key)
            if keywords:
                click.echo(f"Extracted {len(keywords)} keywords:")
                for keyword in keywords[:10]:  # Show first 10
                    click.echo(f"  - {keyword}")
                if len(keywords) > 10:
                    click.echo(f"  ... and {len(keywords) - 10} more")
            else:
                click.echo("No keywords extracted (continuing anyway)")
        except Exception as e:
            click.echo(f"Warning: Keyword extraction failed: {e}", err=True)
            click.echo("Continuing without keywords...")

    # Build prompt
    prompt = build_prompt(title, text_content, preset_components, keywords)
    system_instruction = build_system_instruction(preset_components)

    # Display prompt for confirmation
    click.echo("\n" + "=" * 80)
    click.echo("PROMPT PREVIEW")
    click.echo("=" * 80)
    click.echo("\nImage Configuration:")
    click.echo(f"  Aspect Ratio: {aspect_ratio}")
    click.echo(f"  Size: {size}")
    click.echo(f"\nSystem Instruction:\n{system_instruction}\n")
    click.echo(f"Main Prompt:\n{prompt}\n")
    click.echo("=" * 80)

    # Generate base filename (extension will be determined from API response)
    filename_base = generate_filename_base(title)
    click.echo(
        f"\nOutput filename base: {filename_base} (extension will be determined from API)\n"
    )

    # Confirm with user
    if not click.confirm("Do you want to proceed with image generation?"):
        click.echo("Image generation cancelled.")
        return

    # Initialize Gemini client
    client = genai.Client(api_key=api_key)

    # Generate image
    click.echo("\nGenerating image...")
    try:
        contents = [
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=prompt)],
            ),
        ]

        generate_content_config = types.GenerateContentConfig(
            response_modalities=["IMAGE", "TEXT"],
            image_config=types.ImageConfig(
                aspect_ratio=aspect_ratio,
                image_size=size,
            ),
            system_instruction=[types.Part.from_text(text=system_instruction)],
        )

        file_index = 0
        saved_files = []

        for chunk in client.models.generate_content_stream(
            model="gemini-3-pro-image-preview",
            contents=contents,
            config=generate_content_config,
        ):
            if (
                chunk.candidates is None
                or chunk.candidates[0].content is None
                or chunk.candidates[0].content.parts is None
            ):
                continue

            part = chunk.candidates[0].content.parts[0]

            # Handle image data
            if part.inline_data and part.inline_data.data:
                inline_data = part.inline_data
                data_buffer = inline_data.data
                file_extension = (
                    mimetypes.guess_extension(inline_data.mime_type) or ".png"
                )

                # Generate filename with index if multiple images
                if file_index > 0:
                    output_filename = f"{filename_base}_{file_index}{file_extension}"
                else:
                    output_filename = f"{filename_base}{file_extension}"

                # Save binary file
                with open(output_filename, "wb") as f:
                    f.write(data_buffer)

                saved_files.append(output_filename)
                click.echo(f"Image saved: {output_filename}")
                file_index += 1

            # Handle text responses
            elif hasattr(part, "text") and part.text:
                click.echo(f"Response: {part.text}")

        if saved_files:
            click.echo(f"\nSuccess! Generated {len(saved_files)} image(s):")
            for f in saved_files:
                click.echo(f"  - {f}")
        else:
            click.echo("Warning: No images were generated", err=True)

    except Exception as e:
        click.echo(f"Error generating image: {e}", err=True)
        raise


if __name__ == "__main__":
    cli()
