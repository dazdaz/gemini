# Vertex AI Gemini 2.5 Flash Image API CLI Tool

A command-line interface (CLI) tool for interacting with the **Vertex AI Gemini 2.5 Flash Image API**.

This script enables various image-based operations like **text-to-image generation**, **image editing**, and **creative composition** directly from your terminal.

---

## ✨ Features

* **Text-to-Image Generation**: Create images from text descriptions.
* **Image Editing**: Modify images with a simple text prompt (add, remove, or change objects).
* **Photo Restoration**: Enhance old or damaged photos, remove scratches, and improve details.
* **Style Transfer**: Apply the style of one image to another, with or without a reference image.
* **Creative Composition**: Combine elements from multiple images (up to three) into a single new image.
* **Sketch to Image**: Turn a simple sketch into a detailed, fleshed-out image.
* **Add Text to Image**: Render text onto an image at a specified location.
* **Test Configuration**: Verify tool setup without making API calls.

---

## 🚀 Getting Started

### Quick Setup with UV (Recommended)

The easiest way to get started is to use `uv` for fast Python package management:

```bash
# Clone the repository
git clone https://github.com/dazdaz/gemini-2.5-flash-image-tool
cd gemini-2.5-flash-image-tool

# Install dependencies using uv (faster than pip)
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -r requirements.txt

# Set up IAM permissions (required for first-time setup)
chmod +x 01-setup-iam-permission.sh
./01-setup-iam-permission.sh

# Test your configuration
./run.sh test
```

### Quick Setup with Traditional Python

If you prefer to use the traditional setup script:

```bash
# Clone the repository
git clone https://github.com/dazdaz/gemini-2.5-flash-image-tool
cd gemini-2.5-flash-image-tool

# Run the setup script (creates virtual environment and installs dependencies)
chmod +x setup.sh
./setup.sh

# Set up IAM permissions (required for first-time setup)
chmod +x 01-setup-iam-permission.sh
./01-setup-iam-permission.sh
```

### Manual Setup

If you prefer to set up manually:

1. **Create a virtual environment**:
    ```bash
    # Using uv (recommended)
    uv venv
    source .venv/bin/activate
    
    # Or using traditional Python
    python3 -m venv venv
    source venv/bin/activate
    ```

2. **Install dependencies**:
    ```bash
    # Using uv (faster)
    uv pip install -r requirements.txt
    
    # Or using pip
    pip install -r requirements.txt
    ```

3. **Set up Google Cloud**:
    - Authenticate: `gcloud auth login`
    - Set up application default credentials: `gcloud auth application-default login --scopes=https://www.googleapis.com/auth/cloud-platform`
    - Enable Vertex AI API: `gcloud services enable aiplatform.googleapis.com --project=YOUR_PROJECT_ID`
    - Set up IAM permissions: `./01-setup-iam-permission.sh`

4. **Set environment variable**:
    ```bash
    export GOOGLE_CLOUD_PROJECT=your-project-id
    ```

