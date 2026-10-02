import os
import json
import torch
import torch.nn.functional as F
from PIL import Image
from torchvision import transforms
from pathlib import Path

from ml.model import build_efficientnet_b0, get_device

# Model persistent paths
PERSISTENT_DIRS = [
    "/content/drive/MyDrive/AgriGuard_AI/models",
    "models",
    "../models"
]

CONFIDENCE_THRESHOLD = 60.0

INFERENCE_TRANSFORMS = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.CenterCrop(224),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
])

_MODEL = None
_CLASS_MAP = None
_DEVICE = None

def find_checkpoint():
    """Locate existing model checkpoint across Google Drive and local project folders."""
    checkpoint_names = ["agriguard_efficientnet_b0.pt", "best_classifier.pt"]
    class_map_names = ["class_map.json"]

    for d in PERSISTENT_DIRS:
        for ckpt in checkpoint_names:
            path = os.path.join(d, ckpt)
            if os.path.exists(path):
                # find corresponding class map
                cmap_path = os.path.join(d, "class_map.json")
                if not os.path.exists(cmap_path):
                    cmap_path = "ml/class_map.json"
                return path, cmap_path
    return None, None

def load_saved_model():
    """
    Searches persistent storage for model checkpoint and class map.
    Loads checkpoint, restores model, sets eval mode, moves to CUDA/CPU.
    Returns (model, class_map, device).
    """
    global _MODEL, _CLASS_MAP, _DEVICE

    if _MODEL is not None:
        return _MODEL, _CLASS_MAP, _DEVICE

    _DEVICE = get_device()
    model_path, class_map_path = find_checkpoint()

    if not model_path or not os.path.exists(model_path):
        print("[MODEL RESTORE] No pre-existing checkpoint found in persistent storage.")
        print("[MODEL RESTORE] Initializing default EfficientNet-B0 model architecture.")
        
        # Load class map
        if os.path.exists("ml/class_map.json"):
            with open("ml/class_map.json", "r") as f:
                _CLASS_MAP = json.load(f)
        else:
            _CLASS_MAP = {
                "0": "Corn___Gray_Leaf_Spot", "1": "Corn___Healthy", "2": "Corn___Rust",
                "3": "Rice___Blast", "4": "Rice___Brown_Spot", "5": "Rice___Healthy",
                "6": "Tomato___Early_Blight", "7": "Tomato___Healthy", "8": "Tomato___Late_Blight",
                "9": "Tomato___Leaf_Mold"
            }
        
        num_classes = len(_CLASS_MAP)
        _MODEL = build_efficientnet_b0(num_classes=num_classes, pretrained=True)
        _MODEL.to(_DEVICE)
        _MODEL.eval()
        return _MODEL, _CLASS_MAP, _DEVICE

    # Load class map
    if os.path.exists(class_map_path):
        with open(class_map_path, "r") as f:
            _CLASS_MAP = json.load(f)
    else:
        _CLASS_MAP = {
            "0": "Corn___Gray_Leaf_Spot", "1": "Corn___Healthy", "2": "Corn___Rust",
            "3": "Rice___Blast", "4": "Rice___Brown_Spot", "5": "Rice___Healthy",
            "6": "Tomato___Early_Blight", "7": "Tomato___Healthy", "8": "Tomato___Late_Blight",
            "9": "Tomato___Leaf_Mold"
        }

    num_classes = len(_CLASS_MAP)
    _MODEL = build_efficientnet_b0(num_classes=num_classes, pretrained=False)
    
    checkpoint = torch.load(model_path, map_location=_DEVICE)
    if isinstance(checkpoint, dict) and "model_state_dict" in checkpoint:
        _MODEL.load_state_dict(checkpoint["model_state_dict"])
    else:
        _MODEL.load_state_dict(checkpoint)

    _MODEL.to(_DEVICE)
    _MODEL.eval()

    print("\n==========================================")
    print("MODEL RESTORED SUCCESSFULLY")
    print(f"Device: {_DEVICE}")
    print(f"Number of classes: {num_classes}")
    print(f"Model path: {model_path}")
    print("==========================================\n")

    return _MODEL, _CLASS_MAP, _DEVICE

def parse_class_name(class_str):
    """Parses 'Crop___Disease' string into crop and disease name."""
    if "___" in class_str:
        parts = class_str.split("___")
        crop = parts[0].replace("_", " ")
        disease = parts[1].replace("_", " ")
    else:
        crop = "Unknown Crop"
        disease = class_str.replace("_", " ")
    return crop, disease

def predict_image(image_input):
    """
    Accepts PIL Image, file path, or bytes.
    Returns dictionary with predicted class, crop, disease, confidence %, and all probabilities.
    """
    model, class_map, device = load_saved_model()

    if isinstance(image_input, (str, Path)):
        img = Image.open(image_input).convert("RGB")
    elif isinstance(image_input, Image.Image):
        img = image_input.convert("RGB")
    else:
        raise ValueError("Invalid image input format. Expected PIL Image or file path.")

    tensor = INFERENCE_TRANSFORMS(img).unsqueeze(0).to(device)

    with torch.no_grad():
        outputs = model(tensor)
        probs = F.softmax(outputs, dim=1)[0]

    top_idx = torch.argmax(probs).item()
    top_prob = probs[top_idx].item() * 100.0

    raw_class = class_map.get(str(top_idx), class_map.get(top_idx, "Unknown"))
    crop, disease = parse_class_name(raw_class)

    all_probs = {}
    for idx_k, cls_v in class_map.items():
        k_int = int(idx_k)
        all_probs[cls_v] = round(probs[k_int].item() * 100.0, 2)

    return {
        "prediction_raw": raw_class,
        "crop": crop,
        "disease": disease,
        "confidence": round(top_prob, 2),
        "all_probabilities": all_probs
    }

def safe_prediction(image_input, threshold=CONFIDENCE_THRESHOLD):
    """
    Runs model prediction and applies confidence gate.
    If confidence < threshold, returns status LOW_CONFIDENCE and prevents disease diagnosis.
    """
    pred_res = predict_image(image_input)

    if pred_res["confidence"] < threshold:
        return {
            "status": "LOW_CONFIDENCE",
            "message": f"Low prediction confidence ({pred_res['confidence']}% < {threshold}% threshold). Diagnostic safety gate engaged.",
            "crop": pred_res["crop"],
            "disease": "Uncertain / Low Confidence",
            "prediction": "Uncertain",
            "confidence": pred_res["confidence"],
            "all_probabilities": pred_res["all_probabilities"]
        }

    return {
        "status": "OK",
        "message": "Confidence threshold satisfied.",
        "crop": pred_res["crop"],
        "disease": pred_res["disease"],
        "prediction": f"Model prediction: {pred_res['crop']} - {pred_res['disease']}",
        "confidence": pred_res["confidence"],
        "all_probabilities": pred_res["all_probabilities"]
    }
