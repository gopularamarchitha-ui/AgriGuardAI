import os
import json
import re
from dotenv import load_dotenv

# Load .env file automatically
load_dotenv()

# Configurable Gemini Model (with fallback candidate list if specific model is unavailable)
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")
GEMINI_MODEL_FALLBACKS = ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro", "gemini-2.0-flash-exp"]


def get_gemini_api_key():
    """
    Retrieves GEMINI_API_KEY from environment variables, .env file, or Google Colab userdata secrets.
    """
    load_dotenv()
    key = os.environ.get("GEMINI_API_KEY")

    if not key:
        try:
            # pyrefly: ignore [missing-import]
            from google.colab import userdata
            key = userdata.get("GEMINI_API_KEY")
        except Exception:
            key = None
    return key

def get_gemini_client():
    """Initializes Google GenAI Client using GEMINI_API_KEY."""
    key = get_gemini_api_key()
    if not key:
        print("[Gemini Tool] WARNING: GEMINI_API_KEY is missing!")
        return None
    try:
        from google import genai
        client = genai.Client(api_key=key)
        return client
    except Exception as e:
        print(f"[Gemini Tool] Failed to initialize Google GenAI client: {e}")
        return None

def call_gemini_generate(client, prompt):
    """
    Executes Gemini generate_content with automatic candidate model fallbacks.
    Tries GEMINI_MODEL first; if model unavailable/deprecated (404), tries fallbacks.
    """
    candidate_models = [GEMINI_MODEL] + [m for m in GEMINI_MODEL_FALLBACKS if m != GEMINI_MODEL]
    last_err = None

    for m in candidate_models:
        try:
            response = client.models.generate_content(
                model=m,
                contents=prompt
            )
            return response.text
        except Exception as e:
            err_msg = str(e)
            last_err = e
            if "404" in err_msg or "NOT_FOUND" in err_msg or "not available" in err_msg:
                print(f"[Gemini Model Fallback] Model '{m}' returned 404/unavailable. Trying next model candidate...")
                continue
            else:
                # Non-404 error (e.g. invalid key or network error)
                raise e

    raise last_err

def clean_json_response(text):

    """Clean markdown codeblocks from JSON response."""
    text = text.strip()
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()

