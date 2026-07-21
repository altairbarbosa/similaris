<p align="center">
  <img src="assets/similaris-icon.png" alt="Similaris logo" width="128">
</p>

# Similaris

[English](#english) | [Português (Brasil)](#português-brasil) | [Español](#español)

---

## English

Similaris finds visually similar photos, keeps the highest-resolution version,
and moves the remaining copies to the `duplicates` folder. It compares image
content rather than filenames by combining grayscale structure, edges, and
perceptual hashes.

It can recognize the same photo after color, brightness, contrast, filtering,
recompression, or resizing changes, while using conservative thresholds to
avoid grouping consecutive photos with different poses.

## Features

- Find and separate visually duplicate images.
- Keep the copy with the highest resolution.
- Convert images to high-quality JPG without changing their resolution.
- Convert videos to MP4/H.264 while preserving their original resolution.
- Rename images as `img (N)` and create `photos.zip`.
- Graphical interface in English, Brazilian Portuguese, and Spanish.
- Portable single-file builds for Windows and Linux/WSL.

Supported images: JPG, JPEG, PNG, WebP, BMP, and TIFF. Similaris analyzes only
files directly inside the selected folder and does not recursively inspect the
`duplicates` folder.

## Graphical interface

Run from source:

```bash
python3 app.py
```

The interface detects the system language automatically. You can switch the
language at any time using the selector in the upper-right corner.

## Command-line usage

Install the Python dependencies first:

```bash
python3 -m pip install -r requirements.txt
```

Preview duplicate detection without modifying files:

```bash
python3 photo_organizer.py /path/to/photos
```

Move duplicates, rename the remaining images, and create a ZIP:

```bash
python3 photo_organizer.py /path/to/photos --apply --rename --zip
```

Convert images and videos while preserving the originals:

```bash
python3 photo_organizer.py /path/to/files --apply --convert-all --convert-only
```

Use `--jpg-quality 95` to control JPG quality and `--video-quality 18` to
control the H.264 CRF. Lower CRF values produce higher-quality, larger videos.
The default value is 20.

Run `python3 photo_organizer.py --help` for every available option. Legacy
Portuguese option names remain supported for compatibility.

## Build for Windows

On the Windows build computer, install 64-bit Python 3 and run:

```bat
build_windows.bat
```

The script creates an isolated environment, installs the dependencies,
downloads and verifies FFmpeg, and packages everything into:

```text
dist\Similaris.exe
```

The resulting file is portable on 64-bit Windows 10/11. The destination
computer does not need Python, Pillow, ImageHash, NumPy, or FFmpeg installed.
The initial build requires internet access.

## Build for Linux/WSL

On Ubuntu or WSL, install the build requirements once:

```bash
sudo apt update
sudo apt install -y python3-tk python3-venv
```

Build and run:

```bash
./build_linux.sh
./dist/Similaris
```

The script downloads and verifies a static FFmpeg build and packages Python,
Tkinter, Pillow, ImageHash, NumPy, and FFmpeg into one executable. On Windows 11
with WSL, the graphical window is displayed through WSLg.

Linux builds target the architecture and glibc compatibility of the build
environment. Use `build_windows.bat` to create the native Windows executable.

## Third-party software

License notices are available in [THIRD_PARTY_NOTICES.txt](THIRD_PARTY_NOTICES.txt).

---

## Português (Brasil)

O Similaris encontra fotos visualmente semelhantes, preserva a versão de maior
resolução e move as demais cópias para a pasta `duplicates`. A comparação usa o
conteúdo das imagens, e não seus nomes, combinando estrutura em tons de cinza,
bordas e hashes perceptuais.

Ele reconhece a mesma fotografia após alterações de cor, brilho, contraste,
filtros, recompressão ou redimensionamento, mantendo limites conservadores para
não agrupar fotos consecutivas com poses diferentes.

### Recursos

- Detecta e separa imagens visualmente duplicadas.
- Preserva a cópia com maior resolução.
- Converte imagens para JPG de alta qualidade sem alterar a resolução.
- Converte vídeos para MP4/H.264 preservando a resolução original.
- Renomeia imagens como `img (N)` e cria `photos.zip`.
- Interface gráfica em inglês, português brasileiro e espanhol.
- Builds portáteis de arquivo único para Windows e Linux/WSL.

São compatíveis imagens JPG, JPEG, PNG, WebP, BMP e TIFF. O Similaris analisa
somente os arquivos diretamente dentro da pasta selecionada e não examina
recursivamente a pasta `duplicates`.

### Interface gráfica

```bash
python3 app.py
```

A interface detecta automaticamente o idioma do sistema. O idioma pode ser
alterado a qualquer momento pelo seletor no canto superior direito.

### Uso pelo terminal

Instale as dependências e simule a detecção sem alterar arquivos:

```bash
python3 -m pip install -r requirements.txt
python3 photo_organizer.py /caminho/para/as/fotos
```

Mover duplicatas, renomear as imagens restantes e criar um ZIP:

```bash
python3 photo_organizer.py /caminho/para/as/fotos --apply --rename --zip
```

Converter imagens e vídeos preservando os originais:

```bash
python3 photo_organizer.py /caminho/para/os/arquivos --apply --convert-all --convert-only
```

Use `--jpg-quality 95` para controlar a qualidade do JPG e
`--video-quality 18` para controlar o CRF do H.264. Valores CRF menores geram
vídeos de maior qualidade e tamanho; o padrão é 20. Execute
`python3 photo_organizer.py --help` para consultar todas as opções. Os nomes
antigos das opções em português continuam disponíveis por compatibilidade.

### Construção para Windows

No Windows, instale o Python 3 de 64 bits e execute:

```bat
build_windows.bat
```

O script cria um ambiente isolado, instala as dependências, baixa e valida o
FFmpeg e gera `dist\Similaris.exe`. Esse arquivo é portátil para Windows 10/11
de 64 bits; o computador de destino não precisa ter Python, Pillow, ImageHash,
NumPy ou FFmpeg. A primeira construção requer acesso à internet.

### Construção para Linux/WSL

```bash
sudo apt update
sudo apt install -y python3-tk python3-venv
./build_linux.sh
./dist/Similaris
```

O script baixa e valida um FFmpeg estático e incorpora Python, Tkinter, Pillow,
ImageHash, NumPy e FFmpeg em um único executável. No Windows 11 com WSL, a
janela gráfica é exibida pelo WSLg. O build depende da arquitetura e da
compatibilidade da glibc do ambiente usado na construção.

Os avisos de licença estão em [THIRD_PARTY_NOTICES.txt](THIRD_PARTY_NOTICES.txt).

---

## Español

Similaris encuentra fotos visualmente similares, conserva la versión de mayor
resolución y mueve las demás copias a la carpeta `duplicates`. La comparación
utiliza el contenido de las imágenes, no sus nombres, combinando la estructura
en escala de grises, los bordes y hashes perceptuales.

Puede reconocer una misma fotografía después de cambios de color, brillo,
contraste, filtros, recompresión o tamaño, manteniendo límites conservadores
para no agrupar fotos consecutivas con poses diferentes.

### Funciones

- Detecta y separa imágenes visualmente duplicadas.
- Conserva la copia con mayor resolución.
- Convierte imágenes a JPG de alta calidad sin cambiar la resolución.
- Convierte vídeos a MP4/H.264 conservando la resolución original.
- Renombra imágenes como `img (N)` y crea `photos.zip`.
- Interfaz gráfica en inglés, portugués de Brasil y español.
- Builds portátiles de un solo archivo para Windows y Linux/WSL.

Son compatibles las imágenes JPG, JPEG, PNG, WebP, BMP y TIFF. Similaris
analiza solo los archivos que están directamente en la carpeta seleccionada y
no examina de forma recursiva la carpeta `duplicates`.

### Interfaz gráfica

```bash
python3 app.py
```

La interfaz detecta automáticamente el idioma del sistema. Puede cambiarlo en
cualquier momento mediante el selector de la esquina superior derecha.

### Uso desde la terminal

Instale las dependencias y simule la detección sin modificar archivos:

```bash
python3 -m pip install -r requirements.txt
python3 photo_organizer.py /ruta/a/las/fotos
```

Mover duplicados, renombrar las imágenes restantes y crear un ZIP:

```bash
python3 photo_organizer.py /ruta/a/las/fotos --apply --rename --zip
```

Convertir imágenes y vídeos conservando los originales:

```bash
python3 photo_organizer.py /ruta/a/los/archivos --apply --convert-all --convert-only
```

Use `--jpg-quality 95` para controlar la calidad del JPG y
`--video-quality 18` para controlar el CRF de H.264. Los valores CRF más bajos
producen vídeos de mayor calidad y tamaño; el valor predeterminado es 20.
Ejecute `python3 photo_organizer.py --help` para consultar todas las opciones.
Los nombres antiguos de las opciones en portugués siguen disponibles por
compatibilidad.

### Construcción para Windows

En Windows, instale Python 3 de 64 bits y ejecute:

```bat
build_windows.bat
```

El script crea un entorno aislado, instala las dependencias, descarga y verifica
FFmpeg y genera `dist\Similaris.exe`. Este archivo es portátil para Windows
10/11 de 64 bits; el equipo de destino no necesita Python, Pillow, ImageHash,
NumPy ni FFmpeg. La primera construcción requiere acceso a Internet.

### Construcción para Linux/WSL

```bash
sudo apt update
sudo apt install -y python3-tk python3-venv
./build_linux.sh
./dist/Similaris
```

El script descarga y verifica un FFmpeg estático e incorpora Python, Tkinter,
Pillow, ImageHash, NumPy y FFmpeg en un solo ejecutable. En Windows 11 con WSL,
la ventana gráfica se muestra mediante WSLg. El build depende de la arquitectura
y de la compatibilidad de glibc del entorno utilizado para construirlo.

Los avisos de licencia están en [THIRD_PARTY_NOTICES.txt](THIRD_PARTY_NOTICES.txt).
