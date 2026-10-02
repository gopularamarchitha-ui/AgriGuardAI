import os
import json
import torch
import torch.nn as nn
from torch.optim import AdamW
from sklearn.metrics import classification_report, confusion_matrix, precision_recall_fscore_support, accuracy_score

from ml.model import build_efficientnet_b0, freeze_features, get_device
from ml.dataset import scan_and_map_dataset, create_data_loaders

def save_artifacts(model, class_map, history, metrics=None, save_dir="models"):
    """Saves model checkpoints, class map, history and test metrics to local and Drive directories."""
    os.makedirs(save_dir, exist_ok=True)
    
    # Also save to Google Drive if mounted
    drive_dir = "/content/drive/MyDrive/AgriGuard_AI/models"
    save_dirs = [save_dir]
    if os.path.exists("/content/drive/MyDrive"):
        os.makedirs(drive_dir, exist_ok=True)
        save_dirs.append(drive_dir)

    for d in save_dirs:
        # Save model state dict
        torch.save(model.state_dict(), os.path.join(d, "agriguard_efficientnet_b0.pt"))
        torch.save({"model_state_dict": model.state_dict()}, os.path.join(d, "best_classifier.pt"))
        
        # Save class map
        with open(os.path.join(d, "class_map.json"), "w") as f:
            json.dump(class_map, f, indent=2)

        # Save training history
        with open(os.path.join(d, "training_history.json"), "w") as f:
            json.dump(history, f, indent=2)

        if metrics:
            with open(os.path.join(d, "test_metrics.json"), "w") as f:
                json.dump(metrics, f, indent=2)

    print(f"[PERSISTENCE] Checkpoints and artifacts saved successfully to {save_dirs}")

def train_one_epoch(model, dataloader, criterion, optimizer, device):
    model.train()
    running_loss = 0.0
    correct = 0
    total = 0

    for images, labels in dataloader:
        images, labels = images.to(device), labels.to(device)
        optimizer.zero_grad()
        outputs = model(images)
        loss = criterion(outputs, labels)
        loss.backward()
        optimizer.step()

        running_loss += loss.item() * images.size(0)
        _, preds = torch.max(outputs, 1)
        correct += torch.sum(preds == labels.data).item()
        total += labels.size(0)

    epoch_loss = running_loss / total
    epoch_acc = (correct / total) * 100.0
    return epoch_loss, epoch_acc

def evaluate(model, dataloader, criterion, device):
    model.eval()
    running_loss = 0.0
    correct = 0
    total = 0
    all_preds = []
    all_labels = []

    with torch.no_grad():
        for images, labels in dataloader:
            images, labels = images.to(device), labels.to(device)
            outputs = model(images)
            loss = criterion(outputs, labels)

            running_loss += loss.item() * images.size(0)
            _, preds = torch.max(outputs, 1)
            correct += torch.sum(preds == labels.data).item()
            total += labels.size(0)

            all_preds.extend(preds.cpu().numpy())
            all_labels.extend(labels.cpu().numpy())

    epoch_loss = running_loss / total if total > 0 else 0.0
    epoch_acc = (correct / total) * 100.0 if total > 0 else 0.0
    return epoch_loss, epoch_acc, all_preds, all_labels

def run_training_pipeline(dataset_dir="dataset", epochs_stage1=5, epochs_stage2=5, batch_size=32):
    """
    Executes full 2-Stage training pipeline:
    Stage 1: Frozen feature extractor, train head only.
    Stage 2: Unfrozen features, fine-tune all layers with reduced LR.
    Evaluates on test set and persists model artifacts.
    """
    device = get_device()
    print(f"[Training Pipeline] Using device: {device}")

    mapped_samples, class_to_idx, idx_to_class = scan_and_map_dataset(dataset_dir)
    train_loader, val_loader, test_loader, (test_paths, test_labels) = create_data_loaders(mapped_samples, batch_size=batch_size)

    num_classes = len(idx_to_class)
    model = build_efficientnet_b0(num_classes=num_classes, pretrained=True).to(device)
    criterion = nn.CrossEntropyLoss()

    history = {"stage1": [], "stage2": []}
    best_val_acc = 0.0

    # STAGE 1: Train Head Only
    print("\n=================== STAGE 1: Training Classifier Head ===================")
    freeze_features(model, freeze=True)
    optimizer1 = AdamW(filter(lambda p: p.requires_grad, model.parameters()), lr=1e-3, weight_decay=1e-4)

    for epoch in range(1, epochs_stage1 + 1):
        tr_loss, tr_acc = train_one_epoch(model, train_loader, criterion, optimizer1, device)
        val_loss, val_acc, _, _ = evaluate(model, val_loader, criterion, device)
        print(f"Epoch {epoch}/{epochs_stage1} - Train Loss: {tr_loss:.4f}, Train Acc: {tr_acc:.2f}% | Val Loss: {val_loss:.4f}, Val Acc: {val_acc:.2f}%")
        history["stage1"].append({
            "epoch": epoch, "train_loss": tr_loss, "train_acc": tr_acc, "val_loss": val_loss, "val_acc": val_acc
        })
        if val_acc > best_val_acc:
            best_val_acc = val_acc
            save_artifacts(model, idx_to_class, history, save_dir="models")

    # STAGE 2: Fine-Tuning Full Model
    print("\n=================== STAGE 2: Fine-Tuning Full Architecture ===================")
    freeze_features(model, freeze=False)
    optimizer2 = AdamW(model.parameters(), lr=1e-4, weight_decay=1e-4)

    for epoch in range(1, epochs_stage2 + 1):
        tr_loss, tr_acc = train_one_epoch(model, train_loader, criterion, optimizer2, device)
        val_loss, val_acc, _, _ = evaluate(model, val_loader, criterion, device)
        print(f"Epoch {epoch}/{epochs_stage2} - Train Loss: {tr_loss:.4f}, Train Acc: {tr_acc:.2f}% | Val Loss: {val_loss:.4f}, Val Acc: {val_acc:.2f}%")
        history["stage2"].append({
            "epoch": epoch, "train_loss": tr_loss, "train_acc": tr_acc, "val_loss": val_loss, "val_acc": val_acc
        })
        if val_acc > best_val_acc:
            best_val_acc = val_acc
            save_artifacts(model, idx_to_class, history, save_dir="models")

    # TEST EVALUATION
    print("\n=================== TEST EVALUATION ===================")
    test_loss, test_acc, test_preds, test_targets = evaluate(model, test_loader, criterion, device)
    
    prec, rec, f1, _ = precision_recall_fscore_support(test_targets, test_preds, average='macro')
    cls_report = classification_report(test_targets, test_preds, target_names=[idx_to_class[str(i)] for i in range(num_classes)], output_dict=True)
    conf_mat = confusion_matrix(test_targets, test_preds).tolist()

    test_metrics = {
        "test_accuracy": round(test_acc, 2),
        "precision_macro": round(float(prec), 4),
        "recall_macro": round(float(rec), 4),
        "f1_macro": round(float(f1), 4),
        "classification_report": cls_report,
        "confusion_matrix": conf_mat
    }

    print(f"Test Accuracy: {test_acc:.2f}%")
    print(f"F1 Score (Macro): {f1:.4f}")

    save_artifacts(model, idx_to_class, history, test_metrics, save_dir="models")
    return model, test_metrics

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=str, default="dataset")
    args = parser.parse_args()
    run_training_pipeline(args.dataset)
