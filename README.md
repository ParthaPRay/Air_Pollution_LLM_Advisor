# Air Pollution LLM Advisor

**Author**: Partha Pratim Ray  
**Date**: 24 June 2025  
**Email**: parthapratimray1986@gmail.com

---

## 📖 Project Overview

This project integrates:

- **Live air quality data** from the Open-Meteo API
- **Large Language Model (LLM)** reasoning using a locally hosted Ollama server
- **Interactive map** with Folium visualization
- **Conversational interface** using Gradio chatbot
- **Persistent CSV logging** of all data, including model metrics

The system provides both real-time pollution data and expert-like environmental health advice using a locally running LLM model. It allows users to:

- Search for any Indian city location
- Get air quality data visualized and summarized
- Query an LLM for health impact advice on the air quality
- Log all interactions (first LLM advice only) into a CSV file for research and future analysis

---

## 🌐 Features

- Live AQI data retrieval from Open-Meteo
- PM2.5, PM10, CO, NO2, SO2, O3, AOD, Dust, UV Index, Methane readings
- Folium-based India map with markers
- Gradio UI with full interactive chat
- Uses **Ollama LLM** (local deployment) to answer health queries
- First LLM interaction logged into `llm_aqi_log.csv` with full model metrics:
    - `total_duration`, `load_duration`, `prompt_eval_count`, `prompt_eval_duration`, `eval_count`, `eval_duration`, `tokens_per_second`
- After initial LLM analysis, user can continue chatting but no further logs are generated (only first LLM call is logged)
- Fully edge-deployable with Raspberry Pi or local laptop server running Ollama

---

## 🔧 Requirements

- Python 3.10 or newer
- Ollama server installed and running locally (https://ollama.com/)
- Models loaded inside Ollama (e.g., `granite3.1-moe`, `deepseek-r1`, `qwen3`, etc.)

---

## 🔑 Installation

Clone this repository:

```bash
git clone https://github.com/yourusername/air-pollution-llm-advisor.git
cd air-pollution-llm-advisor
````

Create virtual environment (recommended):

```bash
python3 -m venv venv
source venv/bin/activate
```

Install Python dependencies:

```bash
pip install -r requirements.txt
```

---

## 🔑 Running Ollama Server

Install Ollama on your host machine:

```bash
https://ollama.com/download
```

Load your desired model(s) into Ollama:

```bash
ollama run granite3.1-moe
# or 
ollama run deepseek-r1
```

Ensure Ollama API is available at:

```
http://localhost:11434/
```

If you're using a remote Ollama server, edit this line in the code:

```python
OLLAMA_IP = "192.168.x.x"  # your Ollama host IP
OLLAMA_PORT = "11434"
```

---

## 🚀 Launching the Application

Start your Gradio UI by running:

```bash
python app.py
```

By default, it launches at:

```
http://0.0.0.0:7860
```

---

## 📝 Output File

The application creates a log file `llm_aqi_log.csv` containing:

* Timestamp
* Location & Coordinates
* All pollutant values (cleaned: no units)
* Chosen LLM model
* LLM generated response
* Ollama model metrics

Example:

| timestamp | location | lat | lon | PM2.5 | PM10 | ... | llm\_response | total\_duration | load\_duration | ... |
| --------- | -------- | --- | --- | ----- | ---- | --- | ------------- | --------------- | -------------- | --- |

---

## 📦 requirements.txt

```text
gradio==4.27.0
folium==0.15.1
requests==2.31.0
```

---

## ⚠️ Notes

* The first click on "**Ask LLM for Pollution Analysis**" triggers CSV logging.
* After that, multiple chats can continue but only the first advice gets logged.
* Units (μg/m³, ppm, mg/m³) are automatically stripped before logging.
* Compatible with any Ollama model that supports `/api/generate` or `/api/chat` endpoints.
* Thinking mode is disabled in Ollama calls (`"think": false`) for faster responses.

---
## 🔒 License

MIT License (You can specify if applicable)

---

## 📄 Citation

If you use this work, please cite:

```bibtex
@misc{ray2025airpollution,
  author = {Partha Pratim Ray},
  title = {Air Pollution LLM Advisor},
  year = {2025},
  month = {June},
  url = {https://github.com/yourusername/air-pollution-llm-advisor},
  note = {Version 1.0},
  howpublished = {GitHub repository},
}


