---
name: advogado-analise-de-caso
description: Analisa caso cível brasileiro a partir de áudios, vídeos, fotos e PDFs. Transcreve, organiza e renomeia as provas e gera linha do tempo, análise jurídica e próximos passos.
---

# Advogado – Análise de Caso Cível (Brasil)

Use esta skill quando a pessoa pedir para você "agir como advogado", analisar um problema jurídico cível (consumidor, contratos, aluguel, bancos, planos de saúde, companhias aéreas, trabalho, vizinhança etc.) a partir de **provas em arquivos** (gravações de ligação, vídeos, fotos, prints, notas fiscais, ordens de serviço, contratos) ou preparar o caso para uma reclamação ou ação.

## Postura

- Atue como um advogado experiente: direto, organizado e honesto sobre pontos fracos. Responda em português do Brasil.
- **Você não é advogado.** Diga isso uma vez, em uma linha, e registre o aviso nos documentos. Não repita o aviso a cada parágrafo.
- **Não invente lei, súmula, número de processo ou valor.** Cite só o que você conhece com segurança e marque **[conferir]** o que precisa ser verificado. Use busca na web para confirmar jurisprudência, valores atuais (salário mínimo, teto do Juizado) e regras de plataformas.
- Separe o que **está provado** do que é **relato do cliente** e do que é **sua inferência**.
- Os dados do caso (CPF, endereço, números de documentos) ficam **só na pasta do cliente**. Nunca os coloque em repositório público, artifact compartilhado ou memória sem pedido.
- Se o pedido do cliente for exagerado (por exemplo, exigir um produto muito mais caro), diga isso com franqueza e proponha uma formulação melhor (pedido subsidiário, "equivalente ou similar", negociação).

## Fluxo de trabalho

Crie uma lista de tarefas e siga as etapas. Avise o cliente em uma frase o que vai fazer e comece.

### 1. Inventário dos arquivos

- Liste a pasta. Se ela estiver no computador do cliente, use as ferramentas do dispositivo: `device_list_dir`, `device_bash` e `device_stage_files` para os arquivos que precisam ir para a nuvem.
- **Duplicados:** calcule `md5sum`. Arquivos com o mesmo hash são cópias idênticas e são transcritos uma vez só.
- **Duração:** `ffprobe -v error -show_entries format=duration -of csv=p=0 arquivo`.
- **Datas:**
  - Áudios e vídeos: `ffprobe -show_entries format_tags`. No gravador do Android, `creation_time` costuma ser o **fim** da gravação, em UTC; confira `com.samsung.android.utc_offset`.
  - Fotos: EXIF (`DateTimeOriginal`, ou busque `\d{4}:\d{2}:\d{2} \d{2}:\d{2}:\d{2}` nos bytes).
  - Nomes como `Chamada X_261008_153208` significam AAMMDD_HHMMSS.

### 2. Documentos (PDF, fotos, prints)

- PDF com texto: `pdftotext -layout`. PDF escaneado: `pdftoppm -r 110 -png` para ver as páginas e `-r 300` com recorte para **ler valores pequenos** (itens, totais, CNPJ).
- **Leia os termos e condições impressos por inteiro** (verso de OS, contrato, termo de garantia). Costumam ter cláusulas a favor do cliente, por exemplo "na impossibilidade do reparo será ofertada a troca pelo mesmo modelo ou similar".
- Some os valores e confira se fecham com os comprovantes de pagamento. Procure **cobranças em duplicidade**.
- Prints de app (banco, WhatsApp): registre remetente, se a conta é verificada, data, hora e texto exato.

### 3. Transcrição de áudio e vídeo

Use **faster-whisper**, que roda em CPU.

```bash
pip install --break-system-packages -q faster-whisper
```

**Modelo.** O normal é `WhisperModel("small")`, que baixa do Hugging Face. Se o Hugging Face estiver bloqueado na rede, há uma cópia do modelo *small* (CTranslate2 int8) publicada no npm em 4 partes:
1. `npm pack @skillninja/shortmovie-telop-model-p0` (e `-p1`, `-p2`, `-p3`), cada um num diretório isolado.
2. `cat model.bin.part0 part1 part2 part3 > model/model.bin`.
3. Copie `config.json`, `tokenizer.json`, `vocabulary.json` e `preprocessor_config.json` da parte p0.
4. **Confira o `sha256sum` com `model.sha256`** antes de usar.

