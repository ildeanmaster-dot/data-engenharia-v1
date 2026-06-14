# 🔌 Bloco 1 — Ingestão / Bronze

> **Especialista do bloco:** Engenheiro de Ingestão
> **Objetivo:** construir o cliente da API da Câmara e a camada **Bronze** — o dado cru, fielmente preservado, com auditoria — lidando com paginação, falhas de rede e endpoints que dependem de outros (*fan-out*).

---

## 1. Por que este bloco existe

A Bronze é o **alicerce de confiança** do pipeline. Se ela estiver errada, todo o resto está. A regra de ouro: **Bronze nunca transforma regra de negócio** — ela só copia o que a fonte mandou e carimba *de onde* e *quando* veio. Por quê? Porque é a sua única evidência da origem. Se amanhã uma regra de limpeza estiver errada, você reprocessa a partir da Bronze sem precisar bater na API de novo.

O desafio cobra isso diretamente: *"métodos para rastrear a origem e evolução dos dados (campos de auditoria...)"* e *"controle de paginação"*.

A fonte: **API REST dos Dados Abertos da Câmara** — `https://dadosabertos.camara.leg.br/api/v2`.

---

## 2. Conceitos em 3 níveis

### 2.1 API REST e JSON
- 🟢 **Júnior:** você faz um `GET` numa URL e recebe **JSON** de volta. Na API da Câmara, a lista vem dentro da chave `"dados"`.
- 🟡 **Pleno:** você trata o **status HTTP** (200 ok; 4xx erro seu; 5xx/429 erro do servidor/limite) e separa o *cliente HTTP* (como busca) da *lógica de coleta* (o que busca). Isso é testável e reusável.
- 🔴 **Sênior:** você trata a API como um **contrato instável**: ela pode mudar formato, ficar lenta ou te bloquear. Seu cliente precisa ser defensivo (timeout, retry, idempotência) para não derrubar a fonte nem o seu pipeline.

### 2.2 Paginação
- 🟢 **Júnior:** a API devolve no máximo ~100 itens; para pegar o resto você pede `?pagina=2`, `?pagina=3`...
- 🟡 **Pleno:** em vez de chutar o número da página, siga o **header `Link`** com `rel="next"` — é o contrato oficial e não quebra se a regra de paginação mudar. Pare quando não houver `next`.
- 🔴 **Sênior:** paginação ingênua pode entrar em **loop infinito** ou duplicar dados. Valide que a próxima página é realmente maior que a atual, ponha um teto (`max_pages`) e um `sleep` curto para respeitar rate limit.

### 2.3 Resiliência: retry, backoff e rate limit
- 🟢 **Júnior:** se der erro de rede, tenta de novo.
- 🟡 **Pleno:** tente de novo **só nos erros que valem** (429, 500, 502, 503, 504) — não em 404. Entre tentativas, espere um tempo crescente (**backoff exponencial**: 1s, 1.5s, 2.25s...).
- 🔴 **Sênior:** retry sem backoff vira **ataque de negação de serviço contra a própria fonte**. O backoff dá tempo de o servidor se recuperar; o rate limit (`sleep` entre páginas) evita tomar 429. Em produção isso vira política central com jitter e *circuit breaker*.

### 2.4 Fan-out (endpoints filhos)
- 🟢 **Júnior:** alguns dados precisam de um ID antes: para pegar as despesas de um deputado, preciso primeiro da lista de deputados, depois chamo `/deputados/{id}/despesas`.
- 🟡 **Pleno:** isso é um **fan-out**: para cada pai, N chamadas filhas. Isso explode rápido (1000 deputados × 50 despesas = 50 mil chamadas), então você **limita** quantos pais processa.
- 🔴 **Sênior:** fan-out é o maior risco de custo/tempo da ingestão. Você o controla com limites, paraleliza com cuidado (respeitando rate limit), e idealmente o torna **incremental** (só puxa o que mudou — assunto do Bloco 6).

