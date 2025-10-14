#!/usr/bin/env python3

import os
import argparse
import mimetypes
import tempfile
import urllib.request
import urllib.parse
from pathlib import Path
import time
from PIL import Image

try:
    from google import genai
    from google.genai import types
    from google.genai.types import Part
    from PIL import Image
    import google.auth
    from google.cloud import storage
    import google.auth.transport.requests
except ImportError:
    print("Error: Required Google libraries not found.")
    print("Please install dependencies:")
    print("  pip install google-genai google-auth google-cloud-storage Pillow")
    exit(1)

# --- Configuration ---
LOCATION = "us-central1"  # Changed from "global" to a specific region
MODEL_ID = "gemini-2.5-flash-image"
MAX_RESOLUTION = "1024x1024"

# Valid aspect ratios
VALID_ASPECT_RATIOS = {
    "21:9", "16:9", "4:3", "3:2",  # Landscape
    "1:1",                          # Square
    "9:16", "3:4", "2:3",          # Portrait
    "5:4", "4:5"                   # Flexible
}

# Global verbosity flags
VERBOSE = False
DEBUG = False

# Global clients
client = None
PROJECT_ID = ""
gcs_client = None

def log_verbose(message):
    """Print verbose message if verbose mode is enabled."""
    if VERBOSE:
        print(f"[VERBOSE] {message}")

def log_debug(message):
    """Print debug message if debug mode is enabled."""
    if DEBUG:
        print(f"[DEBUG] {message}")

def initialize_client():
    global client, PROJECT_ID, gcs_client
    
    if client:
        log_debug("Client already initialized, reusing existing client")
        return client

    try:
        # Get project ID from environment or credentials
        PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT", "")
        log_debug(f"GOOGLE_CLOUD_PROJECT env var: {PROJECT_ID or 'not set'}")
        
        # Get default credentials
        log_verbose("Getting default credentials...")
        credentials, project_id_auth = google.auth.default(
            scopes=['https://www.googleapis.com/auth/cloud-platform']
        )
        log_debug(f"Credentials type: {type(credentials)}")
        log_debug(f"Project from auth: {project_id_auth}")
        
        # Check if we have service account credentials and try to get user credentials
        if hasattr(credentials, 'service_account_email'):
            log_verbose(f"Service account detected: {credentials.service_account_email}")
            log_verbose("For Vertex AI, user credentials are recommended. Please ensure you have run:")
            log_verbose("  gcloud auth application-default login --scopes=https://www.googleapis.com/auth/cloud-platform")
        
        if not PROJECT_ID and project_id_auth:
            PROJECT_ID = project_id_auth
            log_verbose(f"Using project from credentials: {PROJECT_ID}")

        if not PROJECT_ID:
            raise ValueError("Could not determine project ID. Please set GOOGLE_CLOUD_PROJECT environment variable.")

        log_verbose(f"Initializing Gemini client with API key...")
        
        # Use API key authentication
        api_key = os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY environment variable not set.")
        log_verbose("Using API key authentication")
        client = genai.Client(api_key=api_key)
        
        log_verbose("Initializing GCS client...")
        gcs_client = storage.Client(credentials=credentials, project=PROJECT_ID)
        
        print(f"Client initialized for project {PROJECT_ID} in {LOCATION}")
        log_debug(f"Client object: {client}")
        
    except Exception as e:
        print(f"Error initializing client: {e}")
        log_debug(f"Full error: {repr(e)}")
        print("\nPlease ensure:")
        print("  1. You have authenticated: gcloud auth application-default login")
        print("  2. Vertex AI API is enabled: gcloud services enable aiplatform.googleapis.com")
        print("  3. GOOGLE_CLOUD_PROJECT is set: export GOOGLE_CLOUD_PROJECT=your-project-id")
        print("  4. You have the necessary IAM roles (run ./01-setup-iam-permission.sh)")
        return None
        
    return client

