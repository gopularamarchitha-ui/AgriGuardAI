import torch
import torch.nn as nn
from torchvision.models import efficientnet_b0, EfficientNet_B0_Weights

def build_efficientnet_b0(num_classes=10, pretrained=True):
    """
    Build EfficientNet-B0 model for crop disease classification.
    Replaces default ImageNet classifier head with num_classes outputs.
    """
    weights = EfficientNet_B0_Weights.DEFAULT if pretrained else None
    model = efficientnet_b0(weights=weights)
    
    # EfficientNet-B0 classifier head: Sequential(Dropout, Linear(1280, num_classes))
    in_features = model.classifier[1].in_features
    model.classifier = nn.Sequential(
        nn.Dropout(p=0.3, inplace=True),
        nn.Linear(in_features, num_classes)
    )
    return model

def freeze_features(model, freeze=True):
    """
    Freeze or unfreeze feature extractor layers for 2-stage training.
    Stage 1: freeze=True (train classifier head only)
    Stage 2: freeze=False (fine-tune feature extractor)
    """
    for param in model.features.parameters():
        param.requires_grad = not freeze

def get_device():
    """Return CUDA if available, else CPU."""
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")
