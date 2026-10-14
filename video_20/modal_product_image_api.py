"""
API de edição de imagens de produto ("premium") no Modal.com

Modelo: Qwen-Image-Edit-2511 + LoRA Lightning (4 passos)
Recorte opcional do produto: BiRefNet (MIT) para recolar o produto original
por cima do resultado e preservar logo/texto pixel a pixel.

Secret no Modal (uma vez):
    modal secret create product-image-api \
        BEARER_TOKEN=<sua-chave-da-api> \
        HF_TOKEN=<seu-token-hugging-face>

Pré-baixar os pesos no Volume (opcional, evita o 1º cold start lento):
    modal run modal_product_image_api.py::download_models

Deploy:
    modal deploy modal_product_image_api.py

Chamada:
    POST https://<workspace>--product-image-api-editor-web.modal.run/generate
    Header: x-api-key: <BEARER_TOKEN>
    Body JSON: {"image": "<base64>", "prompt": "..."}
"""

import os

import modal

APP_NAME = "product-image-api"
EDIT_MODEL = "Qwen/Qwen-Image-Edit-2511"
LIGHTNING_REPO = "lightx2v/Qwen-Image-Edit-2511-Lightning"
LIGHTNING_WEIGHTS = "Qwen-Image-Edit-2511-Lightning-4steps-V1.0-bf16.safetensors"
SEG_MODEL = "ZhengPeng7/BiRefNet"

CACHE_DIR = "/cache/hf"
MAX_IMAGE_BYTES = 15 * 1024 * 1024  # 15 MB após decodificar o base64

app = modal.App(APP_NAME)

hf_cache = modal.Volume.from_name("product-image-hf-cache", create_if_missing=True)
secrets = [modal.Secret.from_name("product-image-api")]  # BEARER_TOKEN + HF_TOKEN

image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("git")
    .pip_install(
        "torch==2.6.0",
        "torchvision==0.21.0",
        "git+https://github.com/huggingface/diffusers",
        "transformers>=4.51",
        "accelerate",
        "peft",
        "safetensors",
        "huggingface_hub[hf_xet]",
        "timm",
        "kornia",
        "einops",
        "pillow",
        "fastapi[standard]",
    )
    .env(
        {
            "HF_HOME": CACHE_DIR,
            # Download paralelo e agressivo via Xet (backend atual do HF Hub)
            "HF_XET_HIGH_PERFORMANCE": "1",
            # Fallback para versões antigas do huggingface_hub
            "HF_HUB_ENABLE_HF_TRANSFER": "0",
        }
    )
)


def _snapshot_all():
    """Baixa todos os pesos para o Volume usando o HF_TOKEN."""
    from huggingface_hub import hf_hub_download, snapshot_download

    token = os.environ["HF_TOKEN"]
    snapshot_download(EDIT_MODEL, token=token, max_workers=16)
    hf_hub_download(LIGHTNING_REPO, LIGHTNING_WEIGHTS, token=token)
    snapshot_download(SEG_MODEL, token=token, max_workers=8)


@app.function(image=image, secrets=secrets, volumes={"/cache": hf_cache}, timeout=3600)
def download_models():
    _snapshot_all()
    hf_cache.commit()
    print("Pesos baixados para o Volume.")