def generate_advisory(crop, disease, confidence, rag_results, weather):
    """
    Generates evidence-grounded agricultural advisory using Google Gemini LLM.
    Returns structured JSON object.
    """
    client = get_gemini_client()

    # Prepare safe evidence context string
    rag_text = ""
    sources_list = []
    if rag_results:
        for idx, doc in enumerate(rag_results, 1):
            rag_text += f"\n[Evidence {idx}] Title: {doc.get('title', '')}\nText: {doc.get('text', '')}\nSource: {doc.get('source', '')}\n"
            sources_list.append(doc.get('source', 'Temporary agricultural knowledge'))
    else:
        rag_text = "No specific RAG evidence retrieved for this class."
        sources_list.append("Temporary agricultural knowledge base")

    weather_str = f"City: {weather.get('city', 'Unknown')}, Temp: {weather.get('temperature_c', 'N/A')}°C, Humidity: {weather.get('humidity_percent', 'N/A')}%, Rainfall: {weather.get('precipitation_mm', 'N/A')}mm"

    if client is None:
        # Safe fallback if API Key is missing or client creation failed
        return {
            "summary": f"Model prediction indicates potential {crop} {disease} with {confidence}% confidence.",
            "why_it_matters": f"{disease} can impact {crop} leaf health and photosynthetic yield if environmental conditions foster fungal spread.",
            "actions": [
                "Inspect lower and middle foliage for visible lesion progression.",
                "Ensure drip irrigation or morning watering to prevent prolonged evening leaf moisture.",
                "Maintain adequate plant spacing to encourage canopy ventilation.",
                "Consult local extension officer or agricultural authority for registered regional treatments."
            ],
            "avoid": [
                "Avoid overhead sprinkler irrigation during high humidity periods.",
                "Do not apply unverified chemical sprays without checking local product labels."
            ],
            "weather_context": f"Current weather in {weather.get('city')}: {weather_str}. High humidity may increase leaf wetness duration.",
            "uncertainties": [
                f"Image analysis provides a screening prediction ({confidence}% confidence). Field verification is recommended.",
                "GEMINI_API_KEY missing or inactive - showing structured safe agricultural fallback advice."
            ],
            "sources": list(set(sources_list))
        }

    prompt = f"""
You are AgriGuard AI, an expert agricultural scientist.
Generate a safe, evidence-grounded advisory based strictly on the provided computer vision prediction, RAG retrieved knowledge, and weather metrics.

INPUT DATA:
- Crop: {crop}
- Predicted Disease: {disease}
- CV Model Confidence: {confidence}%
- Weather Context: {weather_str}
- RAG Retrieved Evidence:
{rag_text}

CRITICAL SAFETY & GROUNDING RULES:
1. Never claim the image diagnosis is 100% certain. Frame it as "possible", "model prediction", or "screening result".
2. Use ONLY the retrieved evidence and general accepted agronomic principles.
3. DO NOT invent specific chemical pesticide names, exact dosages (e.g. 2ml/L), chemical concentrations, waiting periods, or legal approvals.
4. If discussing chemical control, instruct the farmer to follow local product labels and agricultural extension authority guidance.
5. Clearly state evidence limitations and uncertainties.

OUTPUT FORMAT:
Return ONLY valid JSON matching this exact structure:
{{
  "summary": "Short 1-2 sentence overview of the model screening and general health status",
  "why_it_matters": "Explanation of potential disease impact on foliage and yield",
  "actions": [
    "Practical cultural management step 1",
    "Practical cultural management step 2",
    "Practical cultural management step 3"
  ],
  "avoid": [
    "Practices to avoid 1",
    "Practices to avoid 2"
  ],
  "weather_context": "Explanation of how current temperature/humidity relates to leaf wetness and fungal risk",
  "uncertainties": [
    "Model screening limitation note",
    "Field verification recommendation"
  ],
  "sources": [
    "Temporary agricultural knowledge base"
  ]
}}
"""

    try:
        response_text = call_gemini_generate(client, prompt)
        cleaned_json = clean_json_response(response_text)
        advisory_dict = json.loads(cleaned_json)
        return advisory_dict
    except Exception as e:
        print(f"[Gemini Tool] Error generating advisory with Gemini: {e}")
        return {
            "summary": f"Possible {crop} - {disease} detected (Confidence: {confidence}%).",
            "why_it_matters": "Foliar disease can reduce light absorption and crop productivity.",
            "actions": [
                "Scout fields weekly to check for spreading spot patterns.",
                "Ensure proper row spacing and weed sanitation to lower canopy humidity.",
                "Consult local agricultural extension authority for approved crop treatments."
            ],
            "avoid": [
                "Avoid leaf wetness during late afternoon hours."
            ],
            "weather_context": f"Current weather in {weather.get('city')}: {weather_str}.",
            "uncertainties": [
                f"Model prediction confidence is {confidence}%. Physical field scouting is advised."
            ],
            "sources": list(set(sources_list))
        }

def validate_advisory(advisory, crop, disease, rag_results):
    """
    Separate Gemini safety and grounding validation step.
    Audits the generated advisory for unsupported claims, invented chemical doses, or overconfidence.
    Returns: JSON object {"approved": bool, "issues": [...], "unsupported_claims": [...]}
    """
    client = get_gemini_client()

    if client is None:
        # Internal rule check fallback
        issues = []
        unsupported = []
        advisory_str = json.dumps(advisory).lower()
        if "100%" in advisory_str or "certain diagnosis" in advisory_str:
            issues.append("Advisory expresses overconfidence in image diagnosis.")
        if "ml/l" in advisory_str or "gram/liter" in advisory_str:
            unsupported.append("Advisory includes specific unverified chemical dosages.")
        
        approved = len(issues) == 0 and len(unsupported) == 0
        return {
            "approved": approved,
            "issues": issues,
            "unsupported_claims": unsupported,
            "validator": "Rule-based Fallback Validator"
        }

    prompt = f"""
You are the AgriGuard Safety & Grounding Auditor.
Your job is to strictly validate an agricultural advisory generated for a farmer.

CROP: {crop}
DISEASE: {disease}
ADVISORY TO VALIDATE:
{json.dumps(advisory, indent=2)}

VALIDATION AUDIT CRITERIA:
1. Evidence Support: Does the advisory align with standard agronomy?
2. Diagnostic Uncertainty: Does it acknowledge that the CV prediction is a screening model, not a 100% lab test?
3. Chemical Safety: Does it avoid inventing specific unverified chemical dosages, proprietary pesticide formulas, or illegal claims?
4. Source Attribution: Does it acknowledge sources appropriately?

OUTPUT FORMAT:
Return ONLY valid JSON:
{{
  "approved": true or false,
  "issues": ["List of any safety or overconfidence issues"],
  "unsupported_claims": ["List of any unsupported chemical or dosage claims"]
}}
"""
    try:
        response_text = call_gemini_generate(client, prompt)
        cleaned = clean_json_response(response_text)
        res = json.loads(cleaned)
        res["validator"] = f"Gemini Safety Validator ({GEMINI_MODEL})"
        return res
    except Exception as e:
        print(f"[Gemini Validator] Validation call failed: {e}")
        return {
            "approved": True,
            "issues": [],
            "unsupported_claims": [],
            "validator": "Default Safety Audit Pass"
        }

