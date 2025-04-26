# BundestAIkes
Automated pipeline to generate short form video content based on recordings of plenary session of the Bundestag.

## Prerequisites

- Python 3.10 or higher
- ffmpeg (for video/audio processing)
- sox (for audio splitting)
- uv (Python package manager)

### Installing Prerequisites

#### macOS
```bash
brew install ffmpeg sox
pip install uv
```

#### Ubuntu/Debian
```bash
sudo apt-get update
sudo apt-get install ffmpeg sox
pip install uv
```

## Installation

1. Clone the repository:
```bash
git clone https://github.com/nifleisch/BundestAIkes.git
cd BundestAIkes
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies using uv:
```bash
uv pip install -e .
```

4. Create a `.env` file in the project root with your API keys:
```
OPENAI_API_KEY=your_openai_api_key
ASSEMBLYAI_API_KEY=your_assemblyai_api_key
```
