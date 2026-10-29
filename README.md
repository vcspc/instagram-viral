# Instagram Viral Reels AI Agent

Ferramenta inteligente em Python para pesquisar, ranquear e analisar vídeos de **Instagram Reels** com maior engajamento e viralidade para qualquer nicho, orquestrada pela **IA do Google Gemini** e pela biblioteca **instagrapi**.

---

## Como Funciona

1. **Compreensão e Expansão Semântica (Agente Gemini)**: O usuário informa o nicho em linguagem natural (ex: *"vídeos de confeitaria com foco em bolos simples para iniciantes"*). O Gemini analisa o público-alvo e gera uma estratégia completa: hashtags principais de alta densidade, hashtags de cauda longa menos concorridas e termos de pesquisa textual.
2. **Coleta Híbrida e Resiliente**:
   - **Busca Textual Direta**: Consulta o mecanismo de busca oficial do Instagram (SERP) para o termo do usuário e as palavras-chave sugeridas pelo Gemini.
   - **Cascata Inteligente de Hashtags**: Tenta primeiro a aba de Reels (`clips`), recorre a publicações recentes (`recent`), aba de destaque (`top`) e busca textual.
   - **Filtro Abrangente de Vídeos**: Reconhece Reels em qualquer formato do Instagram (`media_type == 2`, `video_duration > 0`, `clips` ou `feed`).
3. **Loop de Refinamento Autônomo**: Se a meta de vídeos não for atingida na primeira rodada, o Gemini inspeciona o lote inicial e gera termos refinados e adjacentes para a rodada seguinte.
4. **Cálculo Ponderado de Viral Score**: Equilibra escala de visualizações com engajamento ativo, dando peso maior a comentários (que sinalizam debate e retenção para o algoritmo).
5. **Engenharia Reversa dos Top Reels**: O Gemini analisa os 10 melhores vídeos encontrados e decodifica os **ganchos (hooks) dos primeiros 3 segundos**, temas dominantes, estratégias de legenda e recomendações práticas.
6. **Exportação Automática**: Salva os resultados em **Markdown** (com links diretos clicáveis para cada Reel), **CSV** (para Excel/Google Sheets) e **JSON**.

---

## Estrutura do Projeto

```text
instagram-viral/
├── .env.example              # Modelo de configuração de credenciais
├── .gitignore                # Regras de segurança (protege .env, sessions/ e outputs/)
├── pyproject.toml            # Metadados e dependências do projeto
├── requirements.txt          # Dependências pip
├── README.md                 # Documentação completa
├── sessions/                 # Sessões autenticadas salvas (*.session.json)
├── outputs/                  # Relatórios exportados (MD, CSV, JSON)
├── src/
│   ├── main.py               # Ponto de entrada da aplicação
│   ├── config/
│   │   ├── settings.py       # Configurações Pydantic validadas do .env
│   │   └── logging_config.py # Configuração de logs com suporte UTF-8
│   ├── models/
│   │   ├── instagram.py      # Modelos Pydantic para Reels e Métricas
│   │   └── agent.py          # Schemas estruturados para o Gemini (Structured Outputs)
│   ├── instagram/
│   │   ├── session_manager.py# Gerenciador de autenticação, 2FA, Email Challenge e Cookies
│   │   ├── collector.py      # Coletor híbrido de Reels com múltiplos fallbacks
│   │   ├── engagement.py     # Fórmulas de cálculo de engajamento e Viral Score
│   │   └── rate_limiter.py   # Jitter aleatório e backoff anti-bloqueio
│   ├── agent/
│   │   ├── gemini_client.py  # Cliente do Google Gemini com saídas tipadas via Pydantic
│   │   ├── prompts.py        # Prompts especializados de planejamento e análise viral
│   │   ├── search_planner.py # Orquestrador de expansão e avaliação de rodadas
│   │   └── viral_analyzer.py # Analisador qualitativo de ganchos e estratégias
│   ├── reports/
│   │   ├── exporter.py       # Exportadores para Markdown, CSV e JSON
│   │   └── formatters.py     # Formatadores numéricos amigáveis (ex: 1.2M, 45K)
│   └── cli/
│       ├── app.py            # Interface de linha de comando com Typer
│       └── views.py          # Componentes visuais com Rich (tabelas e painéis)
└── tests/
    ├── test_engagement.py    # Testes unitários de métricas de engajamento
    ├── test_collector.py     # Testes das estratégias de busca e filtros de Reels
    ├── test_session_manager.py # Testes de persistência de sessão e injeção de cookies
    └── test_exporter.py      # Testes dos exportadores de relatórios
```

