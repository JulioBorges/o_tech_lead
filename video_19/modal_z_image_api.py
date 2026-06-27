import base64
from io import BytesIO
from pathlib import Path
from typing import Optional

import modal

COMFYUI_DIR = Path("/ComfyUI")
BEARER_TOKEN = "SEGUE_O_CANAL_O_TECH_LEAD"
AUTH_COOKIE_NAME = "z_image_access_token"

image = (
    modal.Image.from_registry(
        "nvidia/cuda:12.8.1-devel-ubuntu22.04",
        add_python="3.11",
    )
    .entrypoint([])
    .apt_install("git")
    .pip_install("uv")
    .run_commands(
        "git clone --depth 1 https://github.com/comfyanonymous/ComfyUI /ComfyUI"
    )
    .run_commands(
        "uv pip install --system --compile-bytecode torch==2.7.1 torchvision==0.22.1 torchaudio==2.7.1 --extra-index-url https://download.pytorch.org/whl/cu128"
    )
    .run_commands(
        "uv pip install --system --compile-bytecode -r /ComfyUI/requirements.txt flask huggingface_hub"
    )
)

UNET_REPO_ID = "T5B/Z-Image-Turbo-FP8"
UNET_FILENAME = "z-image-turbo-fp8-e4m3fn.safetensors"
CLIP_REPO_ID = "Comfy-Org/z_image_turbo"
CLIP_FILENAME = "split_files/text_encoders/qwen_3_4b.safetensors"
VAE_FILENAME = "split_files/vae/ae.safetensors"

CACHE_DIR = Path("/cache")
cache_volume = modal.Volume.from_name("hf-hub-cache", create_if_missing=True)
volumes = {CACHE_DIR: cache_volume}

image = image.env(
    {
        "HF_HOME": str(CACHE_DIR),
    }
)

app = modal.App("z-image-turbo-fastapi")

LOGIN_HTML = """
<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Z-Image Turbo - Acesso</title>
  <style>
    :root {
      color-scheme: dark;
      --bg: #0b0f19;
      --panel: #111827;
      --border: #263244;
      --text: #e5e7eb;
      --muted: #9ca3af;
      --accent: #10a37f;
      --accent-hover: #0e8f70;
      --danger: #f87171;
    }

    * { box-sizing: border-box; }

    body {
      display: grid;
      place-items: center;
      min-height: 100vh;
      margin: 0;
      padding: 1rem;
      background: radial-gradient(circle at top, #182238 0, var(--bg) 38rem);
      color: var(--text);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }

    .card {
      width: min(100%, 28rem);
      border: 1px solid var(--border);
      border-radius: 1rem;
      background: rgba(17, 24, 39, 0.86);
      padding: 1.25rem;
    }

    .brand {
      display: flex;
      align-items: center;
      gap: 0.75rem;
      margin-bottom: 1rem;
    }

    .logo {
      display: grid;
      place-items: center;
      width: 2.25rem;
      height: 2.25rem;
      border-radius: 0.75rem;
      background: var(--accent);
      color: #042f24;
      font-weight: 800;
    }

    h1, p { margin-top: 0; }
    h1 { font-size: 1.1rem; margin-bottom: 0.15rem; }
    p { color: var(--muted); line-height: 1.5; }

    label {
      display: block;
      color: var(--muted);
      font-size: 0.82rem;
      margin-bottom: 0.4rem;
    }

    input, button {
      width: 100%;
      border: 1px solid var(--border);
      border-radius: 0.75rem;
      font: inherit;
    }

    input {
      background: #0f172a;
      color: var(--text);
      padding: 0.75rem 0.85rem;
      outline: none;
      margin-bottom: 0.9rem;
    }

    input:focus {
      border-color: var(--accent);
      box-shadow: 0 0 0 3px rgba(16, 163, 127, 0.16);
    }

    button {
      border: 0;
      background: var(--accent);
      color: white;
      cursor: pointer;
      font-weight: 700;
      padding: 0.85rem 1rem;
    }

    button:hover { background: var(--accent-hover); }
    .error { color: var(--danger); margin-top: 0.9rem; margin-bottom: 0; }
    .hidden { display: none; }
  </style>
</head>
<body>
  <form class="card" method="post" action="/">
    <div class="brand">
      <div class="logo">Z</div>
      <div>
        <h1>Z-Image Turbo</h1>
        <p>Acesso restrito</p>
      </div>
    </div>
    <label for="accessToken">Token de acesso</label>
    <input id="accessToken" name="access_token" type="password" autocomplete="current-password" autofocus required />
    <button type="submit">Acessar</button>
    <p class="error __ERROR_CLASS__">Token inválido.</p>
  </form>
</body>
</html>
"""