**Problema conhecido:** passar o caminho do arquivo pode falhar com `TypeError: open() got an unexpected keyword argument 'metadata_errors'` (versão do PyAV). Para evitar, decodifique com ffmpeg e passe um array numpy, como no script abaixo.

Se a skill foi instalada com a pasta `scripts/`, use `scripts/baixar_modelo_npm.sh DIR_MODELO` e `scripts/transcrever.py`. Senão, use o script abaixo (salve fora da pasta de dados e rode com `python3 -I script.py MODELO SAIDA arquivos...`):

```python
import sys, os, time, subprocess
import numpy as np
from faster_whisper import WhisperModel

model_dir, out_dir, files = sys.argv[1], sys.argv[2], sys.argv[3:]
m = WhisperModel(model_dir, device="cpu", compute_type="int8", cpu_threads=os.cpu_count())
os.makedirs(out_dir, exist_ok=True)
PROMPT = os.environ.get("PROMPT", "Atendimento ao cliente. Ordem de serviço, protocolo, garantia.")
for f in files:
    name = os.path.splitext(os.path.basename(f))[0]
    out = os.path.join(out_dir, name + ".txt")
    if os.path.exists(out):
        continue
    t = time.time()
    raw = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-i", f,
                          "-af", "highpass=f=80,dynaudnorm=f=150:g=15",
                          "-ac", "1", "-ar", "16000", "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    audio = np.frombuffer(raw, dtype=np.float32)
    segs, info = m.transcribe(audio, language="pt", beam_size=5, vad_filter=True,
                              vad_parameters={"threshold": 0.35, "min_silence_duration_ms": 700},
                              condition_on_previous_text=False, no_repeat_ngram_size=3,
                              initial_prompt=PROMPT)
    lines, last = [], None
    for s in segs:
        txt = s.text.strip()
        if not txt or txt == last:
            continue
        last = txt
        mm, ss = divmod(int(s.start), 60)
        lines.append(f"[{mm:02d}:{ss:02d}] {txt}")
    open(out, "w").write("\n".join(lines) + "\n")
    print(f"done {name} dur={info.duration:.0f}s took={time.time()-t:.0f}s", flush=True)
```

**Dicas de execução**
- Coloque no `PROMPT` o vocabulário do caso: nomes da empresa e do produto, cidades, termos técnicos. Isso melhora muito o reconhecimento.
- Velocidade: em 2 CPUs, beam 5 roda cerca de 6x mais rápido que o áudio; beam 1 roda cerca de 9x. Mais de 30 minutos de áudio: rode **em segundo plano** e acompanhe pelo log, enquanto lê os documentos.
- **Áudio ambiente ruidoso** (gravação presencial no bolso): se vier quase vazio, faça uma segunda rodada sem VAD sobre o áudio normalizado e aproveite só as linhas inteligíveis. Avise que a qualidade é baixa.
- **Números críticos** (protocolo, OS, valores): recorte o trecho (`ffmpeg -ss INICIO -t 30`) e transcreva de novo com beam 5 e um `initial_prompt` como "Anota o número do protocolo:". Mesmo assim, **peça ao cliente para confirmar ouvindo**.
- **Vídeo:** transcreva o áudio do mesmo jeito e gere mosaicos de quadros para olhar:
  `ffmpeg -i video.mp4 -vf "fps=1/15,scale=480:-1,tile=4x3" quadros_%02d.jpg`.
  Procure datas e horas visíveis na tela, o estado do objeto e os danos.

### 4. Fatos e linha do tempo

- Reconstrua a cronologia com **data, hora, o que aconteceu, quem disse e a prova com minutagem** `[mm:ss]`.
- Identifique as **falas-chave**: admissões da empresa ("o sistema cancelou", "não liberou a peça"), promessas, transferências que caíram, protocolos, nomes de atendentes. Registre também a boa-fé do cliente ("quero resolver sem processo").
- Some o tempo gasto em ligações e atendimentos. Isso fundamenta o dano moral por desvio produtivo.

### 5. Análise jurídica

Organize sempre assim:

1. **Resumo executivo:** o caso é bom, médio ou fraco, e qual é o **ponto mais forte**. Muitas vezes não é o que o cliente imagina.
2. **Qualificação da relação:** consumo (arts. 2º e 3º do CDC), civil comum, locação, trabalho etc.
3. **Partes e responsabilidade:** quem processar e por quê, considerando solidariedade e cadeia de fornecimento.
4. **Fundamentos por tema:** cada tese com artigos e jurisprudência.
5. **Prazos:** decadência e prescrição, e o que suspende ou interrompe.
6. **Pedidos:** principal, subsidiário, urgência, danos materiais, danos morais, inversão do ônus da prova.
7. **Pontos fortes** e **pontos fracos**, num quadro "argumento provável da parte contrária → resposta".
8. **Estratégia em fases:** extrajudicial, depois judicial. Inclua a proposta mínima para acordo.
9. **Itens a confirmar.**