@app.cls(
    image=image,
    gpu="H100",
    secrets=secrets,
    volumes={"/cache": hf_cache},
    timeout=600,
    max_containers=1,  # uma GPU: chamadas extras esperam na fila em vez de subir outro H100
    scaledown_window=30,  # fica quente 30s após a última chamada; o laço sequencial do n8n reutiliza
    # min_containers=1,    # descomente para zerar cold start (H100 24/7, consome o crédito em horas)
)
class Editor:
    @modal.enter()
    def load(self):
        import math
        import threading

        import torch
        from diffusers import FlowMatchEulerDiscreteScheduler, QwenImageEditPlusPipeline
        from transformers import AutoModelForImageSegmentation

        _snapshot_all()  # no-op se já estiver no Volume
        hf_cache.commit()

        token = os.environ["HF_TOKEN"]

        # Scheduler recomendado pelo Qwen-Image-Lightning
        scheduler = FlowMatchEulerDiscreteScheduler.from_config(
            {
                "base_image_seq_len": 256,
                "base_shift": math.log(3),
                "invert_sigmas": False,
                "max_image_seq_len": 8192,
                "max_shift": math.log(3),
                "num_train_timesteps": 1000,
                "shift": 1.0,
                "shift_terminal": None,
                "stochastic_sampling": False,
                "time_shift_type": "exponential",
                "use_beta_sigmas": False,
                "use_dynamic_shifting": True,
                "use_exponential_sigmas": False,
                "use_karras_sigmas": False,
            }
        )

        self.pipe = QwenImageEditPlusPipeline.from_pretrained(
            EDIT_MODEL, scheduler=scheduler, torch_dtype=torch.bfloat16, token=token
        ).to("cuda")
        self.pipe.load_lora_weights(LIGHTNING_REPO, weight_name=LIGHTNING_WEIGHTS, token=token)
        self.pipe.fuse_lora()
        self.pipe.set_progress_bar_config(disable=True)

        self.seg = (
            AutoModelForImageSegmentation.from_pretrained(SEG_MODEL, trust_remote_code=True, token=token)
            .to("cuda")
            .eval()
            .half()
        )

        self.lock = threading.Lock()
        self.api_key = os.environ["BEARER_TOKEN"]

    # ---------- helpers ----------

    def _product_mask(self, img):
        """Máscara (L) do produto via BiRefNet, no tamanho da imagem."""
        import torch
        from PIL import Image, ImageFilter
        from torchvision import transforms

        tf = transforms.Compose(
            [
                transforms.Resize((1024, 1024)),
                transforms.ToTensor(),
                transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
            ]
        )
        x = tf(img).unsqueeze(0).to("cuda").half()
        with torch.no_grad():
            pred = self.seg(x)[-1].sigmoid().cpu()[0].squeeze()
        mask = transforms.ToPILImage()(pred).resize(img.size, Image.LANCZOS)
        # Erosão leve + blur para uma borda natural
        return mask.filter(ImageFilter.MinFilter(3)).filter(ImageFilter.GaussianBlur(1.5))

    @staticmethod
    def _decode_image(b64: str):
        import base64
        import binascii
        import io

        from fastapi import HTTPException
        from PIL import Image, ImageOps

        if "," in b64 and b64.strip().startswith("data:"):
            b64 = b64.split(",", 1)[1]  # aceita data URI
        try:
            raw = base64.b64decode(b64, validate=False)
        except (binascii.Error, ValueError):
            raise HTTPException(400, "image: base64 inválido")
        if len(raw) > MAX_IMAGE_BYTES:
            raise HTTPException(413, "image: arquivo maior que 15 MB")
        try:
            img = Image.open(io.BytesIO(raw))
            img = ImageOps.exif_transpose(img)
        except Exception:
            raise HTTPException(400, "image: formato não reconhecido")

        # Fundo branco em imagens com transparência
        if img.mode in ("RGBA", "LA", "P"):
            img = img.convert("RGBA")
            bg = Image.new("RGBA", img.size, (255, 255, 255, 255))
            img = Image.alpha_composite(bg, img)
        return img.convert("RGB")

    @staticmethod
    def _upscale_small(img, target_side: int = 1024):
        """Imagens pequenas de marketplace (~450px) rendem melhor ampliadas antes."""
        from PIL import Image

        w, h = img.size
        if max(w, h) >= target_side:
            return img
        s = target_side / max(w, h)
        return img.resize((round(w * s), round(h * s)), Image.LANCZOS)

    # ---------- API ----------

    @modal.asgi_app()
    def web(self):
        import base64
        import io
        import secrets as pysecrets
        import time
        from typing import Literal, Optional

        import torch
        from fastapi import Depends, FastAPI, Header, HTTPException
        from pydantic import BaseModel, Field

        api = FastAPI(title="Product Image API", version="1.0.0")

        def require_key(x_api_key: Optional[str] = Header(default=None)):
            if not x_api_key or not pysecrets.compare_digest(x_api_key, self.api_key):
                raise HTTPException(401, "x-api-key inválida ou ausente")

        class GenerateRequest(BaseModel):
            image: str = Field(..., description="Imagem de origem em base64 (aceita data URI)")
            prompt: str = Field(..., min_length=3, max_length=2000)
            negative_prompt: str = " "
            seed: Optional[int] = None
            steps: int = Field(4, ge=2, le=8)
            preserve_product: bool = Field(
                False,
                description="Recola o produto original (recorte BiRefNet) sobre o resultado. "
                "Use com prompts que mantenham posição/tamanho do produto.",
            )
            output_format: Literal["png", "jpeg", "webp"] = "png"

        @api.get("/health")
        def health():
            return {"status": "ok", "model": EDIT_MODEL}

        @api.post("/generate", dependencies=[Depends(require_key)])
        def generate(req: GenerateRequest):
            t0 = time.time()
            src = self._upscale_small(self._decode_image(req.image))

            prompt = req.prompt
            if req.preserve_product:
                prompt += (
                    " Keep the product exactly identical, in the same position, size and angle. "
                    "Only change the background, lighting and surface."
                )

            seed = req.seed if req.seed is not None else int.from_bytes(os.urandom(4), "little")
            gen = torch.Generator(device="cuda").manual_seed(seed)

            with self.lock, torch.inference_mode():
                out = self.pipe(
                    image=[src],
                    prompt=prompt,
                    negative_prompt=req.negative_prompt,
                    true_cfg_scale=1.0,  # Lightning dispensa CFG
                    num_inference_steps=req.steps,
                    generator=gen,
                ).images[0]

                if req.preserve_product:
                    out = out.resize(src.size)
                    mask = self._product_mask(src)
                    out.paste(src, (0, 0), mask)

            buf = io.BytesIO()
            fmt = req.output_format.upper()
            save_kwargs = {"quality": 95} if fmt in ("JPEG", "WEBP") else {}
            out.save(buf, "JPEG" if fmt == "JPEG" else fmt, **save_kwargs)

            return {
                "image": base64.b64encode(buf.getvalue()).decode(),
                "mime_type": f"image/{req.output_format}",
                "width": out.width,
                "height": out.height,
                "seed": seed,
                "elapsed_ms": int((time.time() - t0) * 1000),
            }

        return api