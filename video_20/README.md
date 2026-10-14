# Vídeo 20: Imagens premium de produtos com IA open source (Qwen-Image-Edit + Modal + n8n)

Imagem de produto de marketplace raramente vende bem. Neste vídeo eu mostro como transformar a foto crua de um produto em uma **imagem promocional premium** usando IA, primeiro na mão (Gemini / ChatGPT) e depois de forma **automatizada e praticamente gratuita**, com o modelo open source **Qwen-Image-Edit-2511 Lightning** rodando como API no **Modal** e sendo chamado por um workflow do **n8n**.

## [📚 Entre na nossa comunidade VIP no Whatsapp, muito conteúdo grátis para te ajudar com suas automações!](https://chat.whatsapp.com/CSVzXwWrcAoAC6xGH2EhtC?mode=gi_t)

Junte-se à nossa comunidade para ter acesso aos arquivos mostrados no vídeo, além de muito networking e troca de conhecimento com outros profissionais de tecnologia e automação!

## Arquivos disponíveis

- [servidor Modal da API de imagens de produto](modal_product_image_api.py)
- [workflow n8n para gerar a imagem promocional](GERAR%20IMAGEM%20PROMOCIONAL.json)

## Recursos adicionais

- [Modal](https://modal.com/)
- [Qwen-Image-Edit-2511](https://huggingface.co/Qwen/Qwen-Image-Edit-2511)
- [Qwen-Image-Edit-2511 Lightning (4 passos)](https://huggingface.co/lightx2v/Qwen-Image-Edit-2511-Lightning)
- [Python](https://www.python.org/downloads/)
- [Tokens de acesso do Hugging Face](https://huggingface.co/settings/tokens)
- [Precisa de VPS? conheça a Hostinger](https://www.hostinger.com/br/cart?product=vps:vps_kvm_2&period=24&referral_type=cart_link&REFERRALCODE=OTECHLEAD&referral_id=019d7414-ea71-73fa-af89-9f71755f19ad)

---

## Passo a passo

### O que você vai precisar

| Item | Para quê |
|---|---|
| Python 3.10 ou superior | Rodar o CLI do Modal |
| Conta no [Modal](https://modal.com/) com cartão cadastrado | GPU na nuvem (o plano Starter dá US$ 30 de crédito por mês) |
| Conta no [Hugging Face](https://huggingface.co/) | Baixar o modelo mais rápido com o `HF_TOKEN` |
| n8n (cloud ou self-hosted) | Automatizar a geração das imagens |
| Credencial de um modelo de texto no n8n | Gerar o prompt da imagem (OpenAI ou outro compatível) |

### 1. Instale o Python

Baixe em [python.org/downloads](https://www.python.org/downloads/) o instalador do seu sistema (Windows, Mac ou Linux).

> No Windows, marque a opção **"Add Python to PATH"** durante a instalação.

### 2. Abra o terminal na pasta do projeto

- **Windows:** tecla Windows → digite `cmd` → Enter
- **Mac / Linux:** abra o app **Terminal**

Entre na pasta onde você salvou o `modal_product_image_api.py`:

```bash
cd caminho/da/sua/pasta
```

### 3. Crie o ambiente virtual e instale o Modal

```bash
python -m venv .venv
```

Ative o ambiente:

```bash
# Mac / Linux
source .venv/bin/activate

# Windows (CMD)
.venv\Scripts\activate
```

Instale o CLI do Modal:

```bash
pip install modal
```

### 4. Crie a conta no Modal e proteja seu bolso

1. Acesse [modal.com](https://modal.com/) → **Sign Up** (pode logar com o Google).
2. Escolha **Personal** e clique em **Add Payment Method** para cadastrar o cartão. O Modal faz uma cobrança de verificação de alguns centavos de dólar e estorna em seguida.
3. Depois do cadastro, aparecem os **US$ 30 de crédito por mês**, que se renovam todo mês.
4. **Importante:** vá em **Settings → Usage & Billing → Usage Limit** e coloque **US$ 30**. Assim você nunca gasta além do crédito gratuito.

> Mesmo com o limite, acompanhe o consumo no dashboard do Modal nos primeiros dias.

### 5. Conecte o terminal à sua conta Modal

```bash
python -m modal setup
```

Abra no navegador a URL que aparecer no terminal e autorize. Pronto, o terminal fica logado na sua conta.

### 6. Gere as duas chaves

**a) Chave da sua API (`BEARER_TOKEN`)**

É a "senha" da sua API. Sem ela, qualquer pessoa que descobrir a URL poderia gastar seus créditos. Gere uma chave aleatória com o próprio Python:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Guarde essa chave, você vai usá-la no n8n.

**b) Token do Hugging Face (`HF_TOKEN`)**

Em [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens) → **Create new token**. Um token do tipo **Read** é suficiente. Com o token, o download do modelo fica bem mais rápido.

### 7. Crie o secret no Modal

```bash
modal secret create product-image-api BEARER_TOKEN="SUA_CHAVE_DA_API" HF_TOKEN="SEU_TOKEN_HF"
```

> Use **aspas** nos valores. Algumas chaves geradas têm símbolos como `=` que confundem o terminal.
> O nome do secret precisa ser exatamente `product-image-api`, que é o nome que o script procura.

### 8. Baixe o modelo para o Modal (uma vez só)

```bash
modal run modal_product_image_api.py::download_models
```

Leva alguns minutos (no vídeo foram cerca de 5). Os pesos (~55 GB) ficam salvos no Volume `product-image-hf-cache`, em **Storage** no painel do Modal, e não precisam ser baixados de novo.

### 9. Faça o deploy da API

```bash
modal deploy modal_product_image_api.py
```

No final o terminal mostra a URL da sua API, parecida com:

```
https://SEU-USUARIO--product-image-api-editor-web.modal.run
```

A URL começa com o nome da sua conta Modal. Guarde ela para o n8n.

### 10. Teste a API

**Rota:** `POST /generate`
**Header:** `x-api-key: SUA_CHAVE_DA_API`

```bash
curl -X POST "https://SEU-USUARIO--product-image-api-editor-web.modal.run/generate" \
  -H "x-api-key: SUA_CHAVE_DA_API" \
  -H "Content-Type: application/json" \
  -d '{
    "image": "<IMAGEM_EM_BASE64>",
    "prompt": "Professional studio product photography, dark matte stone pedestal, soft rim lighting, deep blue gradient background, premium advertising"
  }'
```

**Campos do corpo (JSON):**

| Campo | Obrigatório | Descrição |
|---|---|---|
| `image` | sim | Imagem de origem em base64 (aceita também `data:image/png;base64,...`), até 15 MB |
| `prompt` | sim | Descrição da imagem promocional desejada, de 3 a 2000 caracteres (de preferência em inglês) |
| `negative_prompt` | não | O que evitar na imagem |
| `seed` | não | Número fixo para repetir o mesmo resultado |
| `steps` | não | Passos de geração, de 2 a 8 (padrão: 4) |
| `preserve_product` | não | `true` recola o produto original por cima do resultado para preservar logo e textos (padrão: `false`) |
| `output_format` | não | `png`, `jpeg` ou `webp` (padrão: `png`) |

**Resposta:**

```json
{
  "image": "<IMAGEM_GERADA_EM_BASE64>",
  "mime_type": "image/png",
  "width": 1024,
  "height": 1024,
  "seed": 123456,
  "elapsed_ms": 4300
}
```

Para conferir se a API está no ar, sem precisar de chave: `GET /health`.

### 11. Configure o workflow do n8n

1. Importe o arquivo [`GERAR IMAGEM PROMOCIONAL.json`](GERAR%20IMAGEM%20PROMOCIONAL.json) no seu n8n.
2. No nó **CONFIG**, troque `<SUA API KEY>` pela chave `BEARER_TOKEN` do passo 6.
3. No nó **REQUISICAO MODAL**, troque a URL `https://<URL MODAL>generate` pela URL do passo 9 terminando em `/generate`, por exemplo:
   `https://SEU-USUARIO--product-image-api-editor-web.modal.run/generate`
   (cuidado com espaço sobrando no fim da URL).
4. No nó de geração de prompt que estiver ativo, selecione a **sua credencial**.

**Entradas do workflow** (ele é um sub-workflow, acionado pelo nó **WORKFLOW TRIGGER**):

| Campo | Exemplo |
|---|---|
| `urlImagem` | URL da imagem do produto no marketplace |
| `descricaoProduto` | `iPhone 18 Pro Max 512GB Glacial` |

O workflow já vem com esse exemplo fixado no trigger para você testar direto no editor.

**O que o workflow faz:**

1. **CONFIG** guarda a sua chave da API.
2. **Gera o prompt** da imagem com um modelo de IA. Existem dois caminhos:
   - **GERAR PROMPT SOMENTE TEXTO** (ativo por padrão): usa só a descrição do produto, com um modelo de texto (no vídeo, o Atria Dawn Preview do vídeo anterior, configurado como credencial compatível com OpenAI).
   - **GERAR PROMPT COM IMAGEM DE REFERENCIA** (desativado): usa a OpenAI com análise da imagem do produto, o que costuma gerar prompts mais fiéis.
3. **GET PROMPT 1 / GET PROMPT 2** extraem o texto do prompt da resposta de cada caminho, e **UNIFICA RESULTADOS** + **Limit** juntam tudo em um único item.
4. **CARREGA IMAGEM** baixa a imagem do produto e **CONVERTE PARA BASE64** transforma em texto.
5. **REQUISICAO MODAL** chama o `/generate` com a imagem e o prompt. A imagem gerada volta em base64 no campo `image`.

**Trocando para o caminho com imagem de referência:**

1. Ative **GERAR PROMPT COM IMAGEM DE REFERENCIA** e **GET PROMPT 2**.
2. Desative **GERAR PROMPT SOMENTE TEXTO** e **GET PROMPT 1**.
3. Confira se a expressão do GET PROMPT ativo está lendo o texto da resposta do nó anterior. Os dois nós devolvem o resultado em formatos diferentes, então vale executar uma vez e conferir o campo.

**Transformando a resposta em arquivo:** para usar a imagem gerada como binário (enviar no WhatsApp, salvar no Drive etc.), adicione depois do REQUISICAO MODAL um nó **Convert to File** com a operação **Move Base64 String to File** apontando para o campo `image`.

**Dica de timeout:** a primeira requisição pode demorar por causa do cold start. No nó **REQUISICAO MODAL**, vá em **Options → Timeout** e aumente o valor. O campo é em milissegundos: `360000` = 6 minutos.

### 12. Gere em lote para economizar

O Modal cobra por segundo de GPU e o container "dorme" quando fica parado:

- **Cold start** (primeira chamada): cerca de 50 s, por volta de US$ 0,50.
- **Container quente:** cerca de 4 s por imagem.

O script já vem configurado para isso: usa **uma GPU por vez** (`max_containers=1`, chamadas extras esperam na fila) e mantém o container ligado por **30 s** depois da última chamada (`scaledown_window=30`).

Por isso, use o workflow como **sub-workflow** e chame-o em **loop**, um produto atrás do outro. A máquina liga uma vez e gera todas as imagens em sequência. Pelas contas do vídeo, os US$ 30 mensais rendem em torno de **3.600 imagens por mês** gerando em lote.

> No script existe a linha `min_containers=1` comentada. Ela elimina o cold start, mas deixa uma H100 ligada 24 horas por dia e consome o crédito mensal em poucas horas. Só ative se souber o que está fazendo.

---

## Problemas comuns

| Sintoma | Causa provável | Solução |
|---|---|---|
| `401 x-api-key inválida ou ausente` | Header errado ou chave diferente da do secret | Confira o nó CONFIG e o valor do `BEARER_TOKEN` |
| Erro `Secret not found` no deploy | Nome do secret diferente | Recrie o secret com o nome exato `product-image-api` |
| Timeout na primeira chamada | Cold start do container | Aumente o timeout do REQUISICAO MODAL e tente de novo |
| `404` na chamada | URL sem `/generate` ou com espaço no fim | Corrija a URL no nó REQUISICAO MODAL |
| `modal: command not found` | Ambiente virtual não ativado | Rode novamente o `source .venv/bin/activate` (ou `.venv\Scripts\activate`) |
| Erro no `modal secret create` | Caracteres especiais na chave | Coloque os valores entre aspas |
| API parou de responder no fim do mês | Atingiu o limite de US$ 30 | Aguarde a renovação dos créditos ou ajuste o limite |

## Capítulos do vídeo

- 00:00 Imagem crua x imagem promocional
- 00:50 Por que melhorar as imagens dos seus produtos
- 01:24 Forma manual com Gemini e ChatGPT
- 05:04 Gerando milhares de imagens com modelo open source
- 06:15 Por que não o Z-Image Turbo
- 07:52 Qwen-Image-Edit Lightning
- 09:09 Instalando Python e ambiente virtual
- 11:43 O que é o Modal e os US$ 30 grátis por mês
- 13:37 Limite de uso para não gastar
- 14:14 `modal setup`
- 15:03 Criando a chave da API e o token do Hugging Face
- 18:13 Baixando o modelo
- 20:02 Deploy da API
- 21:00 Workflow do n8n
- 25:30 Cold start e timeout
- 26:37 Quanto custa por imagem
- 27:08 Gerando em lote (~3.600 imagens por mês)
- 30:25 Comunidade VIP

## Veja o vídeo

[![Imagens premium de produtos com IA open source](https://img.youtube.com/vi/xostcxP7w_I/maxresdefault.jpg)](https://www.youtube.com/watch?v=xostcxP7w_I)