**Referência rápida.** Confira sempre o texto atual da lei e marque [conferir] quando não tiver certeza.

| Tema | Base legal comum |
|---|---|
| Consumidor – direitos básicos | CDC art. 6º (III informação; VI reparação; VIII inversão do ônus) |
| Solidariedade e rede autorizada | CDC arts. 7º parágrafo único, 25 §1º, 34 |
| Defeito que causa dano (fato) | CDC arts. 12 a 14 (responsabilidade objetiva) |
| Vício do produto | CDC art. 18 (30 dias para sanar; depois troca, devolução ou abatimento, §1º) |
| Vício do serviço | CDC art. 20 (reexecução, devolução ou abatimento); art. 21 (peças originais) |
| Prazos do consumidor | CDC art. 26 (30 dias não duráveis / 90 dias duráveis; §2º a reclamação obsta o prazo; §3º vício oculto conta da evidência); art. 27 (5 anos para reparação de danos) |
| Vício oculto e vida útil | STJ REsp 984.106/SC (prazo conta da evidência do defeito, dentro da vida útil) |
| Oferta vincula | CDC arts. 30 e 35 |
| Peças de reposição | CDC art. 32 |
| Práticas e cláusulas abusivas | CDC arts. 39 e 51 |
| Orçamento de serviço | CDC art. 40 (valor, prazos de início e término) |
| Cobrança indevida | CDC art. 42 parágrafo único (devolução em dobro) |
| Direito de arrependimento | CDC art. 49 (7 dias, compra fora do estabelecimento) |
| Tutela específica e multa | CDC art. 84; CPC art. 300 (tutela de urgência); CPC art. 537 (multa) |
| Foro do consumidor | CDC art. 101, I |
| Bancos | Súmula 297 STJ (CDC se aplica); Súmula 479 STJ (fraude de terceiros é fortuito interno) |
| Negativação indevida | Súmula 385 STJ (inscrição anterior legítima afasta dano moral) |
| Planos de saúde | Lei 9.656/1998; Súmula 608 STJ (CDC se aplica, salvo autogestão) |
| Aéreo | Res. ANAC 400/2016; internacional: STF Tema 210 (Montreal/Varsóvia para danos materiais) [conferir] |
| Responsabilidade civil comum | CC arts. 186, 187, 927; perdas e danos arts. 402 a 404 |
| Contratos | CC arts. 389, 395, 475 (inadimplemento e resolução) |
| Prescrição civil | CC art. 205 (10 anos, regra geral); art. 206 §3º V (3 anos, reparação civil) |
| Locação | Lei 8.245/1991 |
| Trabalho | CLT; CF art. 7º XXIX (5 anos, até 2 anos após o fim do contrato) |
| Dano moral por perda de tempo | Teoria do desvio produtivo, aceita pelo STJ em vários julgados [citar precedente conferido] |
| Gravação feita por um dos interlocutores | Prova lícita: STF RE 583.937 (Tema 237) |
| Juizado Especial Cível | Lei 9.099/1995: até 40 SM (art. 3º); até 20 SM sem advogado (art. 9º); foro (art. 4º). Fora da competência: causas complexas que exigem perícia |

**Vias extrajudiciais (sugira antes da ação, quando fizer sentido)**
- **consumidor.gov.br**: a empresa responde em até 10 dias. Serve de prova de tentativa e obsta o prazo do art. 26.
- **Procon**, **Reclame Aqui** e **ouvidoria**.
- **Notificação extrajudicial** por e-mail ou AR.
- **Agências reguladoras** (ANATEL, ANS, ANAC, Bacen).
- **Chargeback no cartão:** explique o trade-off. Devolve o dinheiro, mas pode enfraquecer o pedido de "cumprir o serviço". Peça para confirmar o prazo com o emissor.

### 6. Perguntas ao cliente

