# Ralph Ollama Web UI

A simple web interface to test and verify your Ollama integration is working correctly.

## Features

- ✅ Real-time connection status to Ollama server
- ✅ List available models
- ✅ Send prompts and see responses
- ✅ Task-based model selection
- ✅ System prompt support
- ✅ Token usage display
- ✅ Beautiful, modern UI

## Quick Start

### 1. Install Dependencies

```bash
# From project root
pip install -r requirements.txt
```

### 2. Make Sure Ollama is Running

```bash
# Start Ollama server (in a separate terminal)
ollama serve
```

### 3. Start the UI Server

```bash
# From project root
python3 ui/app.py
```

### 4. Open in Browser

Open your browser and go to:
```
http://localhost:5001
```

**Note:** Port 5001 is used by default (port 5000 is often used by AirPlay on macOS).  
To use a different port, set the `FLASK_PORT` environment variable:
```bash
FLASK_PORT=8080 python3 ui/app.py
```

## Usage

1. **Check Connection**: The status bar at the top shows if Ollama is connected
2. **Select Model**: Choose a specific model or let it auto-select based on task type
3. **Choose Task Type**: Select a task type (implementation, testing, etc.) for automatic model selection
4. **Add System Prompt** (optional): Provide context for the AI
5. **Enter Your Prompt**: Type what you want to ask
6. **Send**: Click "Send to Ollama" and watch the response appear

## What You'll See

- **Connection Status**: Green dot = connected, Red dot = not connected
- **Server Info**: Shows the Ollama server URL
- **Available Models**: Dropdown shows all models you have installed
- **Response**: The AI's response appears in real-time
- **Metadata**: Model used, provider, and token counts

## Troubleshooting

### "Client not initialized" Error

Make sure you're running from the project root directory and that `config/ollama-config.json` exists.

### "Ollama server is not running"

Start Ollama in a separate terminal:
```bash
ollama serve
```

### Port Already in Use

The default port is 5001. To use a different port:
```bash
FLASK_PORT=8080 python3 ui/app.py
```

### No Models Available

Pull a model first:
```bash
ollama pull llama3.2
```

## API Endpoints

The UI uses these API endpoints:

- `GET /api/status` - Get connection status and available models
- `POST /api/generate` - Generate a response from Ollama
- `GET /api/models` - List available models

You can also use these endpoints directly from other applications.

---

**Enjoy testing your Ollama integration!** 🚀
