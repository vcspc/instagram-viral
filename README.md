# Instagram Viral Reels AI Agent

Ferramenta inteligente em Python para pesquisar, ranquear e analisar vídeos de **Instagram Reels** com maior engajamento e viralidade para qualquer nicho, orquestrada pela **IA do Google Gemini** e pela biblioteca **instagrapi**.

---

## Como Funciona

1. **Agente Gemini Entende a Intenção**: O usuário digita o nicho ou objetivo em linguagem natural (ex: *"vídeos de confeitaria com foco em bolos simples para iniciantes"*). O Gemini expande essa ideia em hashtags principais, hashtags de cauda longa e termos de busca.
2. **Coleta Resiliente com instagrapi**: Varre o Instagram filtrando estritamente publicações do tipo Reels (`clips`), gerenciando sessões para não precisar logar repetidamente e usando delays de segurança contra bloqueios.
3. **Loop de Refinamento Autônomo**: Se a meta de vídeos não for atingida, o Gemini avalia o lote inicial e escolhe novos termos complementares para uma segunda rodada de busca.
4. **Cálculo de Viral Score**: Pondera visualizações, curtidas e comentários (com peso maior em comentários, que indicam alto debate no algoritmo).
5. **Engenharia Reversa de Conteúdo**: O Gemini analisa os 10 melhores Reels encontrados e decodifica os **ganchos (hooks) dos primeiros 3 segundos**, temas dominantes, estratégias de legenda e recomendações práticas.
6. **Relatórios Automáticos**: Exporta os resultados em **Markdown** (com links clicáveis para abrir os Reels), **CSV** (para Excel/Google Sheets) e **JSON**.

---

## Instalação Rápida

### 1. Clonar ou navegar até o diretório
```bash
cd "C:\Users\Vinícius\Documents\projetos\instagram-viral"
```

### 2. Criar e ativar o ambiente virtual (opcional, recomendado)
```bash
python -m venv .venv
# No Windows:
.venv\Scripts\activate
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

Abra o `.env` e preencha:
```env
# Chave gratuita do Google AI Studio: https://aistudio.google.com/
GEMINI_API_KEY=sua_chave_aqui
GEMINI_MODEL=gemini-2.5-flash

# Suas credenciais do Instagram (recomendado usar uma conta secundária para pesquisas)
INSTAGRAM_USERNAME=seu_usuario
INSTAGRAM_PASSWORD=sua_senha

# Opcional: Chave de 2FA TOTP (se tiver 2FA ativado)
INSTAGRAM_2FA_SEED=
```

---

## Como Usar

### 1. Primeiro Login (Opcional, salva a sessão em disco)
```bash
python -m src.main login
```
*Isso salva o arquivo de sessão em `sessions/`. Nas próximas execuções, o login será automático.*

### 2. Pesquisar Reels Virais
Para pesquisar vídeos virais em qualquer tema ou nicho:

```bash
python -m src.main search --query "investimentos e finanças para jovens iniciantes" --limit 20
```

### 3. Opções de Comando
- `-q, --query TEXT`: Nicho ou objetivo da busca (obrigatório).
- `-l, --limit INTEGER`: Quantidade de Reels únicos a coletar e analisar (padrão: 20).
- `-r, --rounds INTEGER`: Quantidade máxima de rodadas de refinamento do agente Gemini (padrão: 2).
- `--no-analysis`: Pula a engenharia reversa qualitativa do Gemini e gera apenas a tabela com métricas.
- `-v, --verbose`: Exibe logs detalhados de depuração.

---

## Relatórios Gerados

Ao término de cada busca, os arquivos são salvos automaticamente na pasta `outputs/`:
- `outputs/{nicho}_{timestamp}.md`: Relatório executivo completo em Markdown com os insights da IA e a tabela de vídeos com links diretos `https://www.instagram.com/reel/{code}/`.
- `outputs/{nicho}_{timestamp}.csv`: Planilha completa para abrir no Excel ou Google Sheets.
- `outputs/{nicho}_{timestamp}.json`: Dados brutos estruturados com todos os metadados.