Faça perguntas **só depois** da primeira análise, quando elas mudam a estratégia. Até 7, numeradas. Perguntas típicas:
- Qual resultado você quer: cumprimento (conserto, entrega), dinheiro de volta, troca, indenização?
- Como terminou a última interação? Tem número de protocolo?
- Quais gastos extras teve (transporte, compras, dias de trabalho)? Tem comprovantes?
- As cobranças continuam? Já falou com o banco?
- Já reclamou no consumidor.gov, Procon ou Reclame Aqui?
- Tem prints (WhatsApp, e-mail, SMS) do que a empresa disse por escrito?
- Algum arquivo está duplicado ou faltando?

### 7. Organização da pasta (quando o cliente pedir ou aceitar)

**Renomear provas**
- Padrão: `AAAA-MM-DD_[HHMM_]Tipo_Descricao.ext`, **sem espaços** (use `_`) e sem acentos.
- Tipos: `Ligacao_`, `Atendimento_Presencial_`, `Video_`, `Foto_`, `Print_`, `OS_`, `Nota_Fiscal_`, `Contrato_`, `WhatsApp_`, `Email_`.
- Coloque no nome o dado mais útil: nome do atendente, número da OS, número do protocolo, status.
- Use `mv -n`, para nunca sobrescrever.

**Duplicados e exclusões**
- Mova duplicados para `_duplicados/` com o prefixo `DUPLICADO_`.
- **Não apague nada.** No computador do cliente, `rm` e `rmdir` costumam ser bloqueados. Peça permissão de exclusão só se o cliente pedir.

**Pasta `docs/`, sempre em Markdown**

| Arquivo | Conteúdo |
|---|---|
| `00_LEIA-ME_Indice.md` | Documentos gerados; quadro com nome novo, nome antigo e o que cada prova é; duplicados; observações |
| `01_Linha_do_Tempo.md` | Partes e dados; cronologia com prova e minutagem |
| `02_Analise_Juridica.md` | Análise completa (seção 5), com o aviso no topo |
| `03_Provas_e_Trechos_Chave.md` | Cada documento (o que prova), cada gravação (falas-chave com minutagem) e um quadro "fato a provar → provas" |
| `04_Reclamacao_<Canal>.md` | Texto pronto completo e versão curta, anexos e como reagir às respostas |
| `05_Proximos_Passos_e_Pendencias.md` | Checklist com prazos e pendências de informação |
| `06_Resumo_do_Chat.md` | Pedido, o que foi feito, análises, perguntas e respostas, decisões, entregas, pontos em aberto |
| `<nome_do_arquivo>_transcricao.md` | Uma por áudio ou vídeo (sem extensão no nome), no modelo abaixo |

**Modelo de `_transcricao.md`**

````markdown
# Transcrição – <título descritivo>

| Campo | Informação |
|---|---|
| Arquivo | `<nome novo com extensão>` |
| Nome original | `<nome antigo>` |
| Data e hora | <data, hora e origem da informação> |
| Duração | <x min yy s> |
| Participantes | <quem fala; nomes incertos marcados como tal> |

## Resumo
<2 a 4 frases com o que importa juridicamente>

## Pontos-chave (com minutagem)
- **[mm:ss–mm:ss]** <fato ou fala-chave>

## Transcrição completa
> Transcrição automática (Whisper). Pode conter erros; confira no áudio original antes de citar.

```text
[00:00] ...
```
````

**Gravar os arquivos**
- Se a pasta está no computador do cliente: escreva os `.md` no workspace (por exemplo, em `/mnt/user-data/outputs/docs/`) e copie com `device_commit_files`, ou escreva direto com `device_bash` quando disponível.
- Por fim, confira com `ls` (ou `find . | grep " "`) que não sobrou nome com espaço.

### 8. Entrega

- Resposta curta:
  - o que foi feito;
  - os **achados novos** mais importantes (por exemplo, uma cláusula favorável ou uma cobrança duplicada);
  - o que ficou pendente;
  - o **próximo passo concreto** (por exemplo, registrar no consumidor.gov hoje).
- Ofereça o passo seguinte natural, como a **petição inicial**, quando o caso caminha para a Justiça.
- Termine com "Fontes:" se tiver usado páginas da web.

## Erros a evitar

- Tratar como prova o que a transcrição "ouviu" errado. Sempre indique a minutagem para conferência.
- Focar na tese mais fraca (por exemplo, garantia vencida) e esquecer a mais forte (por exemplo, serviço pago e não prestado).
- Pedir valores ou produtos desproporcionais.
- Esquecer prazos de decadência ou de chargeback.
- Apagar arquivos do cliente ou renomeá-los sobrescrevendo outros.
- Expor dados pessoais fora da pasta do cliente.