### 2.5 Campos de auditoria
- 🟢 **Júnior:** em cada registro salvo, adiciono de onde veio (`source_url`) e quando coletei (`ingest_ts`).
- 🟡 **Pleno:** esses campos são a base da **linhagem**. Com eles eu reproduzo a coleta, depuro um registro estranho e sei a "validade" do dado.
- 🔴 **Sênior:** auditoria na Bronze + **Time Travel** do Delta = rastreabilidade ponta a ponta exigida em ambientes regulados. Você consegue responder "qual era o estado deste dado no dia X e de onde ele veio?".

### 2.6 Votação simbólica vs nominal (lição de campo) 🗳️
Descoberto na prática quando `votacao_votos` veio com **0 registros**.
- 🟢 **Júnior:** nem todo endpoint que existe retorna dados. `/votacoes/{id}/votos` só tem conteúdo quando a votação é **nominal** (voto registrado deputado a deputado). A maioria é **simbólica** ("aprovado por acordo") e devolve lista vazia.
- 🟡 **Pleno:** votações nominais acontecem sobretudo no **Plenário** (`idOrgao=180`). Coletar votações de comissão e esperar votos individuais é coletar o **pai errado**. A correção foi filtrar a fonte: `idOrgao=180` + só votações com placar (`"...Total: N"` na descrição).
- 🔴 **Sênior:** usar o texto da descrição como filtro é uma **heurística barata** (evita centenas de chamadas a `/votos` que voltariam vazias), mas **frágil** — depende do texto não mudar. A alternativa robusta é chamar `/votos` e guardar só o não-vazio, ao custo de mais requisições. Escolher entre as duas é um trade-off **custo × robustez** que se documenta no registro de decisões. Saber *que existe* essa diferença é o que separa quem leu o dado de quem só copiou o código.

### 2.7 Observabilidade — enxergar o pipeline rodando 👀
Quando o fan-out de despesas parecia "travado" por minutos.
- 🟢 **Júnior:** imprima progresso (`print` por item) para saber que o processo está vivo.
- 🟡 **Pleno:** monitore sem tocar no código abrindo um 2º terminal e contando as linhas dos JSONL crescendo; e use `flush=True`/`python -u` para a saída aparecer em tempo real.
- 🔴 **Sênior:** em produção isso vira **logging estruturado** + métricas (volume, latência, taxa de erro por execução) num dashboard, com alertas. Observabilidade é requisito do desafio ("documentar triggers, dependências, recuperação") — não um luxo.

---

## 3. Mão na massa — reconstruindo a Bronze

> Você digita; eu explico o porquê de cada peça. No fim comparamos com o gabarito (`src/api.py`, `src/bronze.py`, `conf/config.py`).

### 📍 Onde fazer cada coisa: VSCode (local) **e depois** Databricks

A coleta da Bronze é trabalho de **rede (I/O-bound)**, não de Spark. Então o desenvolvimento acontece em **dois ambientes complementares**:

| Etapa | Onde | Por quê |
|---|---|---|
| **Passos 1–6** (config, cliente HTTP, paginação, fan-out, gravar JSONL) | 💻 **VSCode local** + venv | Itera rápido, roda em segundos, testável com `pytest`, sem subir cluster a cada mudança. É puro Python (`requests` + arquivos). |
| Versionar o código | 💻 VSCode → **Git** (push) | O Databricks vai puxar esse mesmo código via *Git folder* (Repos). |
| **Materializar Bronze como Delta** (`notebooks/01_ingest_bronze.py`) | ☁️ **Databricks** | Lê os JSONL do **Volume UC** e grava tabela Delta `camara.bronze.*` usando PySpark. |

**Resumo prático:** faça **todo o passo a passo abaixo no VSCode** (é onde você reconstrói e testa a lógica). Só vá ao Databricks no final, no Passo "No Databricks", para transformar o JSONL cru em tabela Delta. Isso espelha a arquitetura do Bloco 0: *coleta fora do cluster, cluster só processa*.

> 💡 Dá para fazer **tudo** dentro do Databricks (importar os `.py` e rodar como notebook), mas você perde a velocidade de iteração local e o `pytest` fica mais chato. Por isso recomendo VSCode para a lógica e Databricks para a materialização.