def download_from_url(url: str, temp_dir: str) -> str:
    """Downloads a file from a URL to a temporary location."""
    try:
        log_verbose(f"Downloading from URL: {url}")
        
        # Parse URL to get filename
        parsed_url = urllib.parse.urlparse(url)
        filename = os.path.basename(parsed_url.path) or "downloaded_image"
        log_debug(f"Parsed filename from URL: {filename}")
        
        # Ensure filename has an extension
        if '.' not in filename:
            log_verbose("No extension in filename, determining from content-type...")
            with urllib.request.urlopen(url) as response:
                content_type = response.headers.get('Content-Type', '')
                log_debug(f"Content-Type: {content_type}")
                
                if 'jpeg' in content_type or 'jpg' in content_type:
                    filename += '.jpg'
                elif 'png' in content_type:
                    filename += '.png'
                elif 'webp' in content_type:
                    filename += '.webp'
                else:
                    filename += '.jpg'
                    log_verbose(f"Unknown content type, defaulting to .jpg")
        
        temp_path = os.path.join(temp_dir, filename)
        log_debug(f"Temporary path: {temp_path}")
        
        print(f"Downloading from URL: {url}")
        urllib.request.urlretrieve(url, temp_path)
        print(f"Downloaded to temporary file: {filename}")
        
        return temp_path
        
    except Exception as e:
        print(f"Error downloading from URL {url}: {e}")
        log_debug(f"Full error: {repr(e)}")
        return None

def download_from_gcs(gcs_path: str, temp_dir: str) -> str:
    """Downloads a file from GCS to a temporary location."""
    global gcs_client
    
    try:
        log_verbose(f"Downloading from GCS: {gcs_path}")
        
        # Parse GCS path
        if not gcs_path.startswith("gs://"):
            print(f"Error: Invalid GCS path format: {gcs_path}")
            return None
        
        # Remove gs:// prefix and split into bucket and blob
        path_without_prefix = gcs_path[5:]
        parts = path_without_prefix.split('/', 1)
        
        if len(parts) != 2:
            print(f"Error: Invalid GCS path format: {gcs_path}")
            log_debug(f"Path parts: {parts}")
            return None
        
        bucket_name, blob_name = parts
        filename = os.path.basename(blob_name)
        temp_path = os.path.join(temp_dir, filename)
        
        log_debug(f"Bucket: {bucket_name}, Blob: {blob_name}")
        log_debug(f"Temporary path: {temp_path}")
        
        print(f"Downloading from GCS: {gcs_path}")
        
        # Initialize GCS client if needed
        if not gcs_client:
            log_verbose("GCS client not initialized, initializing now...")
            initialize_client()
        
        bucket = gcs_client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        
        log_verbose(f"Downloading blob to {temp_path}...")
        blob.download_to_filename(temp_path)
        
        print(f"Downloaded to temporary file: {filename}")
        return temp_path
        
    except Exception as e:
        print(f"Error downloading from GCS {gcs_path}: {e}")
        log_debug(f"Full error: {repr(e)}")
        return None

def get_local_path(input_path: str, temp_dir: str) -> str:
    """Returns a local file path for the input, downloading if necessary."""
    log_verbose(f"Processing input path: {input_path}")
    
    # Check if it's a URL
    if input_path.startswith(('http://', 'https://')):
        log_debug("Detected HTTP/HTTPS URL")
        return download_from_url(input_path, temp_dir)
    
    # Check if it's a GCS path
    elif input_path.startswith('gs://'):
        log_debug("Detected GCS path")
        return download_from_gcs(input_path, temp_dir)
    
    # Otherwise, treat as local file
    else:
        log_debug("Treating as local file path")
        expanded_path = os.path.expanduser(input_path)
        log_debug(f"Expanded path: {expanded_path}")
        
        if os.path.exists(expanded_path):
            log_verbose(f"Local file found: {expanded_path}")
            return expanded_path
        else:
            print(f"Error: Local file not found: {expanded_path}")
            return None

