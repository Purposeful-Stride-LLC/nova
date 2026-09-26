# Qwen-Image-2.0 vs 2.1 (Cassius, 2026-09-22)

- User link: https://www.qwencloud.com/models/qwen-image-2.0 → **cloud API** `qwen-image-2.0` (DashScope), billed per image.
- Local 7B open weights: **Qwen-Image-2.1** via Comfy-Org pack for ComfyUI (DiT 7B + TE + VAE).
- TUF: downloading lean INT8 DiT + W4A8 TE + VAE into `Projects\ComfyUI\models\...`. VRAM still tight on 8GB; cold GPU required; cloud API remains the reliable path.