### Passo 1 — O catálogo de endpoints (`conf/config.py`)
Em vez de espalhar URLs pelo código, centralize num **dicionário**. Cada endpoint declara: caminho, params default, se é paginado e (se for filho) de quem ele depende.

```python
ENDPOINTS = {
    "deputados": {"path": "/deputados", "params": {"itens": 100, "ordem": "ASC", "ordenarPor": "nome"}, "paginated": True},
    "frentes":   {"path": "/frentes",   "params": {"idLegislatura": 57, "itens": 100}, "paginated": True},
    # fan-out: depende do id do pai
    "deputado_despesas": {"path": "/deputados/{id}/despesas", "params": {"itens": 100, "ano": ANO_CEAP},
                          "paginated": True, "fanout_from": "deputados"},
}
FANOUT_LIMITS = {"deputado_despesas": 20}   # trava para não explodir a coleta
SAMPLES_DIR = "data/samples"
```

> ⚠️ **Sobre o `ano` das despesas (CEAP).** O endpoint `/deputados/{id}/despesas` filtra os gastos por **ano** — é um parâmetro da própria API. No código original esse valor estava **fixo em `2024`** (*hardcoded*), por dois motivos: era o ano de referência quando o projeto foi escrito e fixar um ano **limita o volume** da coleta (sem filtro, viriam despesas de vários anos e o fan-out explodiria).
>
> O problema é que valor fixo no código envelhece: estamos em **2026**, e a 57ª legislatura vai de 2023 a 2027, então 2024/2025/2026 são todos válidos. Boa prática é **não cravar** — deixe configurável e escolha o(s) ano(s) que vai analisar. Por isso, em vez de `"ano": 2024`, defina no topo do arquivo:
>
> ```python
> from datetime import datetime
> ANO_CEAP = datetime.now().year   # ano corrente; ou troque por um ano fixo p/ análise (ex.: 2025)
> ```
>
> 🟡 **Nível pleno:** ano dinâmico evita que o pipeline "pare no tempo". 🔴 **Nível sênior:** em produção você nem fixaria um ano — faria **carga incremental** puxando só o delta desde a última coleta (assunto do Bloco 6). Fixar o ano aqui é uma simplificação consciente para o volume do desafio, e isso é o tipo de decisão que se **documenta** (vai pro registro de decisões técnicas).

**Por quê:** configuração como dado (não código espalhado) deixa a coleta declarativa e fácil de estender. Trocar um limite — ou o ano da CEAP — não exige mexer na lógica.

### Passo 2 — O cliente HTTP defensivo (`src/api.py`)
Uma função só para *buscar*, com retry nos erros certos:

```python
def get_json(path, params=None, retries=3, backoff=1.5):
    url = f"{BASE_URL}{path}"
    for attempt in range(retries):
        r = requests.get(url, headers=DEFAULT_HEADERS, params=params, timeout=30)
        if r.status_code == 200:
            return r
        if r.status_code in (429, 500, 502, 503, 504):   # vale retry
            time.sleep(backoff ** attempt)               # backoff exponencial
            continue
        raise CamaraAPIError(f"HTTP {r.status_code}")     # 4xx: não insiste
    raise CamaraAPIError("falhou após retries")
```
**Por quê:** `timeout` evita travar para sempre; o `if` separa erro transitório de erro definitivo; o `backoff ** attempt` cresce a espera.

### Passo 3 — Iterar páginas seguindo o `Link` (`src/api.py`)
```python
def iter_pages(path, params=None, max_pages=None):
    page = 1
    while True:
        if max_pages and page > max_pages:
            break
        params["pagina"] = page
        r = get_json(path, params=params)
        yield r.json().get("dados", []), page, r.url
        next_url = parse_next_page(r.headers.get("Link"))   # contrato oficial
        if not next_url:
            break
        page += 1
        time.sleep(0.25)   # rate limit básico
```
**Por quê:** `yield` (gerador) processa página a página sem segurar tudo na memória. Parar no `Link` ausente é mais robusto que adivinhar o total.