INDEX_HTML = """
<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Z-Image Turbo</title>
  <style>
    :root {
      color-scheme: dark;
      --bg: #0b0f19;
      --panel: #111827;
      --panel-soft: #172033;
      --border: #263244;
      --text: #e5e7eb;
      --muted: #9ca3af;
      --accent: #10a37f;
      --accent-hover: #0e8f70;
      --danger: #f87171;
    }

    * { box-sizing: border-box; }

    body {
      margin: 0;
      min-height: 100vh;
      background: radial-gradient(circle at top, #182238 0, var(--bg) 38rem);
      color: var(--text);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }

    .app {
      display: grid;
      grid-template-columns: minmax(18rem, 22rem) 1fr;
      min-height: 100vh;
    }

    aside {
      border-right: 1px solid var(--border);
      background: rgba(17, 24, 39, 0.86);
      padding: 1.25rem;
    }

    main {
      display: flex;
      flex-direction: column;
      min-width: 0;
    }

    .brand {
      display: flex;
      align-items: center;
      gap: 0.75rem;
      margin-bottom: 1.5rem;
    }

    .logo {
      display: grid;
      place-items: center;
      width: 2.25rem;
      height: 2.25rem;
      border-radius: 0.75rem;
      background: var(--accent);
      color: #042f24;
      font-weight: 800;
    }

    h1, h2, p { margin-top: 0; }

    h1 { font-size: 1.1rem; margin-bottom: 0.15rem; }
    h2 { font-size: 1rem; margin-bottom: 0.8rem; }
    p { color: var(--muted); line-height: 1.5; }

    .card {
      border: 1px solid var(--border);
      border-radius: 1rem;
      background: rgba(23, 32, 51, 0.7);
      padding: 1rem;
      margin-bottom: 1rem;
    }

    label {
      display: block;
      color: var(--muted);
      font-size: 0.82rem;
      margin-bottom: 0.4rem;
    }

    input, textarea, select, button {
      width: 100%;
      border: 1px solid var(--border);
      border-radius: 0.75rem;
      font: inherit;
    }

    input, textarea, select {
      background: #0f172a;
      color: var(--text);
      padding: 0.75rem 0.85rem;
      outline: none;
    }

    textarea {
      min-height: 8rem;
      resize: vertical;
    }

    input:focus, textarea:focus, select:focus {
      border-color: var(--accent);
      box-shadow: 0 0 0 3px rgba(16, 163, 127, 0.16);
    }

    button {
      border: 0;
      background: var(--accent);
      color: white;
      cursor: pointer;
      font-weight: 700;
      padding: 0.85rem 1rem;
    }

    button:hover:not(:disabled) { background: var(--accent-hover); }
    button:disabled { cursor: not-allowed; opacity: 0.65; }

    .secondary {
      background: transparent;
      border: 1px solid var(--border);
      color: var(--text);
    }

    .secondary:hover:not(:disabled) { background: var(--panel-soft); }

    .row {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 0.75rem;
    }

    .field { margin-bottom: 0.9rem; }

    .token-step {
      max-width: 34rem;
      margin: auto;
      padding: 1.5rem;
    }

    .chat {
      flex: 1;
      overflow-y: auto;
      padding: 2rem clamp(1rem, 4vw, 4rem);
    }

    .message {
      max-width: 64rem;
      margin: 0 auto 1rem;
      border: 1px solid var(--border);
      border-radius: 1rem;
      background: rgba(17, 24, 39, 0.7);
      padding: 1rem;
    }

    .message.user { background: rgba(16, 163, 127, 0.12); }
    .message .role { color: var(--muted); font-size: 0.8rem; margin-bottom: 0.45rem; }
    .message img { display: block; max-width: 100%; border-radius: 0.85rem; margin-top: 0.75rem; }

    .composer {
      border-top: 1px solid var(--border);
      background: rgba(11, 15, 25, 0.92);
      padding: 1rem clamp(1rem, 4vw, 4rem);
    }

    .composer-inner {
      max-width: 64rem;
      margin: 0 auto;
    }

    .error { color: var(--danger); }
    .hidden { display: none; }
    .hint { font-size: 0.8rem; color: var(--muted); }

    @media (max-width: 820px) {
      .app { grid-template-columns: 1fr; }
      aside { border-right: 0; border-bottom: 1px solid var(--border); }
      .row { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <section id="appShell" class="app">
    <aside>
      <div class="brand">
        <div class="logo">Z</div>
        <div>
          <h1>Z-Image Turbo</h1>
          <p class="hint">Open WebUI-style</p>
        </div>
      </div>
      <div class="card">
        <h2>Configurações</h2>
        <div class="row">
          <div class="field">
            <label for="width">Largura</label>
            <input id="width" type="number" min="256" step="16" value="1024" />
          </div>
          <div class="field">
            <label for="height">Altura</label>
            <input id="height" type="number" min="256" step="16" value="1024" />
          </div>
        </div>
        <div class="row">
          <div class="field">
            <label for="steps">Steps</label>
            <input id="steps" type="number" min="1" max="50" value="9" />
          </div>
          <div class="field">
            <label for="guidanceScale">Guidance</label>
            <input id="guidanceScale" type="number" min="0" max="20" step="0.1" value="1.0" />
          </div>
        </div>
        <div class="field">
          <label for="seed">Seed opcional</label>
          <input id="seed" type="number" min="0" placeholder="Aleatória" />
        </div>
      </div>
    </aside>

    <main>
      <div id="chat" class="chat">
        <div class="message">
          <div class="role">Assistente</div>
          <p>Descreva a imagem que você quer gerar. Você também pode informar um prompt negativo no campo abaixo.</p>
        </div>
      </div>

      <form id="generateForm" class="composer">
        <div class="composer-inner">
          <div class="field">
            <label for="prompt">Prompt</label>
            <textarea id="prompt" placeholder="Ex.: cinematic portrait of a futuristic astronaut in a neon rainforest..." required></textarea>
          </div>
          <div class="field">
            <label for="negativePrompt">Negative prompt</label>
            <input id="negativePrompt" type="text" placeholder="Ex.: blurry, low quality, distorted hands" />
          </div>
          <button id="generateButton" type="submit">Gerar imagem</button>
          <p id="status" class="hint"></p>
        </div>
      </form>
    </main>
  </section>

  <script>
    const generateForm = document.getElementById('generateForm');
    const generateButton = document.getElementById('generateButton');
    const chat = document.getElementById('chat');
    const statusText = document.getElementById('status');

    function addMessage(role, html, className = '') {
      const message = document.createElement('div');
      message.className = `message ${className}`.trim();
      message.innerHTML = `<div class="role">${role}</div>${html}`;
      chat.appendChild(message);
      chat.scrollTop = chat.scrollHeight;
      return message;
    }

    function escapeHtml(value) {
      return value.replace(/[&<>"]/g, (char) => ({
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;'
      }[char]));
    }

    generateForm.addEventListener('submit', async (event) => {
      event.preventDefault();

      const prompt = document.getElementById('prompt').value.trim();
      if (!prompt) return;

      const payload = {
        prompt,
        negative_prompt: document.getElementById('negativePrompt').value.trim() || undefined,
        width: Number(document.getElementById('width').value) || 1024,
        height: Number(document.getElementById('height').value) || 1024,
        steps: Number(document.getElementById('steps').value) || 9,
        guidance_scale: Number(document.getElementById('guidanceScale').value) || 1.0,
      };

      const seed = document.getElementById('seed').value;
      if (seed !== '') payload.seed = Number(seed);

      addMessage('Você', `<p>${escapeHtml(prompt)}</p>`, 'user');
      const pending = addMessage('Assistente', '<p>Gerando imagem...</p>');
      generateButton.disabled = true;
      statusText.textContent = 'A geração pode levar alguns segundos.';
      statusText.className = 'hint';

      try {
        const response = await fetch('/generate', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(payload),
        });

        const result = await response.json();
        if (!response.ok) {
          throw new Error(result.error || 'Falha ao gerar imagem');
        }

        pending.innerHTML = `
          <div class="role">Assistente</div>
          <p>Imagem gerada com sucesso.</p>
          <img src="data:image/${result.format || 'png'};base64,${result.image}" alt="Imagem gerada" />
        `;
        statusText.textContent = 'Pronto.';
      } catch (error) {
        pending.innerHTML = `<div class="role">Assistente</div><p class="error">${escapeHtml(error.message)}</p>`;
        statusText.textContent = 'Erro ao gerar imagem.';
        statusText.className = 'hint error';
      } finally {
        generateButton.disabled = false;
      }
    });
  </script>
</body>
</html>
"""