def load_image_part(image_path: str, temp_dir: str = None) -> Part:
    """Loads an image from a file path, URL, or GCS bucket and returns a GenAI Part."""
    # Create temporary directory if needed
    if temp_dir is None:
        temp_dir = tempfile.mkdtemp(prefix="gemini_image_")
        log_debug(f"Created temporary directory: {temp_dir}")
    
    # Get local path (download if necessary)
    local_path = get_local_path(image_path, temp_dir)
    if not local_path:
        return None
    
    try:
        log_verbose(f"Loading image from: {local_path}")
        
        with open(local_path, "rb") as f:
            image_bytes = f.read()
        
        log_debug(f"Read {len(image_bytes)} bytes from image file")

        mime_type, _ = mimetypes.guess_type(local_path)
        log_debug(f"Guessed MIME type: {mime_type}")
        
        if not mime_type or not mime_type.startswith("image/"):
            ext = os.path.splitext(local_path)[1].lower()
            log_verbose(f"Determining MIME type from extension: {ext}")
            
            mime_type_map = {
                ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
                ".png": "image/png", ".webp": "image/webp",
                ".bmp": "image/bmp", ".gif": "image/gif"
            }
            mime_type = mime_type_map.get(ext, "image/jpeg")

        print(f"Loaded image {os.path.basename(local_path)} as {mime_type}")
        log_debug(f"Creating Part with {len(image_bytes)} bytes and MIME type {mime_type}")
        
        return Part.from_bytes(data=image_bytes, mime_type=mime_type)
        
    except Exception as e:
        print(f"Error loading image {local_path}: {e}")
        log_debug(f"Full error: {repr(e)}")
        return None

def call_gemini_api(contents: list, output_path: str, aspect_ratio: str = "16:9"):
    """Sends the content parts to Gemini API and saves the resulting image."""
    if not initialize_client():
        print("Client not initialized. Cannot proceed.")
        return

    if not contents:
        print("Error: No content provided for the API call.")
        return

    output_path = os.path.expanduser(output_path)
    log_debug(f"Output path: {output_path}")
    log_debug(f"Content parts: {len(contents)}")
    log_debug(f"Requested aspect ratio: {aspect_ratio}")

    try:
        print(f"Sending request to Gemini model: {MODEL_ID}...")
        print(f"Aspect ratio: {aspect_ratio}")
        
        if DEBUG:
            print(f"[DEBUG] API call parameters:")
            print(f"  Model: {MODEL_ID}")
            print(f"  Contents: {[type(c).__name__ for c in contents]}")
        
        # Create config for image generation
        config = types.GenerateContentConfig(
            response_modalities=["IMAGE"],
            image_config=types.ImageConfig(
                aspect_ratio=aspect_ratio,
            )
        )
        
        log_debug(f"Config created: {config}")
        
        # Retry logic for API calls
        max_retries = 3
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                response = client.models.generate_content(
                    model=MODEL_ID,
                    contents=contents,
                    config=config,
                )
                break  # Success, exit retry loop
            except Exception as api_error:
                if "503" in str(api_error) or "UNAVAILABLE" in str(api_error):
                    if attempt < max_retries - 1:
                        print(f"Service temporarily unavailable, retrying in {retry_delay} seconds...")
                        time.sleep(retry_delay)
                        retry_delay *= 2  # Exponential backoff
                        continue
                raise api_error  # Re-raise if not a retryable error or max retries reached

        log_verbose("Response received from API")
        log_debug(f"Response type: {type(response)}")
        
        if hasattr(response, 'parts') and response.parts:
            log_verbose(f"Found {len(response.parts)} part(s)")
            has_image = False
            
            for part in response.parts:
                log_debug(f"Processing part: {type(part)}")
                
                if part.text:
                    log_verbose(f"Text part found: {part.text[:100]}...")
                    print(f"Model Text Response: {part.text}")
                elif image := part.as_image():
                    print("---")
                    print("### Received Image Output:")
                    try:
                        # Use the same approach as the cookbook
                        image.save(output_path)
                        
                        print(f"‚Ä¢√Å√ò(Output image saved to {output_path} (Aspect ratio: {aspect_ratio})")
                        log_verbose(f"File size: {os.path.getsize(output_path)} bytes")
                        has_image = True
                        
                    except Exception as e:
                        print(f"Error saving image: {e}")
                        log_debug(f"Full error: {repr(e)}")
                    
            if not has_image:
                print("No image data received in the response.")
                log_debug("No image parts found in any response parts")
        else:
            print("No parts returned in the response.")
            if hasattr(response, 'prompt_feedback'):
                print(f"Prompt Feedback: {response.prompt_feedback}")
                log_debug(f"Full prompt feedback: {response.prompt_feedback}")

    except Exception as e:
        error_msg = str(e)
        if "PERMISSION_DENIED" in error_msg:
            print(f"Permission error: {e}")
            print("\nTo fix this, run: ./01-setup-iam-permission.sh")
            print("This will grant the necessary IAM permissions to your account.")
        elif "404" in error_msg or "not found" in error_msg:
            print(f"Model not found error: {e}")
            print(f"\nThe model '{MODEL_ID}' may not be available in location '{LOCATION}'.")
            print("Try changing the LOCATION variable in the script to 'us-central1' or another region.")
        else:
            print(f"An error occurred during API call: {e}")
        
        log_debug(f"Full error: {repr(e)}")
        
        if DEBUG:
            import traceback
            print("[DEBUG] Full traceback:")
            traceback.print_exc()

