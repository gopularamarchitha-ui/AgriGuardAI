import os
import json
import glob
from pathlib import Path
from PIL import Image
import torch
from torch.utils.data import Dataset, DataLoader
from torchvision import transforms
from sklearn.model_selection import train_test_split

# Standard ImageNet normalization for EfficientNet-B0
IMAGE_SIZE = (224, 224)
TRAIN_TRANSFORMS = transforms.Compose([
    transforms.Resize(IMAGE_SIZE),
    transforms.RandomResizedCrop(224, scale=(0.8, 1.0)),
    transforms.RandomHorizontalFlip(),
    transforms.RandomRotation(15),
    transforms.ColorJitter(brightness=0.2, contrast=0.2),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
])

VAL_TRANSFORMS = transforms.Compose([
    transforms.Resize(IMAGE_SIZE),
    transforms.CenterCrop(224),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
])

TARGET_CLASSES = [
    "Corn___Gray_Leaf_Spot",
    "Corn___Healthy",
    "Corn___Rust",
    "Rice___Blast",
    "Rice___Brown_Spot",
    "Rice___Healthy",
    "Tomato___Early_Blight",
    "Tomato___Healthy",
    "Tomato___Late_Blight",
    "Tomato___Leaf_Mold"
]

class CropLeafDataset(Dataset):
    def __init__(self, image_paths, labels, transform=None):
        self.image_paths = image_paths
        self.labels = labels
        self.transform = transform

    def __len__(self):
        return len(self.image_paths)

    def __getitem__(self, idx):
        path = self.image_paths[idx]
        label = self.labels[idx]
        image = Image.open(path).convert("RGB")
        if self.transform:
            image = self.transform(image)
        return image, label

def scan_and_map_dataset(dataset_root, output_class_map_path="ml/class_map.json"):
    """
    Scans dataset_root folder structure, maps subfolders to target classes,
    counts images, checks for zero-image classes, and saves class mapping.
    """
    root_path = Path(dataset_root)
    if not root_path.exists():
        raise FileNotFoundError(f"Dataset root folder {dataset_root} does not exist.")

    discovered_folders = [f.name for f in root_path.iterdir() if f.is_dir()]
    print(f"[Dataset Discovery] Found {len(discovered_folders)} subdirectories in {dataset_root}:")
    for df in discovered_folders:
        print(f"  - {df}")

    class_to_idx = {cls_name: i for i, cls_name in enumerate(sorted(TARGET_CLASSES))}
    mapped_samples = []
    class_counts = {cls_name: 0 for cls_name in TARGET_CLASSES}
    unmapped_folders = []

    for folder_name in discovered_folders:
        folder_path = root_path / folder_name
        # Match folder_name to target class (exact or normalized match)
        matched_class = None
        for target in TARGET_CLASSES:
            if target.lower() in folder_name.lower() or folder_name.lower() in target.lower():
                matched_class = target
                break

        if matched_class:
            images = glob.glob(str(folder_path / "*.[jJ][pP][gG]")) + \
                     glob.glob(str(folder_path / "*.[jJ][pP][eE][gG]")) + \
                     glob.glob(str(folder_path / "*.[pP][nN][gG]"))
            count = len(images)
            class_counts[matched_class] += count
            for img_p in images:
                mapped_samples.append((img_p, class_to_idx[matched_class]))
        else:
            unmapped_folders.append(folder_name)

    print("\n[Dataset Mapping Summary]")
    print(f"Mapped classes image counts:")
    for cls_name, count in class_counts.items():
        print(f"  - {cls_name}: {count} images")

    if unmapped_folders:
        print(f"Unmapped folders ignored: {unmapped_folders}")

    # Check for empty classes
    empty_classes = [c for c, count in class_counts.items() if count == 0]
    if empty_classes:
        raise ValueError(f"Dataset validation failed! The following target classes have ZERO images: {empty_classes}")

    # Save class map (idx -> name)
    idx_to_class = {i: c for c, i in class_to_idx.items()}
    os.makedirs(Path(output_class_map_path).parent, exist_ok=True)
    with open(output_class_map_path, "w") as f:
        json.dump(idx_to_class, f, indent=2)

    print(f"[Dataset Mapping] Class mapping saved to {output_class_map_path}")
    return mapped_samples, class_to_idx, idx_to_class

def create_data_loaders(mapped_samples, batch_size=32, num_workers=0):
    """
    Splits samples into train/val/test (80/10/10) with stratification and creates PyTorch DataLoaders.
    """
    paths = [s[0] for s in mapped_samples]
    labels = [s[1] for s in mapped_samples]

    # Stratified split: Train (80%) and Temp (20%)
    train_paths, temp_paths, train_labels, temp_labels = train_test_split(
        paths, labels, test_size=0.2, stratify=labels, random_state=42
    )

    # Split Temp into Val (10%) and Test (10%)
    val_paths, test_paths, val_labels, test_labels = train_test_split(
        temp_paths, temp_labels, test_size=0.5, stratify=temp_labels, random_state=42
    )

    train_ds = CropLeafDataset(train_paths, train_labels, transform=TRAIN_TRANSFORMS)
    val_ds = CropLeafDataset(val_paths, val_labels, transform=VAL_TRANSFORMS)
    test_ds = CropLeafDataset(test_paths, test_labels, transform=VAL_TRANSFORMS)

    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True, num_workers=num_workers)
    val_loader = DataLoader(val_ds, batch_size=batch_size, shuffle=False, num_workers=num_workers)
    test_loader = DataLoader(test_ds, batch_size=batch_size, shuffle=False, num_workers=num_workers)

    return train_loader, val_loader, test_loader, (test_paths, test_labels)
