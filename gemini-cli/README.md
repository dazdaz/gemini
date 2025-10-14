## Getting Setup
```
# Method 1
export GEMINI_API_KEY="YOUR_GEMINI_API_KEY"

# Method 2 - In .gemini/.env
GEMINI_API_KEY="YOUR_GEMINI_API_KEY"
```

```
alias gem='cd ~gemini-workingspace && gemini && cd $OLDPWD'`
alias gemupdate='brew upgrade gemini-cli'

gemini /model gemini-2.5-flash
gemini -p "Summarize the main points of the attached file. @./summary.txt"
echo "Count to 10" | gemini
```

## GEMINI.md

Three-Level Configuration System
Gemini CLI supports layered GEMINI.md configurations, prioritized from lowest to highest as follows:

* 1 Global settings: ~/.gemini/GEMINI.md (general rules applied to all projects)
* 2 Project settings: GEMINI.md files located between the current directory and the project root
* 3 Subdirectory settings: Instructions specific to a component or module (local overrides)

### Example #1
```
echo "Do not write to ~/.env" >> ~/src/repo/GEMINI.md
```

### Example #2
```
# GEMINI.md

## General instructions

Projects must use virtual environments, the virtual environment folder must be called .venv, and should be excluded from the git repository.

Python version must be managed with pyenv, Python local version should be 3.11.9 and should be configured in the project folder.

Everytime a python module is installed with pip, a pip freeze must be done to reflect that module installation in a requirements.txt file.

## Planning

If asked to write a plan and create a plan file, do it in a `./plan` subdirectory that you should create beforehand, and should be called `PLAN.md`.

When asked to implement a plan, also record the different steps into a file called steps.md

## API coding

For coding purposes, any API must use the Python Flask framework.

Any constant or variable coming from the environment must be loaded from a .env file.

## Testing

This project uses Pytest as testing framework.

## Running the application
```

* * https://levelup.gitconnected.com/boost-gemini-cli-productivity-100x-with-the-gemini-md-file-61ad8cb00e16 Good guide here

## Other methodology's
* Configure project specs in a @specs folder, so specs/GEMINI.md specs/architecture.md etc


## Extensions

```
gemini extensions install chrome-devtools-mcp
gemini extensions install nanobanana
gemini extensions install flutter
gemini extensions install genkit
gemini extensions install gke-mcp
gemini extensions install gemini-cli-get
```

# Ricc's cli custom commands
```
gemini extensions install https://github.com/palladius/gemini-cli-custom-commands
# 🔄 Update
gemini extensions update palladius-common-commands
gemini extensions update --all
```

## Using gemini-cli with Vertex Model Garden
Switch to Vertex AI for higher quotas, enterprise features, or specific models from Model Garden.

```bash
# Assign the Vertex AI User IAM role (roles/aiplatform.user) granted to your account for the project.

export GOOGLE_CLOUD_PROJECT=GOOGLE_CLOUD_PROJECT_ID
export GOOGLE_CLOUD_LOCATION=global
export GOOGLE_GENAI_USE_VERTEXAI=True
```

## Optional: Enhance Integration with VS Code Extension
For seamless context-aware workflows (e.g., Gemini CLI automatically detecting open files or selections in VS Code), install the Gemini CLI Companion extension. This enables native diffing, workspace access, and better prompts based on your current editor state.

* Open VS Code.
* Go to the Extensions view (Ctrl/Cmd + Shift + X).
* Search for "Gemini CLI Companion".


##Setting Up External Editor for File Updates
Gemini CLI can suggest changes to files and open them directly in VS Code for review and application:

* Open the integrated terminal in VS Code (Ctrl/Cmd + `).
* Start Gemini CLI: Run gemini.
* Configure VS Code as your external editor using the slash command:
```
text/editor vscode
```
* This sets VS Code as the default editor for diffs and updates. VS Code is pre-supported in the list of editors.


## Setup integration for Git Action
```
/setup-github
```

## Updating Files with Gemini CLI
Gemini CLI uses a ReAct (reason-and-act) loop to analyze, suggest, and apply changes. It can read files, propose edits, and use tools like file operations for updates. Here's how to update files:


## 1 Navigate to Your Workspace:

* Open your project folder in VS Code.
* In the integrated terminal, cd to the project directory (e.g., cd my-project).

## 2 Provide Context and Prompt for Updates:

* Reference files using @filename to upload/include them in the prompt (e.g., @src/main.js for local file selection).
* Examples of prompts for updates:
```
Fix a bug: Update @buggy-file.js to fix the null pointer error in the login function.
Add a feature: Add authentication middleware to @app.js and update routes in @routes.js.
Refactor code: Refactor the selected code in my open file to use async/await.
Batch updates: Improve test coverage for all files in @tests/ by adding unit tests.
```

With the Companion extension, Gemini CLI automatically includes context from open files or selections—no need for @ every time.

### 3 Review and Apply Changes:

Gemini CLI will reason step-by-step, then suggest changes (often as a diff).
If configured with /editor vscode, it opens a VS Code window/tab with:

Side-by-side diff view (original vs. proposed).
Highlighted changes for easy review.

Accept changes: Edit manually in VS Code, then save (Ctrl/Cmd + S). Gemini CLI can confirm via follow-up prompts like /apply.
Automated apply: For simple cases, use built-in tools (e.g., prompt: Write changes directly to @file.js), but review first to avoid overwrites. Gemini CLI supports safe file ops via its ReAct loop.

## 4 Iterate and Chat:

Use conversational mode: Follow up with "Make it more efficient" or /chat for threaded discussion.
Slash commands for control:
```
/help: List all commands.
/clear: Reset context.
/quit: Exit session.
```

## 5 Random commands
```
/memory add my name is xyz
/memory show
/memory refresh
```

## MCP Servers
* https://github.com/GoogleCloudPlatform/cloud-run-mcp
* https://github.com/GoogleCloudPlatform/vertex-ai-creative-studio/tree/main/experiments/mcp-genmedia
* 
### Installation of cloud run mcp gemini-cli extension
```bash
mkdir -p ~/.gemini/extensions/cloud-run/gemini-extension && \
curl -s -L https://raw.githubusercontent.com/GoogleCloudPlatform/cloud-run-mcp/main/gemini-extension.json > ~/.gemini/extensions/cloud-run/gemini-extension.json && \
curl -s -L https://raw.githubusercontent.com/GoogleCloudPlatform/cloud-run-mcp/main/gemini-extension/GEMINI.md > ~/.gemini/extensions/cloud-run/gemini-extension/GEMINI.md
```

## Folks writing about gemini-cli
* https://github.com/google-gemini/gemini-cli/releases
* blog.google/technology/developers/gemini-code-assist-free
* https://dotgemini.dev/ Collection of prompts
* https://medium.com/@jackwoth This Week in gemini-cli
* https://medium.com/@iromin
* https://www.philschmid.de/gemini-cli-cheatsheet
* https://github.com/google-gemini/gemini-cli/blob/main/docs/cli/configuration.md
* https://github.com/google-gemini/gemini-cli/releases
* https://cloud.google.com/blog/topics/developers-practitioners/gemini-cli-custom-slash-commands
* https://geminicli.com/
* https://github.com/palladius/gemini-cli-custom-commands
* https://medium.com/google-cloud/advanced-gemini-cli-part-2-decoding-the-context-edc9e815b548
* https://aipositive.substack.com/p/how-i-turned-gemini-cli-into-a-multi