---

## Instalação

### 1. Clonar ou navegar até o diretório
```bash
cd "C:\Users\Vinícius\Documents\projetos\instagram-viral"
```

### 2. Criar e ativar o ambiente virtual (recomendado)
```bash
python -m venv .venv
# No Windows:
.venv\Scripts\activate
# No Linux/Mac:
source .venv/bin/activate
```

### 3. Instalar as dependências
```bash
pip install -r requirements.txt
```

---

## Configuração (.env)

Crie uma cópia do arquivo `.env.example` com o nome `.env`:

```bash
cp .env.example .env
```

Abra o arquivo `.env` e preencha as suas configurações:

```env
# 1. Chave gratuita do Google AI Studio: https://aistudio.google.com/
GEMINI_API_KEY=sua_chave_gemini_aqui
GEMINI_MODEL=gemini-2.5-flash

# 2. Credenciais do Instagram
# IMPORTANTE: Coloque o seu @nome_de_usuario (sem @). NÃO use endereço de e-mail!
INSTAGRAM_USERNAME=seu_perfil
INSTAGRAM_PASSWORD=sua_senha

# Opcional (se preferir autenticar via cookies do navegador):
INSTAGRAM_SESSIONID=

# Opcional: Chave de 2FA TOTP (se tiver configurado em app autenticador)
INSTAGRAM_2FA_SEED=

# Configurações de Delays de Segurança (em segundos)
REQUEST_DELAY_MIN=3.0
REQUEST_DELAY_MAX=6.0
MAX_SEARCH_ROUNDS=3
```

---

## Como Fazer Login (2 Métodos Suportados)

### Método 1: Login Nativo por Usuário e Senha (Recomendado)
1. No `.env`, certifique-se de que `INSTAGRAM_USERNAME` é o seu **nome de usuário do perfil** (ex: `joao.silva`, sem `@` e sem e-mail) e preencha `INSTAGRAM_PASSWORD`.
2. Execute o comando de login:
   ```bash
   python -m src.main login
   ```
3. **Verificação de Segurança (E-mail/SMS):** Por ser um acesso de uma nova aplicação, o Instagram enviará um código de confirmação de 6 dígitos para o seu e-mail ou SMS.
4. O terminal solicitará:
   ```
   Digite o código de 6 dígitos recebido por E-mail:
   ```
5. Digite o código e pressione Enter. A sessão será autenticada e gravada em `sessions/{seu_usuario}.session.json`.
6. **Pronto!** Uma vez salva, a sessão permanece ativa e as buscas futuras conectam-se automaticamente sem pedir senha ou códigos novamente.

---

### Método 2: Login via Cookies do Navegador (Anti-Invalidação)
Para evitar que o Instagram invalide a sessão do seu navegador ao detectar divergência de aparelho, o sistema inclui cabeçalhos web desktop de proteção:
1. Abra o Instagram no seu navegador e pressione **F12**.
2. Vá até a aba **Console**, digite:
   ```javascript
   document.cookie
   ```
3. Pressione Enter e copie o texto completo retornado (contendo `mid`, `ds_user_id`, `csrftoken`, `sessionid`).
4. Cole no seu arquivo `.env`:
   ```env
   INSTAGRAM_SESSIONID="mid=...; ds_user_id=...; sessionid=..."
   ```

---

## Modos de Operação da Ferramenta

A ferramenta possui dois modos principais de pesquisa:

---

### Modo 1: Pesquisa Temática por Nicho (`search`)
Pesquisa Reels virais em qualquer nicho em linguagem natural, expandindo em hashtags e termos semânticos com o Gemini:

```bash
python -m src.main search -q "bolos decorados simples" -t 1m -l 20
```

#### Parâmetros da CLI (`search`):
- `-q, --query TEXT`: Intenção ou nicho de pesquisa em linguagem natural (obrigatório).
- `-t, --timeframe TEXT`: Filtro por data de postagem: `'1w'` (1 semana), `'1m'` (1 mês), `'3m'` (3 meses), `'6m'` (6 meses), `'1y'` (1 ano), dias como `'7d'`, `'15d'`, ou `'all'` para todo o período (padrão: `all`).
- `-l, --limit INTEGER`: Quantidade de Reels únicos a coletar e analisar (padrão: 20).
- `-r, --rounds INTEGER`: Quantidade máxima de rodadas de refinamento do agente Gemini (padrão: 2).
- `--no-analysis`: Pula a engenharia reversa qualitativa do Gemini e gera apenas a tabela com métricas.
- `-v, --verbose`: Exibe logs detalhados de depuração da API.