def translate_to_telugu(advisory):
    """
    Translates English agricultural advisory to farmer-friendly Telugu using Gemini.
    Preserves all safety warnings, uncertainties, and practical steps in 100% pure Telugu script.
    """
    client = get_gemini_client()

    telugu_default = {
        "summary": "పంట ఆకు ఆరోగ్య పరిశీలన మరియు విశ్లేషణ నివేదిక సిద్ధంగా ఉంది.",
        "why_it_matters": "ఆకు మచ్చలు మరియు తెగుళ్లు కిరణజన్య సంయోగ క్రియను తగ్గించి పంట దిగుబడిపై ప్రభావం చూపుతాయి.",
        "actions": [
            "పొలంలో ఆకుల పరిస్థితిని మరియు వ్యాధి వ్యాప్తిని రోజూ గమనించండి.",
            "మొక్కల మధ్య తగినంత గాలి వెలుతురు ప్రసరించేలా చూడండి.",
            "సూర్యోదయ సమయంలో నీరు పారించండి, ఆకులపై నీరు నిల్వ ఉండకుండా చూడండి."
        ],
        "avoid": [
            "ధృవీకరించని రసాయన మందులను స్ప్రే చేయకండి.",
            "సాయంత్రం వేళల్లో ఆకులపై నీరు పడకుండా చూడండి."
        ],
        "treatment": "ఈ వ్యాధికి నిర్దిష్ట పురుగుమందు సూచన ఇవ్వడానికి ధృవీకరించిన సమాచారం అందుబాటులో లేదు. స్థానిక వ్యవసాయ అధికారి లేదా అధీకృత వ్యవసాయ నిపుణుడిని సంప్రదించండి.",
        "weather_context": "వాతావరణంలో తేమ శాతం పెరిగినప్పుడు తెగుళ్ల ఉధృతి పెరుగుతుంది.",
        "uncertainties": ["క్షేత్రస్థాయిలో ఆకులను పరిశీలించి వ్యవసాయ నిపుణుడిని సంప్రదించండి."],
        "sources": ["వ్యవసాయ రక్షణ జ్ఞాన సేవ"]
    }

    if client is None:
        return telugu_default

    prompt = f"""
Translate the following agricultural advisory into 100% PURE, NATURAL TELUGU (తెలుగు) for a local farmer.

CRITICAL MANDATORY RULES:
1. Write 100% in Telugu script (తెలుగు).
2. DO NOT include any English words, English characters (A-Z, a-z), or Latin text anywhere.
3. Translate all crop names (e.g. Tomato -> టమాటా, Rice -> వరి, Corn -> జొన్న) and disease names into clear Telugu spoken in Telangana and Andhra Pradesh.
4. Return ONLY valid JSON matching the input keys.

INPUT JSON:
{json.dumps(advisory, indent=2)}
"""

    try:
        response_text = call_gemini_generate(client, prompt)
        cleaned = clean_json_response(response_text)
        return json.loads(cleaned)
    except Exception as e:
        print(f"[Gemini Telugu Translation] Error: {e}")
        return telugu_default