# --- Command Handlers ---
def handle_generate(args):
    print("Mode: Text-to-Image Generation")
    log_debug(f"Prompt: {args.prompt}")
    log_debug(f"Output: {args.output_file}")
    
    contents = [args.prompt]
    call_gemini_api(contents, args.output_file, args.aspect_ratio)

def handle_edit(args):
    print("Mode: Image Editing")
    log_debug(f"Input: {args.input_file}")
    log_debug(f"Prompt: {args.prompt}")
    
    with tempfile.TemporaryDirectory(prefix="gemini_image_") as temp_dir:
        log_debug(f"Temporary directory: {temp_dir}")
        image_part = load_image_part(args.input_file, temp_dir)
        if image_part:
            contents = [image_part, args.prompt]
            call_gemini_api(contents, args.output_file, args.aspect_ratio)

def handle_restore(args):
    print("Mode: Photo Restoration")
    log_debug(f"Input: {args.input_file}")
    
    with tempfile.TemporaryDirectory(prefix="gemini_image_") as temp_dir:
        image_part = load_image_part(args.input_file, temp_dir)
        if image_part:
            contents = [image_part, args.prompt]
            call_gemini_api(contents, args.output_file, args.aspect_ratio)

def handle_style_transfer(args):
    print("Mode: Style Transfer")
    log_debug(f"Input: {args.input_file}")
    log_debug(f"Style ref: {args.style_ref_image}")
    
    with tempfile.TemporaryDirectory(prefix="gemini_image_") as temp_dir:
        input_image_part = load_image_part(args.input_file, temp_dir)
        if not input_image_part: 
            return

        contents = [input_image_part]
        
        if args.style_ref_image:
            style_image_part = load_image_part(args.style_ref_image, temp_dir)
            if not style_image_part: 
                return
            contents.append(style_image_part)
            print(f"Using style reference image: {os.path.basename(args.style_ref_image)}")

        contents.append(args.prompt)
        call_gemini_api(contents, args.output_file, args.aspect_ratio)

def handle_compose(args):
    print("Mode: Creative Composition")
    
    with tempfile.TemporaryDirectory(prefix="gemini_image_") as temp_dir:
        contents = []
        input_parts = {
            "input1": args.input_file1,
            "input2": args.input_file2,
            "input3": args.input_file3,
        }
        
        for key, path in input_parts.items():
            if path:
                log_debug(f"Loading {key}: {path}")
                image_part = load_image_part(path, temp_dir)
                if not image_part: 
                    return
                contents.append(image_part)
                
        if not contents:
            print("Error: At least one input image is required for compose mode.")
            return
            
        contents.append(args.prompt)
        call_gemini_api(contents, args.output_file, args.aspect_ratio)

