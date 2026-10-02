import os
import json
from flask import Flask, render_template, request, jsonify, send_from_directory
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from ml.predict import load_saved_model
from agent.agriguard_agent import AgriGuardAgent

app = Flask(__name__, template_folder="templates", static_folder="static")

# Ensure required directories exist
os.makedirs("outputs", exist_ok=True)
os.makedirs("models", exist_ok=True)

# Restore or initialize EfficientNet-B0 model on server boot
print("[App Boot] Initializing AgriGuard AI backend service...")
try:
    _model, _class_map, _device = load_saved_model()
    print(f"[App Boot] EfficientNet-B0 Model loaded on device '{_device}' with {len(_class_map)} classes.")
except Exception as e:
    print(f"[App Boot] Warning during model initialization: {e}")

# Global Agent instance
agent = AgriGuardAgent()

@app.route("/")
def index():
    """Renders main AgriGuard AI Web Interface."""
    return render_template("index.html")

@app.route("/analyze", methods=["POST"])
def analyze_crop():
    """
    Primary API endpoint for AgriGuard AI Agent analysis.
    Accepts crop image (upload or webcam snapshot), city, and language.
    Executes 12-step autonomous agent workflow and returns complete JSON output.
    """
    if "image" not in request.files:
        return jsonify({"status": "ERROR", "message": "No leaf image uploaded."}), 400

    file = request.files["image"]
    city = request.form.get("city", "Hyderabad")
    language = request.form.get("language", "English")

    if file.filename == "":
        return jsonify({"status": "ERROR", "message": "Selected image file is empty."}), 400

    # Save temporary input file
    temp_input_path = os.path.join("outputs", "temp_input.jpg")
    file.save(temp_input_path)

    try:
        result = agent.run(temp_input_path, city=city, language=language)
        return jsonify(result)
    except Exception as e:
        print(f"[App Route /analyze] Exception during agent execution: {e}")
        return jsonify({
            "status": "ERROR",
            "message": f"An error occurred during AgriGuard Agent execution: {str(e)}"
        }), 500

@app.route("/voice_query", methods=["POST"])
def voice_query():
    """
    API endpoint for Farmer Voice & Text Questions.
    Accepts spoken or typed question, city, and language.
    Executes RAG search, weather retrieval, Gemini advisory, and gTTS audio generation.
    """
    data = request.get_json(silent=True) or request.form
    question = data.get("question", "").strip()
    city = data.get("city", "Hyderabad")
    language = data.get("language", "Telugu")
    crop = data.get("crop", None)

    if not question:
        return jsonify({"status": "ERROR", "message": "No question text provided."}), 400

    try:
        result = agent.run_voice_query(question=question, city=city, language=language, crop=crop)
        return jsonify(result)
    except Exception as e:
        print(f"[App Route /voice_query] Exception: {e}")
        return jsonify({
            "status": "ERROR",
            "message": f"An error occurred while processing voice question: {str(e)}"
        }), 500

@app.route("/outputs/<path:filename>")
def serve_outputs(filename):
    """Serves generated audio files (MP3s) and persistent output artifacts."""
    return send_from_directory("outputs", filename)

@app.route("/health")
def health_check():
    """System health check endpoint."""
    model, class_map, device = load_saved_model()
    return jsonify({
        "status": "HEALTHY",
        "service": "AgriGuard AI — Intelligent Crop Disease Diagnosis & Advisory Agent",
        "device": str(device),
        "num_classes": len(class_map),
        "supported_classes": list(class_map.values())
    })

if __name__ == "__main__":
    print("\n========================================================")
    print(" AGRIGUARD AI AGENT WEB APPLICATION RUNNING ")
    print(" Access Web UI at: http://localhost:5000 ")
    print("========================================================\n")
    app.run(host="0.0.0.0", port=5000, debug=False)