with image.imports():
    from flask import Flask, request, jsonify, make_response, redirect


@app.cls(
    image=image,
    gpu="L40s",
    volumes=volumes,
    scaledown_window=120,
    timeout=10 * 60,
)
class ZImageTurboModel:
    @modal.enter()
    def enter(self):
        import sys

        import torch
        from huggingface_hub import hf_hub_download

        sys.path.insert(0, str(COMFYUI_DIR))
        from nodes import NODE_CLASS_MAPPINGS

        print("Downloading Z-Image Turbo FP8 model files...")

        # Enable TensorFloat32 for better performance on modern GPUs
        torch.set_float32_matmul_precision("high")

        model_files = [
            (UNET_REPO_ID, UNET_FILENAME, "diffusion_models"),
            (CLIP_REPO_ID, CLIP_FILENAME, "clip"),
            (CLIP_REPO_ID, VAE_FILENAME, "vae"),
        ]

        for repo_id, filename, model_dir in model_files:
            source = hf_hub_download(
                repo_id=repo_id,
                filename=filename,
                cache_dir=CACHE_DIR,
            )
            target = COMFYUI_DIR / "models" / model_dir / Path(filename).name
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists() or target.is_symlink():
                target.unlink()
            target.symlink_to(source)

        unet_loader = NODE_CLASS_MAPPINGS["UNETLoader"]()
        clip_loader = NODE_CLASS_MAPPINGS["CLIPLoader"]()
        vae_loader = NODE_CLASS_MAPPINGS["VAELoader"]()
        self.clip_text_encode = NODE_CLASS_MAPPINGS["CLIPTextEncode"]()
        self.ksampler = NODE_CLASS_MAPPINGS["KSampler"]()
        self.vae_decode = NODE_CLASS_MAPPINGS["VAEDecode"]()
        self.empty_latent_image = NODE_CLASS_MAPPINGS["EmptyLatentImage"]()

        with torch.inference_mode():
            self.unet = unet_loader.load_unet(
                UNET_FILENAME, "fp8_e4m3fn_fast"
            )[0]
            self.clip = clip_loader.load_clip(
                Path(CLIP_FILENAME).name, type="lumina2"
            )[0]
            self.vae = vae_loader.load_vae(Path(VAE_FILENAME).name)[0]

        print("Model loaded successfully!")

    @modal.method()
    def inference(
        self,
        prompt: str,
        negative_prompt: Optional[str] = None,
        width: int = 1024,
        height: int = 1024,
        num_inference_steps: int = 9,
        guidance_scale: float = 1.0,
        seed: Optional[int] = None,
    ) -> bytes:
        import random
        import time

        import torch
        from PIL import Image

        def adjust_dimensions_preserve_aspect(w, h, divisor=16, min_size=256):
            """Adjust dimensions to be divisible by divisor while preserving aspect ratio."""
            aspect_ratio = w / h

            # Start from width, go up and down to find first valid pair
            for offset in range(0, max(w, 1000), divisor):
                for test_w in [w + offset, w - offset]:
                    if test_w < min_size:
                        continue
                    if test_w % divisor != 0:
                        continue

                    # Calculate height from aspect ratio
                    test_h = round(test_w / aspect_ratio)
                    if test_h < min_size:
                        continue
                    if test_h % divisor == 0:
                        return int(test_w), int(test_h)

            # Fallback: just round both
            return (w // divisor) * divisor, (h // divisor) * divisor

        # Adjust dimensions while preserving aspect ratio
        width, height = adjust_dimensions_preserve_aspect(width, height)

        # Use provided seed or generate random one
        if seed is None:
            random.seed(int(time.time()))
            seed = random.randint(0, 18446744073709551615)

        print(f"Generating image with prompt: {prompt}")
        print(f"Dimensions: {width}x{height}")

        with torch.inference_mode():
            positive = self.clip_text_encode.encode(self.clip, prompt)[0]
            negative = self.clip_text_encode.encode(
                self.clip, negative_prompt or ""
            )[0]
            latent_image = self.empty_latent_image.generate(
                width, height, batch_size=1
            )[0]
            samples = self.ksampler.sample(
                self.unet,
                seed,
                num_inference_steps,
                guidance_scale,
                "euler",
                "simple",
                positive,
                negative,
                latent_image,
                denoise=1.0,
            )[0]
            decoded = self.vae_decode.decode(self.vae, samples)[0].detach().cpu()

        image_array = decoded.clamp(0, 1).mul(255).to(torch.uint8).numpy()[0]
        image = Image.fromarray(image_array)

        byte_stream = BytesIO()
        image.save(byte_stream, format="PNG")
        image_bytes = byte_stream.getvalue()

        return image_bytes


@app.function(image=image, volumes=volumes, cpu="0.5", memory="2GiB")
@modal.wsgi_app()
def flask_app():
    web_app = Flask(__name__)

    def render_login(error=False):
        error_class = "" if error else "hidden"
        return LOGIN_HTML.replace("__ERROR_CLASS__", error_class)

    def has_valid_access_cookie():
        return request.cookies.get(AUTH_COOKIE_NAME) == BEARER_TOKEN

    @web_app.route("/", methods=["GET", "POST"])
    def index():
        if request.method == "POST":
            if request.form.get("access_token") == BEARER_TOKEN:
                response = make_response(redirect("/"))
                response.set_cookie(
                    AUTH_COOKIE_NAME,
                    BEARER_TOKEN,
                    httponly=True,
                    secure=request.is_secure,
                    samesite="Lax",
                )
                return response

            return render_login(error=True), 401

        if not has_valid_access_cookie():
            return render_login()

        return INDEX_HTML

    @web_app.route("/health")
    def health_check():
        return jsonify({"status": "alive"})

    @web_app.route("/generate", methods=["POST"])
    def generate_image():
        """
        Generate an image using Z-Image Turbo FP8 model.

        - **prompt**: Text description of the image you want to generate
        - **negative_prompt**: Text description of what to avoid in the image
        - **width**: Desired image width in pixels (default: 1024)
        - **height**: Desired image height in pixels (default: 1024)
        - **steps**: Number of inference steps (default: 9)
        - **guidance_scale**: Guidance scale (default: 1.0)
        - **seed**: Seed for reproducible results (default: random)
        """
        auth_scheme, _, credentials = request.headers.get("Authorization", "").partition(
            " "
        )

        has_valid_bearer_token = (
            auth_scheme.lower() == "bearer" and credentials == BEARER_TOKEN
        )

        if not has_valid_bearer_token and not has_valid_access_cookie():
            return (
                jsonify({"error": "Incorrect bearer token"}),
                401,
                {"WWW-Authenticate": "Bearer"},
            )

        data = request.get_json(force=True)
        prompt = data.get("prompt")
        negative_prompt = data.get("negative_prompt")
        width = data.get("width", 1024)
        height = data.get("height", 1024)
        steps = data.get("steps", 9)
        guidance_scale = data.get("guidance_scale", 1.0)
        seed = data.get("seed")  # None if not provided, will use random

        if not prompt:
            return jsonify({"error": "'prompt' parameter is required"}), 400

        def adjust_dimensions_preserve_aspect(w, h, divisor=16, min_size=256):
            """Adjust dimensions to be divisible by divisor while preserving aspect ratio."""
            aspect_ratio = w / h

            # Start from width, go up and down to find first valid pair
            for offset in range(0, max(w, 1000), divisor):
                for test_w in [w + offset, w - offset]:
                    if test_w < min_size:
                        continue
                    if test_w % divisor != 0:
                        continue

                    # Calculate height from aspect ratio
                    test_h = round(test_w / aspect_ratio)
                    if test_h < min_size:
                        continue
                    if test_h % divisor == 0:
                        return int(test_w), int(test_h)

            # Fallback: just round both
            return (w // divisor) * divisor, (h // divisor) * divisor

        try:
            # Adjust dimensions while preserving aspect ratio
            adjusted_width, adjusted_height = adjust_dimensions_preserve_aspect(
                width, height
            )

            model = ZImageTurboModel()
            result_bytes = model.inference.remote(
                prompt=prompt,
                negative_prompt=negative_prompt,
                width=adjusted_width,
                height=adjusted_height,
                num_inference_steps=steps,
                guidance_scale=guidance_scale,
                seed=seed,
            )

            # Encode as base64
            img_base64 = base64.b64encode(result_bytes).decode("utf-8")

            return jsonify(
                {
                    "image": img_base64,
                    "format": "png",
                }
            )

        except Exception as e:
            print(f"Error: {e}")
            return jsonify({"error": str(e)}), 500

    return web_app
