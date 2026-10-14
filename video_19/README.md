# Vídeo 19: z-image-turbo grátis + n8n

A Alibaba lançou o Z-Image-Turbo, um modelo de texto para imagem rapidíssimo licenciado sob Apache-2.0, e já está roubando os holofotes do Flux.2. Testamos para ver se realmente ultrapassa o Flux. Além disso, tenha duas formas de usar o Z-Image-Turbo GRATUITAMENTE: usando n8n e Modal, ou execute no Google Colab...

## [📚 Entre na nossa comunidade VIP no Whatsapp, muito conteúdo grátis para te ajudar com suas automações!](https://chat.whatsapp.com/CSVzXwWrcAoAC6xGH2EhtC?mode=gi_t)

Junte-se à nossa comunidade para ter acesso aos arquivos mostrados no vídeo, além de muito networking e troca de conhecimento com outros profissionais de tecnologia e automação!

## Arquivos disponíveis

- [servidor modal para o z-image-turbo](modal_z_image_api.py)
- [workflow n8n para testar o z-image-turbo](n8n_test_z-image-turbo.json)

## Recursos adicionais

- [Google Colab para rodar o z-image-turbo](https://github.com/camenduru/Z-Image-jupyter?tab=readme-ov-file#-jupyter-notebook)
- [Precisa de VPS? conheça a Hostinger](https://www.hostinger.com/br/cart?product=vps:vps_kvm_2&period=24&referral_type=cart_link&REFERRALCODE=OTECHLEAD&referral_id=019d7414-ea71-73fa-af89-9f71755f19ad)
- [Z-Image-Turbo](https://huggingface.co/Tongyi-MAI/Z-Image-Turbo)
- [modal](https://modal.com/)

---

## Método 1: API no Modal + n8n

Você cria um app serverless no [Modal](https://modal.com/) que gera imagens com o Z-Image-Turbo e chama ele pelo n8n.

### O que você vai precisar

| Item | Para quê |
|---|---|
| Conta no [Modal](https://modal.com/) com cartão cadastrado | GPU na nuvem (US$ 30 de crédito por mês) |
| Python 3 com suporte a ambiente virtual (`venv`) | Rodar o CLI do Modal |
| Windows: WSL2 | Os comandos abaixo rodam no terminal do WSL2 |
| n8n | Rodar o workflow de teste |

### 1. Crie a conta no Modal

1. Crie sua conta em [modal.com](https://modal.com/).
2. Cadastre o cartão de crédito para liberar os **US$ 30 por mês**. Você só é cobrado se passar desse valor.
3. Defina um limite de gastos: **Credits → Usage and Billing Settings → Usage Limit**. Quando o app atinge o limite, ele é encerrado e para de responder.

> Acompanhe o consumo na tela inicial do Modal.

### 2. Baixe o arquivo do servidor

Copie o [`modal_z_image_api.py`](modal_z_image_api.py) deste repositório para uma pasta no seu computador e abra o terminal nessa pasta.

> **Windows:** inicie o WSL2 e navegue até a pasta pelo terminal dele.

### 3. Defina o token da sua API

Abra o `modal_z_image_api.py` e troque o valor da linha abaixo por uma senha só sua:

```python
BEARER_TOKEN = "SEGUE_O_CANAL_O_TECH_LEAD"
```

Esse token protege a API: sem ele, quem descobrir a URL pode gastar os seus créditos. Você vai usar o mesmo valor no n8n.

### 4. Crie o ambiente virtual e instale o Modal

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install modal
```

### 5. Conecte o terminal à sua conta

```bash
modal setup
```

Uma aba do navegador abre pedindo autorização. Clique em **autorizar** e espere o terminal mostrar que o token foi verificado.

### 6. Faça o deploy

```bash
modal deploy modal_z_image_api.py
```

O app sobe para a nuvem do Modal e o terminal mostra a **URL do servidor**. Copie essa URL.

### 7. Configure o workflow no n8n

1. Importe o [`n8n_test_z-image-turbo.json`](n8n_test_z-image-turbo.json) no seu n8n.
2. No nó **Generate image** (HTTP Request):
   - Troque `<<URL DO SEU SERVIDOR>>` pela URL do passo 6 (mantendo o `/generate` no final).
   - No header `Authorization`, troque `<<TOKEN DO SEU SERVIDOR>>` pelo token do passo 3, no formato `Bearer SEU_TOKEN` (sem espaço antes do `Bearer`).
3. Execute o workflow: ele abre um **formulário** onde você digita o prompt. O n8n faz a requisição, converte a resposta em arquivo e mostra a imagem gerada.

> A **primeira execução demora mais**, porque o app do Modal está sendo carregado na memória. As próximas são bem mais rápidas.

### Desempenho e custo

- Cerca de **8 segundos** por imagem de 1 megapixel (GPU L40S).
- Com os US$ 30 do Modal, dá para gerar cerca de **6.650 imagens por mês**.
- Para comparação, a mesma quantidade de imagens no fal.ai custaria cerca de US$ 33.

### Referência da API

**`POST /generate`**

Header: `Authorization: Bearer SEU_TOKEN`

```bash
curl -X POST "https://SUA-URL-DO-MODAL/generate" \
  -H "Authorization: Bearer SEU_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Carro de corrida da nascar amarelo", "width": 1024, "height": 1024, "steps": 9, "guidance_scale": 1}'
```

| Campo | Obrigatório | Padrão | Descrição |
|---|---|---|---|
| `prompt` | sim | | Descrição da imagem (quanto mais detalhado, melhor) |
| `negative_prompt` | não | | O que evitar na imagem |
| `width` / `height` | não | 1024 | Tamanho em pixels (ajustado para múltiplos de 16) |
| `steps` | não | 9 | Passos de geração |
| `guidance_scale` | não | 1.0 | Escala de guidance |
| `seed` | não | aleatório | Número fixo para repetir o resultado |

Resposta: `{"image": "<PNG em base64>", "format": "png"}`

Outras rotas:

- `GET /health`: verifica se o servidor está no ar.
- `GET /`: interface web para gerar imagens pelo navegador, com login pelo mesmo token.

---

## Método 2: Google Colab (100% gratuito)

O Google Colab roda código Python nas máquinas do Google, de graça.

1. Abra o [notebook do Z-Image-Turbo](https://github.com/camenduru/Z-Image-jupyter?tab=readme-ov-file#-jupyter-notebook) e clique no link do Jupyter Notebook. Ele carrega direto no Colab.
2. Rode o **primeiro bloco** e aguarde.
3. Rode o **segundo bloco** e aguarde novamente.
4. No **terceiro bloco**, edite o prompt e execute para gerar a imagem.

> A primeira geração leva cerca de um minuto ou mais; as seguintes são mais rápidas. Diferente do método com n8n, este não dá para automatizar.

---

## Capítulos do vídeo

- 00:00 Imagens grátis via API com o Z-Image-Turbo
- 01:16 Método 1: Modal + n8n
- 01:22 Criando a conta e o limite de gastos
- 02:01 Deploy do servidor
- 03:00 Workflow no n8n
- 03:29 Desempenho e custo
- 03:46 Método 2: Google Colab

## Veja o vídeo

[![Z-Image Turbo Grátis no n8n](https://img.youtube.com/vi/DxpE8g6lm5k/maxresdefault.jpg)](https://www.youtube.com/watch?v=DxpE8g6lm5k)
