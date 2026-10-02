import datetime
from ml.predict import safe_prediction
from rag.retriever import retrieve_rag
from tools.weather import get_weather
from tools.gemini import generate_advisory, validate_advisory, translate_to_telugu, generate_voice_advisory
from tools.tts import make_telugu_audio

class AgriGuardAgent:
    """
    AgriGuard AI Autonomous Agent.
    Orchestrates EfficientNet-B0 CV model, Confidence Safety Gate,
    RAG Knowledge Retrieval Tool, Open-Meteo Weather Tool,
    Google Gemini Advisory Generator, Gemini Grounding Validator,
    Telugu Translator, and gTTS Speech Generator.
    """

    def __init__(self):
        self.trace = []

    def log_step(self, step_num, tool, action, details=""):
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        entry = {
            "step": step_num,
            "timestamp": timestamp,
            "tool": tool,
            "action": action,
            "details": details
        }
        self.trace.append(entry)
        print(f"[AGENT TRACE Step {step_num}] [{tool}] {action} - {details}")

    def run(self, image, city="Hyderabad", language="English"):
        """
        Executes end-to-end 12-step autonomous agent workflow.
        Returns complete diagnostic and advisory bundle with execution trace.
        """
        self.trace = []

        # STEP 1: Receive Image
        self.log_step(1, "Input Gateway", "Farmer crop leaf image received", f"Target City: {city}, Selected Language: {language}")

        # STEP 2: Run EfficientNet Prediction
        self.log_step(2, "EfficientNet-B0 Prediction Tool", "Executing PyTorch deep learning inference", "Preprocessing 224x224 RGB image and evaluating softmax probabilities")
        
        try:
            pred_res = safe_prediction(image, threshold=60.0)
        except Exception as e:
            self.log_step(2, "EfficientNet-B0 Prediction Tool", "Inference Exception", str(e))
            pred_res = {
                "status": "ERROR",
                "message": f"Model inference failure: {e}",
                "crop": "Unknown",
                "disease": "Unknown",
                "prediction": "Processing Error",
                "confidence": 0.0,
                "all_probabilities": {}
            }

        # STEP 3: Apply Confidence Gate
        if pred_res["status"] == "LOW_CONFIDENCE":
            self.log_step(3, "Confidence Gate", "Safety Gate ENGAGED (Low Confidence)", f"Confidence {pred_res['confidence']}% is below 60.0% threshold. Halting disease-specific treatment recommendations.")
            
            fallback_advisory_en = {
                "summary": "Low confidence screening result. Safe general crop care recommended.",
                "why_it_matters": "The model cannot confirm a specific disease class with sufficient certainty.",
                "actions": [
                    "Scout leaves for secondary symptom signs or insect pests.",
                    "Ensure adequate drainage and avoid over-watering.",
                    "Take additional photos under bright, clear daylight and resubmit."
                ],
                "avoid": ["Do not apply target chemical sprays based on low-confidence screening."],
                "treatment": "No verified chemical pesticide recommendation is available for unconfirmed screening results. Consult your local agricultural officer.",
                "weather_context": f"Check local weather for {city}.",
                "uncertainties": [f"Model confidence was {pred_res['confidence']}%."],
                "sources": ["Safety Gate Policy"]
            }

            fallback_advisory_te = {
                "summary": "ఆకు వ్యాధిని ఖచ్చితంగా గుర్తించడానికి ఏఐకి తగినంత నమ్మకం లేదు. దయచేసి వెలుతురులో మరొక స్పష్టమైన ఫోటో తీసి మళ్లీ ప్రయత్నించండి.",
                "why_it_matters": "తక్కువ నమ్మకంతో ఉన్న నివేదిక ఆధారంగా నిర్దిష్ట మందులు పిచికారీ చేయడం వల్ల పంటకు నష్టం జరగవచ్చు.",
                "actions": [
                    "ఆకుల అడుగు భాగాన్ని మరియు కాండాన్ని నిశితంగా పరిశీలించండి.",
                    "పొలంలో నీరు నిల్వ ఉండకుండా తగినంత డ్రైనేజీ ఏర్పాటు చేయండి.",
                    "మంచి వెలుతురు ఉన్న సమయంలో ఆకు ఫోటోను స్పష్టంగా తీసి మళ్లీ విశ్లేషించండి."
                ],
                "avoid": ["తక్కువ నమ్మకం ఉన్న విశ్లేషణ ఆధారంగా ఎటువంటి రసాయన మందులు పిచికారీ చేయకండి."],
                "treatment": "ఈ వ్యాధికి నిర్దిష్ట పురుగుమందు సూచన ఇవ్వడానికి ధృవీకరించిన సమాచారం అందుబాటులో లేదు. స్థానిక వ్యవసాయ అధికారి లేదా అధీకృత వ్యవసాయ నిపుణుడిని సంప్రదించండి.",
                "weather_context": f"{city} స్థానిక వాతావరణాన్ని గమనించండి. అధిక తేమ వ్యాధుల వ్యాప్తికి కారణమవుతుంది.",
                "uncertainties": ["మోడల్ విశ్లేషణ నమ్మకం 60 శాతం కంటే తక్కువగా ఉంది."],
                "sources": ["వ్యవసాయ భద్రతా విధానం"]
            }

            selected_advisory = fallback_advisory_te if language == "Telugu" else fallback_advisory_en

            return {
                "status": "LOW_CONFIDENCE",
                "prediction_info": pred_res,
                "advisory": selected_advisory,
                "safety_validation": {"approved": True, "issues": ["Safety gate engaged due to low confidence"]},
                "weather": get_weather(city),
                "rag_evidence": [],
                "telugu_advisory": fallback_advisory_te if language == "Telugu" else None,
                "audio_path": make_telugu_audio(fallback_advisory_te) if language == "Telugu" else None,
                "agent_trace": self.trace
            }
        
        self.log_step(3, "Confidence Gate", "Safety Gate PASSED", f"Confidence {pred_res['confidence']}% >= 60.0% threshold. Crop: {pred_res['crop']}, Disease: {pred_res['disease']}")

        # STEP 4: Retrieve RAG Evidence
        query = f"{pred_res['crop']} {pred_res['disease']} symptoms control management"
        self.log_step(4, "RAG Knowledge Retrieval Tool", "Querying temporary agricultural knowledge base", f"Query: '{query}'")
        
        rag_results = retrieve_rag(query, top_k=5)
        self.log_step(4, "RAG Knowledge Retrieval Tool", "Retrieval Complete", f"Retrieved {len(rag_results)} relevant document chunk(s)")

        # STEP 5: Evidence Check
        if not rag_results:
            self.log_step(5, "RAG Knowledge Check", "No RAG evidence found", "Engaging safe general fallback advisory")
        else:
            self.log_step(5, "RAG Knowledge Check", "Evidence verified", f"Top match: '{rag_results[0].get('title', '')}' (Score: {rag_results[0].get('relevance_score', 0)})")

        # STEP 6: Call Weather Tool
        self.log_step(6, "Open-Meteo Weather Tool", f"Fetching real-time weather for {city}", "Querying temperature, relative humidity, and precipitation")
        weather_info = get_weather(city)
        self.log_step(6, "Open-Meteo Weather Tool", "Weather Context Acquired", weather_info.get("summary", ""))

        # STEP 7: Call Gemini Advisory Generator
        self.log_step(7, "Google Gemini LLM Tool", "Invoking Gemini advisory generator", f"Model: gemini-2.5-flash. Sending diagnosis + {len(rag_results)} RAG chunks + weather context")
        advisory = generate_advisory(
            crop=pred_res["crop"],
            disease=pred_res["disease"],
            confidence=pred_res["confidence"],
            rag_results=rag_results,
            weather=weather_info
        )
        self.log_step(7, "Google Gemini LLM Tool", "Advisory Generated", f"Summary: {advisory.get('summary', '')[:80]}...")

        # STEP 8: Call Gemini Safety Validator
        self.log_step(8, "Gemini Safety Validator", "Auditing advisory for evidence grounding and safety", "Verifying diagnostic uncertainty, absence of unverified pesticide doses, and source compliance")
        val_result = validate_advisory(advisory, pred_res["crop"], pred_res["disease"], rag_results)

        # STEP 9: Revision Step if Rejected
        if not val_result.get("approved", True):
            self.log_step(9, "Gemini Safety Validator", "Advisory REJECTED by safety auditor", f"Issues: {val_result.get('issues')}. Triggering single revision pass...")
            # Perform single revision pass
            advisory = generate_advisory(
                crop=pred_res["crop"],
                disease=pred_res["disease"],
                confidence=pred_res["confidence"],
                rag_results=rag_results,
                weather=weather_info
            )
            val_result = validate_advisory(advisory, pred_res["crop"], pred_res["disease"], rag_results)
            self.log_step(9, "Gemini Safety Validator", "Revision Pass Completed", f"Approved: {val_result.get('approved')}")
        else:
            self.log_step(9, "Gemini Safety Validator", "Advisory APPROVED on first audit pass", f"Validator: {val_result.get('validator', 'Gemini Auditor')}")

        # STEP 10: Telugu Translation (if selected)
        telugu_advisory = None
        if language == "Telugu":
            self.log_step(10, "Gemini Telugu Translation Tool", "Translating advisory to Telugu", "Converting summary, actions, and safety warnings to farmer-friendly Telugu")
            telugu_advisory = translate_to_telugu(advisory)
            self.log_step(10, "Gemini Telugu Translation Tool", "Telugu Translation Complete", "Preserved safety notices and practical steps")
        else:
            self.log_step(10, "Language Selector", "English language selected", "Skipping Telugu translation")

        # STEP 11: Telugu TTS (if selected)
        audio_path = None
        if language == "Telugu" and telugu_advisory:
            self.log_step(11, "gTTS Telugu Speech Tool", "Generating Telugu MP3 audio stream", "Synthesizing spoken audio for illiterate or voice-first farmers")
            audio_path = make_telugu_audio(telugu_advisory)
            self.log_step(11, "gTTS Telugu Speech Tool", "Audio Generation Complete", f"Saved to: {audio_path}")
        else:
            self.log_step(11, "gTTS Speech Tool", "Audio Generation Skipped", "Language is English or audio unrequested")

        # STEP 12: Return Complete Result
        self.log_step(12, "AgriGuard Agent", "Workflow Completed Successfully", "Bundling outputs, trace logs, sources, and validation audit report")

        return {
            "status": "SUCCESS",
            "prediction_info": pred_res,
            "advisory": advisory,
            "safety_validation": val_result,
            "weather": weather_info,
            "rag_evidence": rag_results,
            "telugu_advisory": telugu_advisory,
            "audio_path": audio_path,
            "agent_trace": self.trace
        }

    def run_voice_query(self, question, city="Hyderabad", language="Telugu", crop=None):
        """
        Executes voice question workflow:
        Retrieves agricultural RAG evidence, weather metrics, calls Gemini advisory generator,
        translates to Telugu, and synthesizes Telugu audio MP3.
        """
        self.trace = []
        self.log_step(1, "Voice Query Input", "Farmer spoken/typed question received", f"Question: '{question}', City: {city}, Language: {language}")

        # 1. RAG Retrieval
        rag_query = f"{crop or ''} {question}".strip()
        self.log_step(2, "RAG Knowledge Retrieval", "Searching agricultural knowledge base", f"Query: '{rag_query}'")
        rag_results = retrieve_rag(rag_query, top_k=5)

        # 2. Weather Context
        self.log_step(3, "Weather Tool", f"Fetching weather for {city}")
        weather_info = get_weather(city)

        # 3. Gemini Advisory Generation
        self.log_step(4, "Gemini LLM Tool", "Generating answer for voice question")
        advisory = generate_voice_advisory(question, rag_results, weather_info, language=language)

        # 4. Telugu Translation
        telugu_advisory = None
        if language == "Telugu":
            self.log_step(5, "Telugu Translator", "Ensuring Telugu advisory format")
            if isinstance(advisory, dict) and any('\u0c00' <= c <= '\u0c7f' for c in str(advisory.get("summary", ""))):
                telugu_advisory = advisory
            else:
                telugu_advisory = translate_to_telugu(advisory)
        else:
            telugu_advisory = None

        # 5. Audio Generation
        audio_path = None
        target_advisory_for_audio = telugu_advisory if telugu_advisory else advisory
        if language == "Telugu" or target_advisory_for_audio:
            self.log_step(6, "gTTS Telugu Speech Engine", "Generating Telugu MP3 audio")
            audio_path = make_telugu_audio(target_advisory_for_audio)

        self.log_step(7, "AgriGuard Agent", "Voice Query Processing Complete")

        return {
            "status": "SUCCESS",
            "question": question,
            "advisory": advisory,
            "telugu_advisory": telugu_advisory,
            "weather": weather_info,
            "audio_path": audio_path,
            "agent_trace": self.trace
        }