5. **Set Google AI API Key (Recommended)**:
    For the most reliable authentication, it is recommended to use a Google AI API key.

    - Go to the [Google AI Studio](https://aistudio.google.com/app/apikey) and click **"Create API key"**.
    - Alternatively, you can create an API key in the [Google Cloud Console](https://console.cloud.google.com/apis/credentials) by navigating to **"APIs & Services" > "Credentials" > "Create Credentials" > "API key"**.
    - Copy the generated API key.
    - Set it as an environment variable:
      ```bash
      export GOOGLE_API_KEY="your-api-key"
      ```
    The `run.sh` script will automatically use this key if it is set.

### Prerequisites

* **Python 3.8+** (or install `uv` for faster package management)
* **Google Cloud Project**: You need an active Google Cloud project with the Vertex AI API enabled.
* **Authentication**: Ensure you're authenticated with Google Cloud. The easiest way is to run:
    ```bash
    gcloud auth application-default login --scopes=https://www.googleapis.com/auth/cloud-platform
    ```

---

## 💻 Usage

### Test Your Configuration

Before using the tool, test your configuration to ensure everything is set up correctly:

```bash
# Test configuration without making API calls
./run.sh test

# Test with debug output
./run.sh --debug test
```

### Using the Run Script (Recommended)

The easiest way to use the tool is with the provided run script, which handles the virtual environment automatically:

```bash
# Make the run script executable
chmod +x run.sh

# Use the run script (it will activate the virtual environment automatically)
./run.sh generate output.jpg -p "A sunset over mountains"
./run.sh edit input.jpg output.jpg -p "Remove the car"
```

### Manual Usage

If you prefer to run the tool manually:

1. Activate the virtual environment:
    ```bash
    # If using uv
    source .venv/bin/activate
    
    # If using traditional setup
    source venv/bin/activate
    ```

2. Set your project (if not already set):
    ```bash
    export GOOGLE_CLOUD_PROJECT=your-project-id
    ```

3. Run the tool:
    ```bash
    python aiphoto-tool.py <command> [options]
    ```

The tool uses a subcommand structure. The general syntax is:

```bash
python aiphoto-tool.py <command> [options]
```

---

## 💻 Commands Reference

### Test Command
```bash
# Test tool configuration without API calls
./run.sh test
./run.sh --debug test
```

### Text-to-Image Generation
```bash
# Example of text-to-image generation: creates a new image from a text prompt.
./aiphoto-tool.py generate -p "draw me a horse on the beach, gallopping into the sunset" horse.jpg

# Specify the aspect ratio, else default to 16:9
./aiphoto-tool.py generate output.jpg -p "A sunset over mountains" --aspect-ratio 21:9
```

### Image Editing
```bash
# Example of image editing: modifies an input image based on a text prompt.
./aiphoto-tool.py edit 1.jpeg 1-myfile.jpeg -p "remove background"
./aiphoto-tool.py edit my_photo.jpeg my_photo_new_look.jpeg -p "change my clothes to a blue suit"
./aiphoto-tool.py edit input.jpg output.jpg -p "Remove the car" --aspect-ratio 1:1
```

### Photo Restoration
```bash
# Example of photo restoration: enhances an old or damaged photo.
./aiphoto-tool.py restore 1.jpeg 1-restored.jpeg -p "Fixing fading, tears, scratches but don't make any other changes"
```

### Sketch to Image
```bash
# Example of sketch-to-image: transforms a sketch into a detailed image.
./aiphoto-tool.py sketch_to_image sketch.png -p "A photorealistic black sports car" detailed_car.png
```

### Add Text to Image
```bash
# Example of adding text: renders text onto an image.
./aiphoto-tool.py add_text image.png -p "Add the words 'Happy Birthday!' in cursive at the top center of the image" new_image.png
```

### Creative Composition
```bash
# Example of creative composition: combines elements from multiple images.
./aiphoto-tool.py compose --input_file1 background.jpg --input_file2 person.png -p "Place the person from the second image in front of the background" final.png
./aiphoto-tool.py compose --input_file1 picofme.JPG --input_file2 cap.png -p "Place the cap from the second image onto the man's head in the first image but don't change any facial features" man_with_cap.jpeg
```

### Style Transfer
```bash
# Example of style transfer (text-based): applies a style described by a text prompt.
./aiphoto-tool.py style_transfer input.png stylized.png -p "In the style of a watercolor painting"

# Another example of style transfer (text-based): applies a style described by a text prompt.
./aiphoto-tool.py style_transfer input.png -p "In the style of a watercolor painting" stylized.png

# Example of style transfer (reference-based): uses a second image as a style reference.
./aiphoto-tool.py style_transfer input.png --style_ref_image my_style.png -p "Apply the style of the second image to the first" stylized.png
```

---

## 🛠️ Troubleshooting

### Permission Denied Errors
If you encounter permission denied errors, run the IAM setup script:
```bash
./01-setup-iam-permission.sh
```

### Authentication Issues
If you have authentication problems, ensure you've run:
```bash
gcloud auth application-default login --scopes=https://www.googleapis.com/auth/cloud-platform
```

### Test Your Setup
Always test your configuration first:
```bash
./run.sh test
```

### Debug Mode
Use debug mode for detailed troubleshooting:
```bash
./run.sh --debug generate output.jpg -p "test prompt"
```

### Common Issues

1. **Virtual environment not found**: Run `./setup.sh` or create with `uv venv`
2. **Dependencies not installed**: Run `uv pip install -r requirements.txt` or `pip install -r requirements.txt`
3. **Project ID not set**: Set `export GOOGLE_CLOUD_PROJECT=your-project-id`
4. **Model not found**: The tool now uses `gemini-2.0-flash` which should be available in most regions

---

## 📦 Requirements

The tool requires the following Python packages (listed in [`requirements.txt`](requirements.txt)):

- `google-genai>=0.2.0`
- `google-auth>=2.0.0`
- `google-cloud-storage>=2.0.0`
- `Pillow>=10.0.0`

Install with:
```bash
# Using uv (recommended)
uv pip install -r requirements.txt

# Or using pip
pip install -r requirements.txt
```

---

## 🤝 Contributing

Feel free to submit issues and enhancement requests!

---

## 📜 License

See the [LICENCE](LICENCE) file for details.
