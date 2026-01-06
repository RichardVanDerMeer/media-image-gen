# Book Image Generator

A Python CLI tool that generates visualizations of book pages in specific styles or themes using Google's Gemini AI.

## Features

- Generate images from book titles and text content
- Support for preset styles (watercolor, etc.)
- Automatic keyword extraction from book titles
- Interactive prompt confirmation before generation
- Auto-generated filenames based on book title and timestamp

## Installation

1. Install dependencies:

```bash
pip install -e .
```

Or using uv:

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

### Basic Usage

```bash
python main.py generate \
  --title "The Old Man and the Sea" \
  --text-file page12.txt \
  --style watercolor
```

### Options

- `--title`: Book title (required)
- `--text-file`: Path to text content file (required)
- `--style`: Preset style name (default: "watercolor")
- `--skip-keywords`: Skip keyword extraction step

### Example

```bash
python main.py generate \
  --title "A Day in the Life of Ivan Denisovich" \
  --text-file sample_page.txt \
  --style watercolor
```

The tool will:

1. Extract keywords from the book title
2. Build a descriptive prompt combining the title, text content, keywords, and style
3. Display the prompt for your confirmation
4. Generate the image and save it with an auto-generated filename

## Output

Images are saved with filenames in the format:

```
{sanitized_title}_{timestamp}.{extension}
```

Example: `the_old_man_and_the_sea_20241215_143022.png`

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

1. **Keyword Extraction**: Uses Gemini Pro to extract setting/atmosphere keywords from the book title
2. **Prompt Construction**: Combines book title, text content, keywords, and preset style into a narrative prompt
3. **System Instruction**: Preset style guidelines are provided as system instructions to guide the AI
4. **Image Generation**: Uses Gemini 3 Pro Image Preview to generate the image
5. **File Saving**: Saves the generated image with an auto-generated filename

## Requirements

- Python 3.10+
- Gemini API key
- Dependencies: click, google-genai, python-dotenv, pyyaml

## Troubleshooting

- **API Key Error**: Make sure `GEMINI_API_KEY` is set in your environment or `.env` file
- **Preset Not Found**: Check that the preset file exists in the `presets/` directory
- **Keyword Extraction Fails**: Use `--skip-keywords` to proceed without keywords
