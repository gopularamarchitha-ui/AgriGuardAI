import json
from ml.model import build_efficientnet_b0
from ml.train import save_artifacts

with open('ml/class_map.json') as f:
    cmap = json.load(f)

model = build_efficientnet_b0(num_classes=len(cmap), pretrained=True)
save_artifacts(model, cmap, {'bootstrap': True}, save_dir='models')
print('Bootstrap model checkpoint saved to models/')
