# Project Livewire: Step-by-Step Instructions

This guide provides clear, step-by-step instructions on how to set up and run the Project Livewire application.

## Prerequisites

Before you begin, ensure you have the following installed on your system:
- **Python 3.10+**
- **pip** (Python's package installer)

## Step 1: Set Up the Environment

First, you need to create a virtual environment and install the required dependencies. This ensures that the project's packages do not interfere with other Python projects on your system.

1.  **Create a Virtual Environment:**
    Open your terminal in the project's root directory and run the following command to create a virtual environment named `venv`:
    ```bash
    python3 -m venv venv
    ```

2.  **Install Dependencies:**
    Next, activate the virtual environment and install the necessary Python packages from the `server/requirements.txt` file. The following command does both in one step:
    ```bash
    source venv/bin/activate && pip install -r server/requirements.txt
    ```
    *Note: You only need to run this setup process once.*

## Step 2: Start the Application

A convenient script has been created to handle starting both the backend and frontend servers.

1.  **Make the Script Executable (First Time Only):**
    If you haven't done so already, you need to make the `start.sh` script executable. Run this command from the project's root directory:
    ```bash
    chmod +x server/start.sh
    ```

2.  **Run the Start Script:**
    To start both the backend (WebSocket) and frontend (HTTP) servers, execute the script:
    ```bash
    ./server/start.sh
    ```
    You will see output confirming that both servers are running.

## Step 3: Access the Application

Once the servers are running, you can access the application in your web browser.

- **Open your web browser** (Chrome is recommended) and navigate to:
  **[http://localhost:8000/index.html](http://localhost:8000/index.html)**

You can now interact with the application using your voice.

## Step 4: Stop the Application

When you are finished, you can stop both servers using the same script with the `stop` argument.

- **Run the Stop Command:**
  In your terminal, run the following command:
  ```bash
  ./server/start.sh stop
  ```
  This will find and terminate the server processes, freeing up the ports.

---

## How It Works: Project Structure

You may notice several Python files inside the `server/computer_agent/` directory. **These files are internal modules and are not meant to be run directly.** The main application server (`server.py`) automatically manages them.

Here is a brief overview:
-   **`server/server.py`**: This is the main backend server that handles WebSocket connections from the client. It listens for your voice commands.
-   **`server/computer_agent/runner.py`**: When you ask for a browser task, this script is responsible for launching and managing the browser automation process.
-   **`server/computer_agent/agent.py`**: This is the core of the computer agent. It communicates with the AI model to decide which actions to take based on your commands and the content of the screen.
-   **`server/computer_agent/computers/`**: This directory contains the code that directly controls the web browser (using the Playwright library).

All of these components are started and coordinated automatically when you run the `./server/start.sh` script. You do not need to interact with them individually.