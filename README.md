# claude-skills

Skills (Agent Skills) para o Claude.

| Skill | O que faz |
|---|---|
| [`advogado-analise-de-caso`](skills/advogado-analise-de-caso/SKILL.md) | Analisa um caso cível brasileiro a partir de áudios, vídeos, fotos e PDFs. Transcreve as gravações, renomeia e organiza as provas, e gera em `docs/` a linha do tempo, a análise jurídica, os trechos-chave, o texto de reclamação e os próximos passos |
| [`evernote-knowledge-base`](skills/evernote-knowledge-base/SKILL.md) | Salva conteúdo no Evernote como base de conhecimento: ingere documentos (Markdown/PDF) ou entregáveis da conversa (análises, resumos, transcrições), uma nota por documento com o texto integral convertido para ENML, tags reaproveitadas (sempre `Knowledge Base`) e PDFs anexados. Requer o conector do Evernote |

## Como usar

- **No Claude (app):** em Configurações → Capabilities → Skills, faça upload da pasta da skill compactada em .zip (a pasta contém `SKILL.md` e, quando houver, `scripts/`).
- **No Claude Code:** copie a pasta para `~/.claude/skills/` (pessoal) ou `.claude/skills/` (projeto).

## Estrutura

```
skills/
  advogado-analise-de-caso/
    SKILL.md                    # instruções da skill
    scripts/
      transcrever.py            # transcrição com faster-whisper (pt-BR)
      baixar_modelo_npm.sh      # baixa o modelo Whisper small via npm quando o Hugging Face está bloqueado
  evernote-knowledge-base/
    SKILL.md                    # instruções da skill (usa o conector do Evernote)
```

> Aviso: a skill `advogado-analise-de-caso` organiza e analisa casos com apoio de IA e não substitui a orientação de um advogado.
