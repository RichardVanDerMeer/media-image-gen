"""Media Image Generator CLI - Generate visualizations for books, films, and music tracks."""

import mimetypes
import os
import re
from datetime import datetime

import click
import questionary
from dotenv import load_dotenv
from google import genai
from google.genai import types

from keywords import extract_keywords
from presets import load_preset, get_preset_components, list_available_presets

# Load environment variables from .env file
load_dotenv()


# Output directory for generated images
OUTPUT_DIR = "output"


# Supported aspect ratios and sizes for Gemini API
SUPPORTED_ASPECT_RATIOS = ["1:1", "2:3", "3:2", "3:4", "4:3", "4:5", "16:9"]
SUPPORTED_SIZES = ["1K", "2K", "4K"]


def ensure_output_dir():
    """Create output directory if it doesn't exist."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)


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
    """Sanitize title for use in filename."""
    # Convert to lowercase
    title = title.lower()
    # Replace spaces and special characters with underscores
    title = re.sub(r"[^a-z0-9]+", "_", title)
    # Remove leading/trailing underscores
    title = title.strip("_")
    return title


def generate_filename_base(title: str, media_type: str = "book") -> str:
    """
    Generate base output filename (without extension) from title, media type, and timestamp.

    Args:
        title: The media title
        media_type: Type of media (book, film, or music)

    Returns:
        Base filename: {media_type}_{sanitized_title}_{timestamp}
    """
    sanitized = sanitize_title(title)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{media_type}_{sanitized}_{timestamp}"


def build_prompt(
    title: str,
    text_content: str,
    preset_components: dict,
    keywords: list,
    media_type: str = "book",
    include_overlay: bool = False,
    author: str = "",
    artist: str = "",
) -> str:
    """
    Build descriptive narrative prompt from title, text, preset, and keywords.

    Args:
        title: The book/film/music title
        text_content: Text content describing the scene/mood
        preset_components: Dictionary with base, lighting, color_palette, camera
        keywords: List of extracted keywords
        media_type: Type of media (book, film, or music)
        include_overlay: Whether to include title overlay
        author: Author name (for books)
        artist: Artist name (for music)

    Returns:
        Narrative prompt string
    """
    # Start with media context
    media_context = {
        "book": f"Based on the book '{title}'",
        "film": f"Based on the film '{title}'",
        "music": f"Based on the music track '{title}'"
    }
    prompt_parts = [media_context.get(media_type.lower(), f"Based on '{title}'")]

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

    # Add title overlay instructions if requested
    if include_overlay:
        if media_type.lower() == "book":
            overlay_text = f"Include a book cover-style design with the title '{title}'"
            if author:
                overlay_text += f" and author '{author}'"
            overlay_text += " prominently displayed in a style matching the illustration"
            prompt_parts.append(overlay_text)
        elif media_type.lower() == "film":
            prompt_parts.append(
                f"Include the title '{title}' as a cinematic title overlay in a style matching the illustration"
            )
        elif media_type.lower() == "music":
            overlay_text = f"Include the track title '{title}'"
            if artist:
                overlay_text += f" and artist name '{artist}'"
            overlay_text += " as a music cover-style overlay in a style matching the illustration"
            prompt_parts.append(overlay_text)

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
    """Media Image Generator - Generate visualizations for books, films, and music tracks."""
    pass


@cli.command()
@click.option(
    "--title",
    required=True,
    help="Title of the book, film, or music track",
)
@click.option(
    "--text-file",
    required=False,
    type=click.Path(exists=True, readable=True),
    help="Path to text content file (if not provided, will prompt interactively)",
)
@click.option(
    "--media-type",
    type=click.Choice(["book", "film", "music"], case_sensitive=False),
    default="book",
    help="Type of media: book, film, or music track (default: book)",
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
    media_type: str,
    style: str,
    skip_keywords: bool,
    aspect_ratio: str,
    size: str,
):
    """Generate an image visualization for a book, film, or music track."""

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

    # Get text content - either from file or interactive input
    if text_file:
        # Read from file
        try:
            with open(text_file, "r", encoding="utf-8") as f:
                text_content = f.read()
        except Exception as e:
            click.echo(f"Error reading text file: {e}", err=True)
            return
    else:
        # Interactive input
        click.echo("\nEnter or paste your text content below.")
        click.echo("Press Ctrl+D (Unix) or Ctrl+Z then Enter (Windows) when finished:")
        click.echo("-" * 80)
        try:
            text_content = click.get_text_stream('stdin').read()
            if not text_content.strip():
                click.echo("Error: No text content provided", err=True)
                return
        except (EOFError, KeyboardInterrupt):
            click.echo("\nInput cancelled.", err=True)
            return
        click.echo("-" * 80)
        click.echo(f"Received {len(text_content)} characters\n")

    # Extract keywords (unless skipped)
    keywords = []
    if not skip_keywords:
        media_label = {"book": "book", "film": "film", "music": "music track"}[media_type.lower()]
        click.echo(f"Extracting keywords from {media_label} title...")
        try:
            keywords = extract_keywords(title, api_key, media_type)
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

    # Build prompt (no overlay support in non-interactive mode for now)
    prompt = build_prompt(title, text_content, preset_components, keywords, media_type, False, "", "")
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
    filename_base = generate_filename_base(title, media_type)
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

                # Ensure output directory exists
                ensure_output_dir()

                # Generate filename with index if multiple images
                if file_index > 0:
                    output_filename = os.path.join(
                        OUTPUT_DIR, f"{filename_base}_{file_index}{file_extension}"
                    )
                else:
                    output_filename = os.path.join(
                        OUTPUT_DIR, f"{filename_base}{file_extension}"
                    )

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


@cli.command()
def interactive():
    """Interactive mode - answer prompts to generate an image."""

    print("=" * 80)
    print("✨ MEDIA IMAGE GENERATOR - INTERACTIVE MODE ✨")
    print("=" * 80)
    print()

    # Load API key
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("❌ Error: GEMINI_API_KEY not found in environment or .env file")
        return

    # Step 1: Media Type
    media_type = questionary.select(
        "📚 Select media type:",
        choices=[
            questionary.Choice("📖 Book", value="book"),
            questionary.Choice("🎬 Film", value="film"),
            questionary.Choice("🎵 Music", value="music"),
        ],
        default="book",
    ).ask()

    if not media_type:
        print("\n❌ Cancelled.")
        return

    # Step 2: Title
    title = questionary.text(
        "✍️  Enter the title:",
        validate=lambda text: len(text.strip()) > 0 or "Title cannot be empty",
    ).ask()

    if not title:
        print("\n❌ Cancelled.")
        return

    # Step 3: Style/Preset
    presets = list_available_presets()
    if not presets:
        print("⚠️  Warning: No presets found in presets/ directory")
        print("Using default 'watercolor' style")
        style = "watercolor"
    else:
        preset_choices = [
            questionary.Choice(
                f"{preset['name']} - {preset['description']}",
                value=preset["filename"],
            )
            for preset in presets
        ]

        style = questionary.select(
            "🎨 Select visual style:",
            choices=preset_choices,
        ).ask()

        if not style:
            print("\n❌ Cancelled.")
            return

    # Step 4: Text Content
    provide_text = questionary.confirm(
        "📝 Do you want to provide text content for this scene?",
        default=True,
    ).ask()

    if provide_text is None:
        print("\n❌ Cancelled.")
        return

    text_content = ""
    if provide_text:
        print("\n" + "-" * 80)
        print("📋 Enter or paste your text content below.")
        print("Press Ctrl+D (Unix) or Ctrl+Z then Enter (Windows) when finished:")
        print("-" * 80)
        try:
            import sys

            text_content = sys.stdin.read()
            print("-" * 80)
            if text_content.strip():
                print(f"✅ Received {len(text_content)} characters")
            else:
                print("⚠️  No text content provided - will use title only")
                text_content = ""
        except (EOFError, KeyboardInterrupt):
            print("\n⚠️  No text content provided - will use title only")
            text_content = ""

    # Step 4b: Title Overlay
    include_overlay = questionary.confirm(
        "🎯 Include title overlay on the image?",
        default=False,
    ).ask()

    if include_overlay is None:
        print("\n❌ Cancelled.")
        return

    author = ""
    artist = ""

    if include_overlay:
        if media_type.lower() == "book":
            author = questionary.text(
                "✍️  Enter author name:",
                validate=lambda text: len(text.strip()) > 0 or "Author cannot be empty",
            ).ask()
            if not author:
                print("\n❌ Cancelled.")
                return
        elif media_type.lower() == "music":
            artist = questionary.text(
                "🎤 Enter artist name:",
                validate=lambda text: len(text.strip()) > 0 or "Artist cannot be empty",
            ).ask()
            if not artist:
                print("\n❌ Cancelled.")
                return

    # Step 5: Additional Options
    extract_keywords = questionary.confirm(
        "🔑 Extract keywords from title?",
        default=True,
    ).ask()

    if extract_keywords is None:
        print("\n❌ Cancelled.")
        return

    skip_keywords = not extract_keywords

    aspect_ratio = questionary.select(
        "📐 Select aspect ratio:",
        choices=SUPPORTED_ASPECT_RATIOS,
        default="3:4",
    ).ask()

    if not aspect_ratio:
        print("\n❌ Cancelled.")
        return

    size = questionary.select(
        "📏 Select image size:",
        choices=SUPPORTED_SIZES,
        default="1K",
    ).ask()

    if not size:
        print("\n❌ Cancelled.")
        return

    # Configuration Summary
    print()
    print("=" * 80)
    print("📋 CONFIGURATION SUMMARY")
    print("=" * 80)
    print(f"Media Type:     {media_type}")
    print(f"Title:          {title}")
    if include_overlay:
        if media_type.lower() == "book" and author:
            print(f"Author:         {author}")
        elif media_type.lower() == "music" and artist:
            print(f"Artist:         {artist}")
    print(f"Style:          {style}")
    print(
        f"Text Content:   {'Yes (' + str(len(text_content)) + ' chars)' if text_content else 'No'}"
    )
    print(f"Title Overlay:  {'Yes' if include_overlay else 'No'}")
    print(f"Keywords:       {'Yes' if not skip_keywords else 'No'}")
    print(f"Aspect Ratio:   {aspect_ratio}")
    print(f"Size:           {size}")
    print("=" * 80)
    print()

    proceed = questionary.confirm(
        "🚀 Proceed with image generation?",
        default=True,
    ).ask()

    if not proceed:
        print("❌ Cancelled.")
        return

    # Now call the generation logic (same as generate command)
    print("\n" + "=" * 80)
    print("🎨 GENERATING IMAGE")
    print("=" * 80)

    # Load preset
    try:
        preset = load_preset(style)
        preset_components = get_preset_components(preset)
    except FileNotFoundError as e:
        print(f"❌ Error: {e}")
        return
    except Exception as e:
        print(f"❌ Error loading preset: {e}")
        return

    # Extract keywords (unless skipped)
    keywords = []
    if not skip_keywords:
        media_label = {"book": "book", "film": "film", "music": "music track"}[
            media_type.lower()
        ]
        print(f"\n🔍 Extracting keywords from {media_label} title...")
        try:
            keywords = extract_keywords(title, api_key, media_type)
            if keywords:
                print(f"✅ Extracted {len(keywords)} keywords:")
                for keyword in keywords[:10]:
                    print(f"  - {keyword}")
                if len(keywords) > 10:
                    print(f"  ... and {len(keywords) - 10} more")
            else:
                print("⚠️  No keywords extracted (continuing anyway)")
        except Exception as e:
            print(f"⚠️  Warning: Keyword extraction failed: {e}")
            print("Continuing without keywords...")

    # Build prompt
    prompt = build_prompt(
        title, text_content, preset_components, keywords, media_type, include_overlay, author, artist
    )
    system_instruction = build_system_instruction(preset_components)

    # Display prompt
    print("\n" + "=" * 80)
    print("📝 PROMPT PREVIEW")
    print("=" * 80)
    print(f"\nSystem Instruction:\n{system_instruction}\n")
    print(f"Main Prompt:\n{prompt}\n")
    print("=" * 80)

    # Generate filename
    filename_base = generate_filename_base(title, media_type)
    print(f"\n💾 Output filename base: {filename_base}\n")

    # Initialize Gemini client
    client = genai.Client(api_key=api_key)

    # Generate image
    print("\n🎨 Generating image...")
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

                # Ensure output directory exists
                ensure_output_dir()

                # Generate filename with index if multiple images
                if file_index > 0:
                    output_filename = os.path.join(
                        OUTPUT_DIR, f"{filename_base}_{file_index}{file_extension}"
                    )
                else:
                    output_filename = os.path.join(
                        OUTPUT_DIR, f"{filename_base}{file_extension}"
                    )

                # Save binary file
                with open(output_filename, "wb") as f:
                    f.write(data_buffer)

                saved_files.append(output_filename)
                print(f"💾 Image saved: {output_filename}")
                file_index += 1

            # Handle text responses
            elif hasattr(part, "text") and part.text:
                print(f"💬 Response: {part.text}")

        if saved_files:
            print(f"\n✅ Success! Generated {len(saved_files)} image(s):")
            for f in saved_files:
                print(f"  - {f}")
        else:
            print("⚠️  Warning: No images were generated")

    except Exception as e:
        print(f"❌ Error generating image: {e}")
        raise


if __name__ == "__main__":
    cli()