---

### Modo 2: Auditoria de Perfil e Transcrição de Roteiros (`profile`)
Audita um perfil específico do Instagram passando a arroba (`@username`), analisa seguidores, posts, biografia, ranqueia os Reels de melhor desempenho, **baixa os Top Reels, converte em áudio via FFmpeg, transcreve com timestamps via Whisper** e decodifica a estratégia de roteiro com o Gemini:

```bash
python -m src.main profile --username @criador -l 30 -t 3m --top-transcribe 3
```

#### O que o modo de perfil realiza:
1. **Auditoria Cadastral:** Extrai e exibe total de seguidores, perfis seguidos, contagem de publicações, selo de verificado, biografia completa e links externos.
2. **Mineração e Ranking:** Coleta os Reels recentes do criador (com filtro opcional por data como `-t 1m` ou `-t 3m`) e calcula o `viral_score` ponderado.
3. **Download e Conversão de Áudio:** Baixa os Top N Reels mais virais do perfil e converte os vídeos para WAV 16kHz mono via **FFmpeg**.
4. **Transcrição Whisper com Timestamps:** Transcreve a fala com marcadores de tempo exatos (`[MM:SS - MM:SS] Texto falado`) e isola o **gancho falado nos primeiros 3 segundos**.
5. **Diagnóstico da IA Gemini:**
   - **Posicionamento e Bio:** Avalia a proposta de valor, público-alvo, CTA e sugere melhorias práticas na bio.
   - **Decodificação de Roteiro:** Analisa os ganchos auditivos dos primeiros 3s, ritmo de fala, pausas, retenção e chamadas para ação faladas (CTAs).
   - **Template de Roteiro:** Cria um roteiro passo a passo replicável inspirado no vídeo de maior sucesso do criador.
6. **Limpeza Automática:** Deleta imediatamente os arquivos temporários de vídeo e áudio baixados ao término da análise.

#### Parâmetros da CLI (`profile`):
- `-u, --username TEXT`: Nome de usuário do perfil no Instagram (ex: `@criador` ou `criador`) (obrigatório).
- `-l, --limit INTEGER`: Quantidade de Reels recentes do perfil a analisar (padrão: 30).
- `-t, --timeframe TEXT`: Filtro por período de postagem (`1w`, `1m`, `3m`, `6m`, `1y` ou `all`) (padrão: `all`).
- `-n, --top-transcribe INTEGER`: Quantidade dos Reels mais virais do perfil para baixar e transcrever (padrão: 3).
- `-w, --whisper-model TEXT`: Tamanho do modelo Whisper (`base`, `tiny`, `small`) (padrão: `base`).
- `--no-analysis`: Pula o diagnóstico qualitativo da IA e gera apenas as tabelas e transcrições.
- `-v, --verbose`: Exibe logs detalhados de depuração.

---

## Métricas de Engajamento e Viral Score

Cada Reel minerado é avaliado por uma fórmula matemática ponderada:

$$\text{Taxa de Engajamento (\%)} = \frac{\text{likes} + \text{comentários}}{\max(\text{views}, 1)} \times 100$$

$$\text{Viral Score} = \frac{\text{likes} \times 1.0 + \text{comentários} \times 3.5}{\log_{10}(\max(\text{views}, 10)) + 1}$$

- **Por que comentários têm peso 3.5?** Comentários exigem esforço ativo do usuário, geram debates e são o sinal de maior peso no algoritmo de distribuição de Reels do Instagram.
- **Por que normalizar por $\log_{10}(\text{views})$?** Impede que um vídeo com apenas 5 visualizações e 2 curtidas tenha um score artificialmente maior do que um vídeo viral de 500.000 visualizações com milhares de interações reais.

---

## Relatórios Exportados

Ao término da pesquisa, são gerados automaticamente 3 arquivos na pasta `outputs/`:
- `outputs/{nicho}_{data}.md`: Relatório executivo completo em Markdown com a estratégia do Gemini, análise de ganchos dos primeiros 3s, temas recorrentes e tabela com **links diretos clicáveis para cada Reel** (`https://www.instagram.com/reel/{code}/`).
- `outputs/{nicho}_{data}.csv`: Planilha completa para importação direta no Excel ou Google Sheets.
- `outputs/{nicho}_{data}.json`: Arquivo estruturado com todos os metadados brutos para integração com outras ferramentas.

---

## Testes Automatizados

O projeto conta com uma suíte de testes unitários que não consome limites de API nem tokens:

```bash
python -m unittest discover -s tests -v
```