def handle_add_text(args):
    print("Mode: Add Text to Image")
    log_debug(f"Input: {args.input_file}")
    
    with tempfile.TemporaryDirectory(prefix="gemini_image_") as temp_dir:
        image_part = load_image_part(args.input_file, temp_dir)
        if image_part:
            contents = [image_part, args.prompt]
            call_gemini_api(contents, args.output_file, args.aspect_ratio)

def handle_sketch_to_image(args):
    print("Mode: Sketch to Image")
    log_debug(f"Input: {args.input_file}")
    
    with tempfile.TemporaryDirectory(prefix="gemini_image_") as temp_dir:
        image_part = load_image_part(args.input_file, temp_dir)
        if image_part:
            contents = [image_part, args.prompt]
            call_gemini_api(contents, args.output_file, args.aspect_ratio)

def handle_test(args):
    """Test command to verify tool setup without making API calls."""
    print("Mode: Test Configuration")
    print("Testing tool setup...")
    
    # Test project ID
    PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT", "")
    if PROJECT_ID:
        print(f"‚úì Project ID: {PROJECT_ID}")
    else:
        print("‚úó Project ID not set")
    
    # Test credentials
    try:
        credentials, project_id_auth = google.auth.default(
            scopes=['https://www.googleapis.com/auth/cloud-platform']
        )
        print(f"‚úì Credentials loaded: {type(credentials).__name__}")
        if hasattr(credentials, 'service_account_email'):
            print(f"  Service account: {credentials.service_account_email}")
    except Exception as e:
        print(f"‚úó Credentials error: {e}")
    
    # Test imports
    try:
        from google.genai import Client
        print("‚úì Google GenAI client available")
    except ImportError as e:
        print(f"‚úó Import error: {e}")
    
    # Test configuration
    print(f"‚úì Model: {MODEL_ID}")
    print(f"‚úì Location: {LOCATION}")
    
    # Test argument parsing
    print(f"‚úì Debug mode: {DEBUG}")
    print(f"‚úì Verbose mode: {VERBOSE}")
    
    print("\nTool setup test completed!")
    print("Note: API calls require proper IAM permissions.")

def validate_aspect_ratio(value):
    """Validate aspect ratio argument."""
    if value not in VALID_ASPECT_RATIOS:
        raise argparse.ArgumentTypeError(
            f"Invalid aspect ratio '{value}'. Must be one of: {', '.join(sorted(VALID_ASPECT_RATIOS))}"
        )
    return value

