#!/usr/bin/env bash
# Baixa o modelo Whisper "small" (CTranslate2 int8) publicado no npm em 4 partes,
# para ambientes em que o Hugging Face está bloqueado. Uso: ./baixar_modelo_npm.sh DIR_MODELO
set -euo pipefail
DEST="${1:?informe o diretório de destino do modelo}"
TMP="$(mktemp -d)"
mkdir -p "$DEST"
cd "$TMP"
for i in 0 1 2 3; do
  mkdir "p$i"
  (cd "p$i" && npm pack "@skillninja/shortmovie-telop-model-p$i" --silent >/dev/null && tar xzf ./*.tgz)
done
cp p0/package/{config.json,tokenizer.json,vocabulary.json,preprocessor_config.json} "$DEST/"
cat p0/package/model.bin.part0 p1/package/model.bin.part1 p2/package/model.bin.part2 p3/package/model.bin.part3 > "$DEST/model.bin"
EXPECTED="$(cut -d' ' -f1 p0/package/model.sha256)"
ACTUAL="$(sha256sum "$DEST/model.bin" | cut -d' ' -f1)"
if [ "$EXPECTED" != "$ACTUAL" ]; then
  echo "ERRO: sha256 não confere ($ACTUAL != $EXPECTED)" >&2; rm -f "$DEST/model.bin"; exit 1
fi
rm -rf "$TMP"
echo "Modelo pronto em $DEST (sha256 ok)"
