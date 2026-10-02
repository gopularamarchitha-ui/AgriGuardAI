import sys
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

from agent.agriguard_agent import AgriGuardAgent

agent = AgriGuardAgent()
print("Testing Voice Query Agent workflow...")

res_te = agent.run_voice_query(
    question="నా టమాటా ఆకుల మీద నల్లటి మచ్చలు వస్తున్నాయి. ఏం చేయాలి?",
    city="Hyderabad",
    language="Telugu"
)

print("\n================ VOICE QUERY TEST (TELUGU) ================")
print("Status:", res_te.get("status"))
print("Question:", res_te.get("question"))
print("Telugu Summary:", res_te.get("telugu_advisory", {}).get("summary") if res_te.get("telugu_advisory") else res_te.get("advisory", {}).get("summary"))
print("Audio Path:", res_te.get("audio_path"))
print("Weather City:", res_te.get("weather", {}).get("city"))
print("============================================================\n")

res_en = agent.run_voice_query(
    question="There are brown spots on my tomato leaves. What should I do?",
    city="Vijayawada",
    language="English"
)

print("\n================ VOICE QUERY TEST (ENGLISH) ================")
print("Status:", res_en.get("status"))
print("Question:", res_en.get("question"))
print("English Summary:", res_en.get("advisory", {}).get("summary"))
print("Audio Path:", res_en.get("audio_path"))
print("============================================================\n")
