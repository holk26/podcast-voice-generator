from typing import Optional, Dict, List


def get_gpu_info() -> List[Dict]:
    import torch
    gpus = []
    if not torch.cuda.is_available():
        return gpus
    for i in range(torch.cuda.device_count()):
        props = torch.cuda.get_device_properties(i)
        gpus.append({
            "id": i,
            "name": props.name,
            "total_memory_gb": props.total_memory / (1024 ** 3),
            "compute_capability": f"{props.major}.{props.minor}"
        })
    return gpus


def get_vram_info(device_id: int = 0) -> Dict:
    import torch
    if not torch.cuda.is_available():
        return {"available": False}
    try:
        torch.cuda.set_device(device_id)
        total = torch.cuda.get_device_properties(device_id).total_memory / (1024 ** 3)
        reserved = torch.cuda.memory_reserved(device_id) / (1024 ** 3)
        allocated = torch.cuda.memory_allocated(device_id) / (1024 ** 3)
        free = total - allocated
        return {
            "available": True,
            "device_id": device_id,
            "total_gb": total,
            "allocated_gb": allocated,
            "reserved_gb": reserved,
            "free_gb": free,
        }
    except Exception as e:
        return {"available": False, "error": str(e)}


def estimate_vram_needed(engine: str, model_size: str = "default") -> float:
    estimates = {
        ("xtts", "default"): 4.0,
        ("bark", "small"): 4.0,
        ("bark", "medium"): 7.0,
        ("bark", "large"): 10.0,
    }
    return estimates.get((engine, model_size), 4.0)


def can_fit_model(device_id: int, engine: str, model_size: str = "default", safety_margin_gb: float = 2.0) -> bool:
    vram = get_vram_info(device_id)
    if not vram.get("available"):
        return False
    needed = estimate_vram_needed(engine, model_size) + safety_margin_gb
    return vram["free_gb"] >= needed


def select_best_device() -> str:
    import torch
    if not torch.cuda.is_available():
        return "cpu"
    best_id = 0
    best_free = -1
    for i in range(torch.cuda.device_count()):
        vram = get_vram_info(i)
        if vram.get("available") and vram["free_gb"] > best_free:
            best_free = vram["free_gb"]
            best_id = i
    return f"cuda:{best_id}"


def clear_gpu_cache() -> None:
    import torch
    if torch.cuda.is_available():
        torch.cuda.empty_cache()


def format_vram(gb: float) -> str:
    if gb >= 1.0:
        return f"{gb:.2f} GB"
    return f"{gb * 1024:.2f} MB"