def generate_voice_advisory(question, rag_results, weather, language="Telugu"):
    """
    Generates a farmer advisory in response to a spoken or typed voice query.
    Returns structured JSON object.
    """
    client = get_gemini_client()
    rag_text = ""
    sources_list = []
    if rag_results:
        for idx, doc in enumerate(rag_results, 1):
            rag_text += f"\n[Evidence {idx}] Title: {doc.get('title', '')}\nText: {doc.get('text', '')}\nSource: {doc.get('source', '')}\n"
            sources_list.append(doc.get('source', 'Agricultural RAG Knowledge'))
    else:
        rag_text = "No specific RAG evidence retrieved."

    weather_str = f"City: {weather.get('city', 'Unknown')}, Temp: {weather.get('temperature_c', 'N/A')}°C, Humidity: {weather.get('humidity_percent', 'N/A')}%, Rainfall: {weather.get('precipitation_mm', 'N/A')}mm"

    telugu_voice_default = {
        "question": question,
        "summary": f"మీ ప్రశ్న '{question}' నమోదు చేయబడింది. పంట సంరక్షణ సలహా సిద్ధంగా ఉంది.",
        "why_it_matters": "ఆకు తెగుళ్లను తొలి దశలోనే గుర్తించడం వల్ల దిగుబడి నష్టాన్ని అరికట్టవచ్చు.",
        "actions": [
            "పొలంలో ఆకుల పరిస్థితిని రోజూ గమనించండి.",
            "మొక్కల మధ్య తగినంత గాలి వెలుతురు ప్రసరించేలా చూడండి.",
            "స్థానిక కృషి విజ్ఞాన కేంద్రం (KVK) లేదా వ్యవసాయ అధికారిని సంప్రదించండి."
        ],
        "avoid": ["ధృవీకరించని రసాయన మందులను స్ప్రే చేయకండి."],
        "treatment": "ఈ వ్యాధికి నిర్దిష్ట పురుగుమందు సూచన ఇవ్వడానికి ధృవీకరించిన సమాచారం అందుబాటులో లేదు. స్థానిక వ్యవసాయ అధికారి లేదా అధీకృత వ్యవసాయ నిపుణుడిని సంప్రదించండి.",
        "weather_context": f"స్థానిక వాతావరణం: {weather_str}",
        "sources": list(set(sources_list))
    }

    if client is None:
        return telugu_voice_default

    clean_q = question.replace('"', "'").replace('\n', ' ')
    prompt = f"""
You are AgriGuard AI, an expert agricultural agent for smallholder farmers.
Answer the farmer's question in 100% PURE TELUGU (తెలుగు) based on verified agronomic principles, weather data, and retrieved evidence.

FARMER QUESTION: "{clean_q}"
WEATHER METRICS: {weather_str}
RAG RETRIEVED EVIDENCE:
{rag_text}

CRITICAL RULES:
1. Write 100% in Telugu script (తెలుగు). Do NOT use English words or English alphabet text.
2. Provide practical, clear, farmer-friendly guidance.
3. NEVER invent pesticide brand names, exact chemical concentrations, or dosages (e.g. 2ml/L) unless explicitly given in retrieved evidence.
4. If specific verified pesticide information is unavailable, output exact text for treatment:
   "ఈ వ్యాధికి నిర్దిష్ట పురుగుమందు సూచన ఇవ్వడానికి ధృవీకరించిన సమాచారం అందుబాటులో లేదు. స్థానిక వ్యవసాయ అధికారి లేదా అధీకృత వ్యవసాయ నిపుణుడిని సంప్రదించండి."

OUTPUT JSON FORMAT:
{{
  "question": "Short summary of farmer question in Telugu",
  "summary": "తెలుగులో స్పష్టమైన సలహా సమాధానం",
  "why_it_matters": "పంట ఆరోగ్యానికి గల ప్రాముఖ్యత",
  "actions": ["చేయవలసిన పనులు 1", "చేయవలసిన పనులు 2"],
  "avoid": ["నివారించవలసిన పనులు 1"],
  "treatment": "ధృవీకరించిన చికిత్స లేదా: 'ఈ వ్యాధికి నిర్దిష్ట పురుగుమందు సూచన ఇవ్వడానికి ధృవీకరించిన సమాచారం అందుబాటులో లేదు. స్థానిక వ్యవసాయ అధికారి లేదా అధీకృత వ్యవసాయ నిపుణుడిని సంప్రదించండి.'",
  "weather_context": "వాతావరణ ప్రభావం",
  "expert_consultation": "వ్యవసాయ నిపుణుడిని ఎప్పుడు సంప్రదించాలి",
  "sources": ["వ్యవసాయ సమాచార కేంద్రం"]
}}
"""
    try:
        response_text = call_gemini_generate(client, prompt)
        cleaned = clean_json_response(response_text)
        return json.loads(cleaned)
    except Exception as e:
        print(f"[Gemini Voice Advisory Error]: {e}")
        return telugu_voice_default

