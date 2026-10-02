import os
import json
import numpy as np
from PIL import Image
from pathlib import Path
import onnxruntime as ort

# Model paths
ONNX_MODEL_PATH = os.path.join("models", "agriguard_efficientnet_b0.onnx")
CLASS_MAP_PATH = os.path.join("models", "class_map.json")

CONFIDENCE_THRESHOLD = 60.0

# Singleton global cache for ONNX Inference Session & Class Map
_ONNX_SESSION = None
_CLASS_MAP = None


def load_saved_model():
    """
    Singleton Loader for ONNX EfficientNet-B0 Runtime Session.
    Ensures ONNX session is initialized ONCE on CPU (Memory Footprint ~35MB RAM).
    """
    global _ONNX_SESSION, _CLASS_MAP

    if _ONNX_SESSION is not None:
        return _ONNX_SESSION, _CLASS_MAP, "cpu"

    print("[ML Boot] Initializing ONNX Runtime CPU session (Ultra Low-Memory Mode <512MB RAM)...")

    # Load class map
    cmap_file = CLASS_MAP_PATH if os.path.exists(CLASS_MAP_PATH) else "ml/class_map.json"
    if os.path.exists(cmap_file):
        with open(cmap_file, "r") as f:
            _CLASS_MAP = json.load(f)
    else:
        _CLASS_MAP = {
            "0": "Corn___Gray_Leaf_Spot", "1": "Corn___Healthy", "2": "Corn___Rust",
            "3": "Rice___Blast", "4": "Rice___Brown_Spot", "5": "Rice___Healthy",
            "6": "Tomato___Early_Blight", "7": "Tomato___Healthy", "8": "Tomato___Late_Blight",
            "9": "Tomato___Leaf_Mold"
        }

    onnx_file = ONNX_MODEL_PATH if os.path.exists(ONNX_MODEL_PATH) else os.path.join("ml", "agriguard_efficientnet_b0.onnx")

    if not os.path.exists(onnx_file):
        raise FileNotFoundError(f"[ML Boot] ONNX Model file not found at {onnx_file}")

    # Set ONNX Runtime CPU execution provider with single thread for low RAM
    opts = ort.SessionOptions()
    opts.intra_op_num_threads = 1
    opts.inter_op_num_threads = 1
    opts.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL

    _ONNX_SESSION = ort.InferenceSession(onnx_file, sess_options=opts, providers=["CPUExecutionProvider"])
    
    print(f"[ML Boot] ONNX Session successfully loaded on CPU ({len(_CLASS_MAP)} classes). Singleton ready for inference.\n")
    return _ONNX_SESSION, _CLASS_MAP, "cpu"


def preprocess_image_numpy(image_input):
    """
    Matches torchvision Resize((224, 224)) + CenterCrop(224) + Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]).
    Returns NumPy float32 array of shape (1, 3, 224, 224).
    """
    if isinstance(image_input, (str, Path)):
        with Image.open(image_input) as img:
            img = img.convert("RGB")
            return _transform_pil_image(img)
    elif isinstance(image_input, Image.Image):
        img = image_input.convert("RGB")
        return _transform_pil_image(img)
    else:
        raise ValueError("Invalid image input format. Expected PIL Image or file path.")


def _transform_pil_image(img):
    w, h = img.size
    short_side = min(w, h)
    scale = 224.0 / short_side
    new_w, new_h = int(round(w * scale)), int(round(h * scale))
    img = img.resize((new_w, new_h), Image.Resampling.BILINEAR)

    left = (new_w - 224) // 2
    top = (new_h - 224) // 2
    img = img.crop((left, top, left + 224, top + 224))

    arr = np.array(img, dtype=np.float32) / 255.0
    mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
    std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
    arr = (arr - mean) / std

    arr = np.transpose(arr, (2, 0, 1))
    return np.expand_dims(arr, axis=0).astype(np.float32)


def softmax(x):
    e_x = np.exp(x - np.max(x, axis=1, keepdims=True))
    return e_x / e_x.sum(axis=1, keepdims=True)


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
    Accepts PIL Image or file path.
    Performs memory-optimized ONNX CPU inference.
    """
    session, class_map, _device = load_saved_model()

    input_data = preprocess_image_numpy(image_input)
    input_name = session.get_inputs()[0].name

    raw_output = session.run(None, {input_name: input_data})[0]
    probs = softmax(raw_output)[0]

    top_idx = int(np.argmax(probs))
    top_prob = float(probs[top_idx]) * 100.0

    raw_class = class_map.get(str(top_idx), class_map.get(top_idx, "Unknown"))
    crop, disease = parse_class_name(raw_class)

    all_probs = {}
    for idx_k, cls_v in class_map.items():
        k_int = int(idx_k)
        all_probs[cls_v] = round(float(probs[k_int]) * 100.0, 2)

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
