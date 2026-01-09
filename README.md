# Media Image Generator

A Python CLI tool that generates visualizations for books, films, and music tracks in specific styles or themes using Google's Gemini AI.

## Features

- Generate images from books, films, or music track titles with descriptive text
- Support for multiple media types (books, films, music tracks)
- Support for preset styles (watercolor, noir, etc.)
- Automatic keyword extraction tailored to each media type
- **Interactive text input** - paste content directly or provide a file
- Interactive prompt confirmation before generation
- Auto-generated filenames with media type prefix and timestamp
- Configurable aspect ratios (1:1, 2:3, 3:2, 3:4, 4:3, 4:5, 16:9)
- Configurable image sizes (1K, 2K, 4K)

## Installation

1. Install dependencies:

```bash
uv sync
```

## Setup

1. Get a Gemini API key from [Google AI Studio](https://makersuite.google.com/app/apikey)

2. Set the API key as an environment variable:

```bash
export GEMINI_API_KEY="your-api-key-here"
```

Or create a `.env` file in the project root:

```
GEMINI_API_KEY=your-api-key-here
```

## Usage

### Interactive Mode (Recommended)

For the easiest experience, use interactive mode where you'll be guided through all options:

```bash
python main.py interactive
```

This will prompt you for:
1. **Media type** - Choose between book, film, or music
2. **Title** - Enter the title of your media
3. **Visual style** - Select from available presets with descriptions
4. **Text content** - Optionally paste scene description, lyrics, or other content
5. **Additional options** - Aspect ratio, image size, keyword extraction

### Command Line Mode

**With a text file:**
```bash
python main.py generate \
  --title "The Old Man and the Sea" \
  --text-file page12.txt \
  --style watercolor
```

**With interactive input (paste text directly):**
```bash
python main.py generate \
  --title "The Old Man and the Sea" \
  --style watercolor
# Then paste your text and press Ctrl+D (Unix) or Ctrl+Z+Enter (Windows)
```

**For a film:**

```bash
python main.py generate \
  --title "Blade Runner" \
  --text-file scene_description.txt \
  --media-type film \
  --style noir
```

**For a music track:**

```bash
python main.py generate \
  --title "Bohemian Rhapsody" \
  --text-file lyrics.txt \
  --media-type music \
  --style watercolor
```

### Options

- `--title`: Title of the book, film, or music track (required)
- `--text-file`: Path to text content file (optional - if omitted, you'll be prompted to paste text interactively)
- `--media-type`: Type of media - `book`, `film`, or `music` (default: `book`)
- `--style`: Preset style name (default: `watercolor`)
- `--skip-keywords`: Skip keyword extraction step
- `--aspect-ratio`: Image aspect ratio - `1:1`, `2:3`, `3:2`, `3:4`, `4:3`, `4:5`, `16:9` (default: `3:4`)
- `--size`: Image size - `1K`, `2K`, `4K` (default: `1K`)

### Example

**Book visualization:**

```bash
python main.py generate \
  --title "A Day in the Life of Ivan Denisovich" \
  --text-file sample_page.txt \
  --style watercolor \
  --aspect-ratio 3:4
```

**Film scene visualization:**

```bash
python main.py generate \
  --title "The Grand Budapest Hotel" \
  --text-file scene.txt \
  --media-type film \
  --style poetic_realism \
  --aspect-ratio 16:9
```

**Music track visualization:**

```bash
python main.py generate \
  --title "Clair de Lune" \
  --text-file mood_description.txt \
  --media-type music \
  --style watercolor \
  --aspect-ratio 1:1
```

The tool will:

1. If no text file is provided, prompt you to paste text content interactively
2. Extract keywords from the title (tailored to the media type)
3. Build a descriptive prompt combining the title, text content, keywords, and style
4. Display the prompt for your confirmation
5. Generate the image and save it with an auto-generated filename

## Output

All generated images are saved in the `output/` directory with filenames in the format:

```
{media_type}_{sanitized_title}_{timestamp}.{extension}
```

Examples:

- `output/book_the_old_man_and_the_sea_20260109_143022.png`
- `output/film_blade_runner_20260109_150000.png`
- `output/music_bohemian_rhapsody_20260109_153045.png`

**Note:** The `output/` directory is automatically created if it doesn't exist and is excluded from version control via `.gitignore`.

## Presets

Presets define the visual style for image generation. They are stored as YAML files in the `presets/` directory.

### Preset Structure

```yaml
name: watercolor
prompt:
  base: |
    Watercolor illustration, soft edges, muted colors,
    painterly texture, paper grain visible
  lighting: soft natural light
  color_palette: pastel blues and earth tones
  camera: wide shot
```

### Creating Custom Presets

1. Create a new YAML file in the `presets/` directory
2. Follow the structure above
3. Use the preset name (without .yaml) with the `--style` option

### Preset Components

- `base`: Base style description
- `lighting`: Lighting conditions
- `color_palette`: Color scheme
- `camera`: Camera/angle perspective

## How It Works

1. **Media Type Selection**: Choose between book, film, or music track visualization
2. **Keyword Extraction**: Uses Gemini Pro to extract relevant keywords tailored to the media type:
   - Books: setting, atmosphere, themes
   - Films: cinematic mood, visual style, atmosphere
   - Music: mood, energy, emotional atmosphere
3. **Prompt Construction**: Combines title, text content, keywords, and preset style into a narrative prompt
4. **System Instruction**: Preset style guidelines are provided as system instructions to guide the AI
5. **Image Generation**: Uses Gemini 3 Pro Image Preview to generate the image
6. **File Saving**: Saves the generated image with an auto-generated filename including media type

## Requirements

- Python 3.10+
- Gemini API key
- Dependencies: click, google-genai, python-dotenv, pyyaml

## Troubleshooting

- **API Key Error**: Make sure `GEMINI_API_KEY` is set in your environment or `.env` file
- **Preset Not Found**: Check that the preset file exists in the `presets/` directory
- **Keyword Extraction Fails**: Use `--skip-keywords` to proceed without keywords
