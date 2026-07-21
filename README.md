# Organizador de fotos

O script `organizar_fotos.py` compara o conteúdo visual das imagens, não apenas
os nomes. Ele preserva a versão de maior resolução de cada grupo e separa as
demais na pasta `repetidas`.

A comparação combina estrutura em tons de cinza, bordas e hashes perceptuais.
Por isso, também consegue reconhecer a mesma fotografia após mudanças de cor,
brilho, contraste, filtros, recompressão ou redimensionamento, mantendo um limite
conservador para não confundir fotos consecutivas com poses diferentes.

## Preparação (somente na primeira vez)

No Ubuntu/Debian:

```bash
sudo apt install python3-pil python3-imagehash
```

Ou, em sistemas que já possuem `pip`:

```bash
python3 -m pip install Pillow ImageHash
```

## Uso

Primeiro, faça apenas uma simulação para conferir os resultados:

```bash
python3 organizar_fotos.py /caminho/para/as/fotos
```

Para realmente separar as duplicatas:

```bash
python3 organizar_fotos.py /caminho/para/as/fotos --aplicar
```

Para separar, renomear como `img (1).jpg`, `img (2).jpg` etc. e criar
`fotos.zip`:

```bash
python3 organizar_fotos.py /caminho/para/as/fotos --aplicar --renomear --zip
```

O script lê JPG, JPEG, PNG, WebP, BMP e TIFF. Ele analisa somente os arquivos
diretamente dentro da pasta informada; portanto, não volta a analisar o conteúdo
da subpasta `repetidas`.

## Converter imagens e vídeos

As conversões preservam os arquivos originais. Os novos arquivos são colocados
na subpasta `convertidos`.

Converter todas as imagens para JPG em alta resolução e qualidade 92:

```bash
python3 organizar_fotos.py /caminho/para/os/arquivos --aplicar --converter-imagens --somente-converter
```

Converter vídeos para MP4/H.264, mantendo a resolução original:

```bash
python3 organizar_fotos.py /caminho/para/os/arquivos --aplicar --converter-videos --somente-converter
```

Converter imagens e vídeos de uma vez:

```bash
python3 organizar_fotos.py /caminho/para/os/arquivos --aplicar --converter-tudo --somente-converter
```

É possível ajustar a qualidade com `--qualidade-jpg 95` e
`--qualidade-video 18`. No vídeo, números CRF menores geram mais qualidade e
arquivos maiores. O padrão 20 oferece alta qualidade com tamanho equilibrado.

Retire `--somente-converter` quando quiser converter e depois também executar a
detecção/separação de duplicatas na pasta original.

A conversão de vídeos requer FFmpeg:

```bash
sudo apt install ffmpeg
```

## Interface para Windows

Execute `interface_windows.py` com Python para abrir a interface gráfica:

```bat
py interface_windows.py
```

### Gerar a versão portable

No computador usado para construir o programa, instale o Python 3 para Windows
e dê duplo clique em `criar_exe_windows.bat`. Na primeira execução, esse arquivo:

1. cria um ambiente de construção isolado;
2. instala Pillow, ImageHash e PyInstaller;
3. baixa o build `essentials` do FFmpeg para Windows;
4. incorpora Python, todas as bibliotecas e o FFmpeg em um único executável.

O resultado será criado em:

```text
dist\OrganizadorFotos.exe
```

O arquivo resultante é portable para Windows 10/11 de 64 bits. Basta copiar
somente `OrganizadorFotos.exe` para o computador de destino e abri-lo; não é
necessário instalar Python, Pillow, ImageHash ou FFmpeg nesse computador.

A construção inicial requer acesso à internet. O executável pode demorar alguns
segundos a mais na primeira abertura, pois aplicativos PyInstaller de arquivo
único extraem seus componentes para uma pasta temporária durante a execução.
