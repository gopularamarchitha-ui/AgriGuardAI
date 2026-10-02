from PIL import Image, ImageDraw
import os
import sys

# Ensure UTF-8 output encoding for console
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

from agent.agriguard_agent import AgriGuardAgent

# Create a synthetic green leaf image for testing
test_img_path = "outputs/test_leaf.jpg"
os.makedirs("outputs", exist_ok=True)
img = Image.new("RGB", (224, 224), color=(34, 139, 34))
draw = ImageDraw.Draw(img)
draw.ellipse([50, 50, 170, 170], fill=(107, 142, 35))
img.save(test_img_path)

print(f"Created test leaf image at: {test_img_path}")

agent = AgriGuardAgent()
res = agent.run(test_img_path, city="Hyderabad", language="Telugu")

print("\n================ END-TO-END TEST RESULTS ================")
print("Status:", res.get("status"))
print("Crop:", res["prediction_info"].get("crop"))
print("Disease:", res["prediction_info"].get("disease"))
print("Confidence:", res["prediction_info"].get("confidence"), "%")
print("Weather Summary:", res["weather"].get("summary"))
print("Advisory Summary:", res["advisory"].get("summary"))
print("Safety Approved:", res["safety_validation"].get("approved"))
tel_sum = res.get("telugu_advisory", {}).get("summary") if res.get("telugu_advisory") else "N/A"
print("Telugu Summary:", tel_sum)
print("Audio Path:", res.get("audio_path"))
print("Trace Step Count:", len(res.get("agent_trace", [])))
print("=========================================================\n")