# --- Main Execution & Argument Parsing ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="CLI tool for Gemini 2.5 Flash Image API features on Vertex AI",
        formatter_class=argparse.RawTextHelpFormatter
    )
    
    # Global arguments
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output")
    parser.add_argument("-d", "--debug", action="store_true", help="Enable debug output (implies verbose)")
    
    subparsers = parser.add_subparsers(title="commands", dest="command", required=True, help="Available image operations")

    # Test command
    parse_test = subparsers.add_parser("test", help="Test tool configuration without API calls")
    parse_test.set_defaults(func=handle_test)

    # Generate command
    parse_generate = subparsers.add_parser("generate", help="Text-to-image generation")
    parse_generate.add_argument("output_file", help="Output file path for generated image")
    parse_generate.add_argument("-p", "--prompt", required=True, help="Text prompt for image generation")
    parse_generate.add_argument("-a", "--aspect-ratio", type=validate_aspect_ratio, default="16:9",
                                help="Aspect ratio (default: 16:9)")
    parse_generate.set_defaults(func=handle_generate)

    # Edit command
    parse_edit = subparsers.add_parser("edit", help="General mask-free image editing")
    parse_edit.add_argument("input_file", help="Input image path/URL/GCS path")
    parse_edit.add_argument("output_file", help="Output file path")
    parse_edit.add_argument("-p", "--prompt", required=True, help="Text prompt describing the edit")
    parse_edit.add_argument("-a", "--aspect-ratio", type=validate_aspect_ratio, default="16:9",
                            help="Aspect ratio (default: 16:9)")
    parse_edit.set_defaults(func=handle_edit)

    # Restore command
    parse_restore = subparsers.add_parser("restore", help="Restore and enhance old or damaged photos")
    parse_restore.add_argument("input_file", help="Input image path/URL/GCS path")
    parse_restore.add_argument("output_file", help="Output file path")
    parse_restore.add_argument("-p", "--prompt",
                               default="Restore this photograph: enhance colors, improve details and sharpness, and remove defects.",
                               help="Prompt for restoration guidance")
    parse_restore.add_argument("-a", "--aspect-ratio", type=validate_aspect_ratio, default="16:9",
                               help="Aspect ratio (default: 16:9)")
    parse_restore.set_defaults(func=handle_restore)

    # Style Transfer command
    parse_style = subparsers.add_parser("style_transfer", help="Apply a new style to an image")
    parse_style.add_argument("input_file", help="Content image path/URL/GCS path")
    parse_style.add_argument("output_file", help="Output file path")
    parse_style.add_argument("-p", "--prompt", required=True, help="Prompt describing the desired style")
    parse_style.add_argument("--style_ref_image", help="Optional style reference image", required=False)
    parse_style.add_argument("-a", "--aspect-ratio", type=validate_aspect_ratio, default="16:9",
                             help="Aspect ratio (default: 16:9)")
    parse_style.set_defaults(func=handle_style_transfer)

    # Compose command
    parse_compose = subparsers.add_parser("compose", help="Combine elements from up to 3 reference images")
    parse_compose.add_argument("output_file", help="Output file path")
    parse_compose.add_argument("-p", "--prompt", required=True, help="Prompt describing how to combine images")
    parse_compose.add_argument("--input_file1", required=True, help="First input image")
    parse_compose.add_argument("--input_file2", help="Optional second input image")
    parse_compose.add_argument("--input_file3", help="Optional third input image")
    parse_compose.add_argument("-a", "--aspect-ratio", type=validate_aspect_ratio, default="16:9",
                               help="Aspect ratio (default: 16:9)")
    parse_compose.set_defaults(func=handle_compose)

    # Add Text command
    parse_add_text = subparsers.add_parser("add_text", help="Render text on an image")
    parse_add_text.add_argument("input_file", help="Input image path/URL/GCS path")
    parse_add_text.add_argument("output_file", help="Output file path")
    parse_add_text.add_argument("-p", "--prompt", required=True, help="Prompt describing the text and placement")
    parse_add_text.add_argument("-a", "--aspect-ratio", type=validate_aspect_ratio, default="16:9",
                                help="Aspect ratio (default: 16:9)")
    parse_add_text.set_defaults(func=handle_add_text)

    # Sketch to Image command
    parse_sketch = subparsers.add_parser("sketch_to_image", help="Generate a detailed image from a sketch")
    parse_sketch.add_argument("input_file", help="Sketch image path/URL/GCS path")
    parse_sketch.add_argument("output_file", help="Output file path")
    parse_sketch.add_argument("-p", "--prompt", default="Flesh out this sketch into a detailed color image", 
                             help="Optional prompt to guide generation")
    parse_sketch.add_argument("-a", "--aspect-ratio", type=validate_aspect_ratio, default="16:9",
                              help="Aspect ratio (default: 16:9)")
    parse_sketch.set_defaults(func=handle_sketch_to_image)

    args = parser.parse_args()
    
    # Set global verbosity flags
    if args.debug:
        DEBUG = True
        VERBOSE = True
    elif args.verbose:
        VERBOSE = True
    
    log_debug("Debug mode enabled")
    log_verbose("Verbose mode enabled")
    
    args.func(args)