> 🔄 **Revisão (após explorar a API real):** confirmamos que a paginação vem **no corpo** da resposta, no array `links` com `rel="next"` — e está sempre presente. É mais confiável que o header `Link` (que proxies/caches podem remover). Versão recomendada do laço, lendo do corpo:
> ```python
> body = r.json()
> records = body.get("dados", [])
> yield records, page, r.url
> has_next = any(l.get("rel") == "next" for l in body.get("links", []))
> if not has_next:
>     break
> page += 1
> ```
> Com isso, `parse_next_page` e os imports `urlparse/parse_qs` ficam dispensáveis. 💡 Bônus confirmado: na CEAP, os campos `ano` e `mes` já vêm prontos na resposta — para agregação mensal você **não precisa** derivar do `data_documento`.

### Passo 4 — Gravar a Bronze com auditoria (`src/bronze.py`)
```python
def _audit(endpoint, source_url):
    return {"ingest_ts": datetime.now(timezone.utc).isoformat(),
            "endpoint": endpoint, "source_url": source_url}

def collect_simple(name, max_pages=None):
    cfg = ENDPOINTS[name]
    out = Path(SAMPLES_DIR) / f"{name}.jsonl"
    with out.open("w", encoding="utf-8") as f:
        for records, _, source_url in iter_pages(cfg["path"], cfg["params"], max_pages):
            for rec in records:
                rec["_audit"] = _audit(name, source_url)     # carimbo de origem
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")   # 1 JSON por linha
```
**Por quê:** **JSONL** (um objeto por linha) é o formato cru ideal — append-friendly, streamável, e você lê linha a linha sem carregar o arquivo inteiro. `ensure_ascii=False` preserva acentos (Brasília, não Brasília).

### Passo 5 — Fan-out (`src/bronze.py`)
Leia os IDs do pai já coletado e itere os filhos, com limite e **tolerância a falha por item**:
```python
def collect_fanout(name, max_parents=None):
    cfg = ENDPOINTS[name]
    parent_ids = _load_parents(cfg["fanout_from"])[: max_parents or FANOUT_LIMITS.get(name, 10)]
    for pid in parent_ids:
        try:
            path = cfg["path"].format(id=pid)
            # ... coleta e grava, carimbando rec["_parent_id"] = pid
        except Exception as e:
            print(f"[warn] {name} pid={pid}: {e}")   # registra, mas não derruba a coleta toda
```
**Por quê:** um deputado com erro não pode abortar os outros 19. Falha isolada + log = resiliência.

### Passo 6 — Rodar e conferir
```bash
python -m src.runner            # coleta tudo
# ou pular coleta se já tiver os JSONL:
python -m src.runner --skip-bronze
head -n 1 data/samples/deputados.jsonl   # veja um registro cru + _audit
```

### No Databricks (Bronze "de verdade")
O notebook `01_ingest_bronze.py` lê esses JSONL do **Volume UC** e materializa como **tabela Delta** `camara.bronze.*`. A coleta (passos acima) roda **fora do cluster** e só entrega arquivos no Volume — exatamente a separação que discutimos no Bloco 0.

---

## ✅ O que você aprendeu
- Por que a Bronze preserva o dado **cru** e só adiciona auditoria.
- Consumir uma **API REST** paginada seguindo o header `Link`.
- Resiliência: **retry com backoff** nos status certos e **rate limit**.
- **Fan-out** de endpoints filhos com limite e tolerância a falha.
- Gravar em **JSONL** com `ingest_ts`/`source_url` e por que esse formato.
- Como isso vira tabela **Delta** no Volume do Unity Catalog.

## 🎯 O que você deveria dominar para seguir
- Explicar a diferença entre erro que merece retry (429/5xx) e erro que não (4xx).
- Desenhar o fluxo: catálogo de endpoints → cliente HTTP → iter_pages → grava JSONL.
- Justificar por que a coleta não aplica regra de negócio.
- Saber o que são `ingest_ts`, `source_url`, `_parent_id` e para que servem.

## 📝 Quiz certo/errado (gabarito comentado)
1. *"Em um erro HTTP 404, o cliente deve tentar novamente várias vezes."*
   ❌ **Errado.** 404 é erro definitivo (recurso não existe); retry só faz sentido em 429/5xx (transitórios).
2. *"JSONL guarda um array JSON único com todos os registros."*
   ❌ **Errado.** JSONL é **um objeto JSON por linha** — justamente para ler/gravar em streaming.
3. *"Seguir o header `Link rel=next` é mais robusto que incrementar `?pagina=` manualmente."*
   ✅ **Certo.** É o contrato oficial; não quebra se a paginação mudar.
4. *"No fan-out, se a coleta de um pai falhar, a coleta inteira deve abortar."*
   ❌ **Errado.** Você registra o erro daquele item e segue; resiliência exige isolar a falha.
5. *"Backoff exponencial existe para não sobrecarregar a fonte que já está em apuros."*
   ✅ **Certo.** Espera crescente dá tempo de o servidor se recuperar e evita novos 429.
6. *"Se o endpoint `/votacoes/{id}/votos` retorna lista vazia, é porque o pipeline tem um bug."*
   ❌ **Errado.** Pode ser uma votação **simbólica**, que não registra voto individual. O "vazio" é o dado correto; o ajuste é coletar votações **nominais** (Plenário).

## 🎤 Perguntas de entrevista (com resposta-modelo)

**🟢 Júnior — "Como você pagina uma API que devolve 100 itens por vez?"**
> Faço uma requisição inicial e, enquanto houver próxima página, continuo. Na API da Câmara cada resposta traz um array `links`; enquanto existir um `rel="next"`, eu sigo para a próxima e paro quando ele some. Assim não preciso adivinhar quantas páginas existem. (O header HTTP `Link` traz a mesma informação, mas o `links` do corpo é mais confiável.)

**🟡 Pleno — "Você chamou um endpoint e veio vazio, mas você tinha certeza de que havia dados. Como investiga?"**
> Primeiro confirmo na fonte: chamo a URL exata (que tenho gravada em `source_url`) no navegador/curl e vejo a resposta crua. Se a API realmente devolve vazio, o "bug" não é meu — é a semântica do dado. Foi o que aconteceu com os votos: o endpoint só retorna voto individual em votação **nominal**; as simbólicas vêm vazias. A correção foi coletar o pai certo (votações do Plenário com placar registrado), não mexer no coletor.

**🟡 Pleno — "Por que separar o cliente HTTP da lógica de coleta?"**
> Porque são responsabilidades diferentes. O cliente sabe *como* buscar (retry, timeout, status), e deve ser genérico e testável. A coleta sabe *o que* buscar e como salvar. Separados, eu testo o retry com mocks sem bater na rede, reuso o cliente em todos os endpoints, e mudo a regra de coleta sem tocar na de rede.

**🔴 Sênior — "Sua ingestão precisa puxar despesas de 1000 deputados, cada um com centenas de notas. Como você projeta isso sem estourar tempo, custo e sem ser bloqueado?"**
> Primeiro, eu trato como fan-out controlado: limito o número de pais por execução e torno a carga **incremental** — guardo o último estado (data/ID/hash) e só busco o delta, em vez de varrer tudo toda vez. Respeito o rate limit com sleep e backoff com jitter para não tomar 429, e isolo falha por item para não perder a corrida inteira por um erro. Rodo a coleta **fora do cluster** (job leve entregando no object storage), porque é trabalho I/O-bound e não justifica compute caro parado. Gravo cru com auditoria para poder reprocessar sem rebater na API. E monitoro: volume coletado, taxa de erro e latência, com runbook de replay se uma janela falhar.

---

### ➡️ Próximo: **Bloco 2 — Prata / Silver** (Engenheiro de Transformação): ler o cru, padronizar nomes, tipar datas, achatar estruturas aninhadas e deduplicar por chave primária.
