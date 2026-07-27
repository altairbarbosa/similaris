<p align="center">
  <img src="assets/similaris-icon.png" alt="Similaris logo" width="128">
</p>

# Similaris

Windows x64 builds are published on the
[GitHub Releases page](https://github.com/altairbarbosa/similaris/releases).

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
- Enhance and upscale photos or illustrations by 2x, 3x, or 4x locally with Real-ESRGAN.
- Convert videos to MP4/H.264 while preserving their original resolution.
- Rename images as `img (N)`.
- Graphical interface in English, Brazilian Portuguese, and Spanish.
- Conservative, balanced, and sensitive duplicate-detection profiles.
- Fast candidate filtering followed by bidirectional ORB matching, MAGSAC alignment,
  transform validation, and structural comparison.
- Native WinUI 3 interface for Windows 10/11.

Supported images: JPG, JPEG, PNG, WebP, BMP, and TIFF. Similaris analyzes only
files directly inside the selected folder and does not recursively inspect the
`duplicates` folder.

## Graphical interface

Run the WinUI 3 interface from source:

```powershell
dotnet run --project .\src\Similaris.WinUI\Similaris.WinUI.csproj -c Debug
```

The interface detects the system language automatically. The adaptive side
navigation provides Organize, Convert, Enhance, and Settings. Language,
appearance, support, and license notices are available in Settings. Appearance
defaults to the operating system theme and can be fixed to Light or Dark.
The **Support** tab explains how contributions help the project and opens the
configured PayPal donation page in the default browser.

The **Images** section contains duplicate detection, renaming, and detection
sensitivity. Its organization mode only controls destructive image
actions: simulation reports what would be separated or renamed, while apply
performs those changes. If apply is selected immediately afterward, Similaris
reuses the validated simulation while the files remain unchanged. It also writes
`duplicates/report.txt`, mapping each separated copy to the retained image and
their resolutions. The **Convert** section groups photo and video conversion in
separate tabs; conversions always preserve originals. The **Image enhancement** section creates PNG files in
`enhanced` and preserves the originals. A Vulkan-compatible GPU is recommended.
Video conversion does not compare videos.

Each operational section accepts either an entire source folder or explicitly
selected files and has its own output destination. Image comparison requires at
least two selected images. Explicit selection processes only those files.

## Command-line usage

Install the Python dependencies first:

```bash
python3 -m pip install -r requirements.txt
```

Preview duplicate detection without modifying files:

```bash
python3 photo_organizer.py /path/to/photos
```

Move duplicates and rename the remaining images:

```bash
python3 photo_organizer.py /path/to/photos --apply --rename
```

Convert images and videos while preserving the originals:

```bash
python3 photo_organizer.py /path/to/files --convert-all --convert-only
```

Enhance all supported images locally at 2x:

```bash
python3 photo_organizer.py /path/to/images --enhance-images --enhance-only --enhancement-scale 2
```

Use `--jpg-quality 95` to control JPG quality and `--video-quality 18` to
control the H.264 CRF. Lower CRF values produce higher-quality, larger videos.
The default value is 20.

Run `python3 photo_organizer.py --help` for every available option. Legacy
Portuguese option names remain supported for compatibility.

## Build for Windows

On the Windows build computer, install 64-bit Python 3, the .NET SDK, and the
Windows App SDK tooling. Then run:

```powershell
.\build_winui3.ps1 -Configuration Release
```

The script builds the Python core with PyInstaller and publishes the WinUI 3 application for Windows x64. The initial build requires internet access.

See [docs/winui3-migration.md](docs/winui3-migration.md) for the architecture and
build commands.

### Microsoft Store package

Create the x64 MSIX package from PowerShell on a computer with the Windows
10/11 SDK installed:

```powershell
.\build_winui3.ps1 -Configuration Release -Package
```

Package identity values are configured in
`src\Similaris.WinUI\Package.appxmanifest`. The Store signs the package after
certification. Increase the four-part version for every submission; do not
reuse a version already submitted.

The video tab is conversion-only. Similaris currently does not detect duplicate
videos; it creates MP4/H.264/AAC copies in `converted` and preserves originals.

## Third-party software

License notices are available in [THIRD_PARTY_NOTICES.txt](THIRD_PARTY_NOTICES.txt).

## License

Similaris source code is available under the [MIT License](LICENSE). You may
use, copy, modify, merge, publish, distribute, sublicense, and sell copies as
long as the copyright and license notices are preserved. The software is
provided without warranty. Bundled third-party components retain their own
licenses.

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
- Melhora e amplia fotos ou ilustrações em 2x, 3x ou 4x localmente com Real-ESRGAN.
- Converte vídeos para MP4/H.264 preservando a resolução original.
- Renomeia imagens como `img (N)`.
- Interface gráfica em inglês, português brasileiro e espanhol.
- Perfis de detecção conservador, equilibrado e sensível.
- Filtragem rápida de candidatos seguida de correspondência ORB bidirecional,
  alinhamento MAGSAC, validação da transformação e comparação estrutural.
- Interface nativa WinUI 3 para Windows 10/11.

São compatíveis imagens JPG, JPEG, PNG, WebP, BMP e TIFF. O Similaris analisa
somente os arquivos diretamente dentro da pasta selecionada e não examina
recursivamente a pasta `duplicates`.

### Interface gráfica

```powershell
dotnet run --project .\src\Similaris.WinUI\Similaris.WinUI.csproj -c Debug
```

A interface detecta automaticamente o idioma do sistema. A navegação lateral
adaptativa oferece Organizar, Converter, Aprimorar e Configurações. Idioma,
aparência, apoio e avisos de licença ficam em Configurações. Por padrão, a
aparência acompanha o sistema operacional e pode ser fixada em Claro ou Escuro.
A guia **Apoie** explica como as contribuições ajudam o projeto e abre a página
configurada de doação do PayPal no navegador padrão.

A seção **Imagens** contém detecção de duplicatas, renomeação e sensibilidade.
Seu modo de organização controla somente ações que alteram
imagens: a simulação informa o que seria separado ou renomeado, enquanto aplicar
realiza essas mudanças. Ao aplicar logo depois, o Similaris reutiliza a simulação
validada enquanto os arquivos permanecerem inalterados. Também gera o arquivo
`duplicates/report.txt`, relacionando cada cópia separada à imagem mantida e às
respectivas resoluções. A seção **Converter** agrupa as conversões de fotos e
vídeos em abas e sempre preserva os originais. A seção **Melhoria de imagens**
cria arquivos PNG em `enhanced`, preserva os originais e recomenda uma GPU
compatível com Vulkan. A conversão de vídeos não compara vídeos.

Cada seção operacional aceita uma pasta de origem inteira ou arquivos escolhidos
individualmente e mantém seu próprio destino. A comparação exige pelo menos duas
imagens selecionadas. Na seleção explícita, somente esses arquivos são processados.

### Uso pelo terminal

Instale as dependências e simule a detecção sem alterar arquivos:

```bash
python3 -m pip install -r requirements.txt
python3 photo_organizer.py /caminho/para/as/fotos
```

Mover duplicatas e renomear as imagens restantes:

```bash
python3 photo_organizer.py /caminho/para/as/fotos --apply --rename
```

Converter imagens e vídeos preservando os originais:

```bash
python3 photo_organizer.py /caminho/para/os/arquivos --convert-all --convert-only
```

Melhorar localmente todas as imagens compatíveis em 2x:

```bash
python3 photo_organizer.py /caminho/para/as/imagens --enhance-images --enhance-only --enhancement-scale 2
```

Use `--jpg-quality 95` para controlar a qualidade do JPG e
`--video-quality 18` para controlar o CRF do H.264. Valores CRF menores geram
vídeos de maior qualidade e tamanho; o padrão é 20. Execute
`python3 photo_organizer.py --help` para consultar todas as opções. Os nomes
antigos das opções em português continuam disponíveis por compatibilidade.

### Construção para Windows

No Windows, instale o Python 3 de 64 bits, o .NET SDK e as ferramentas do
Windows App SDK. Depois execute:

```powershell
.\build_winui3.ps1 -Configuration Release
```

O script gera o core Python com PyInstaller e publica a aplicação WinUI 3 para Windows x64. A primeira construção requer acesso à internet para baixar FFmpeg e Real-ESRGAN.

#### Pacote para a Microsoft Store

Crie o pacote MSIX x64 no PowerShell de um computador com o Windows 10/11 SDK
instalado:

```powershell
.\build_winui3.ps1 -Configuration Release -Package
```

Os dados de identidade do pacote são configurados em
`src\Similaris.WinUI\Package.appxmanifest`. A Store assina o pacote após a
certificação. A versão de quatro partes deve ser aumentada a cada envio.

A aba de vídeos serve somente para conversão. Atualmente, o Similaris não
detecta vídeos duplicados; ele cria cópias MP4/H.264/AAC em `converted` e
preserva os originais.

Os avisos de licença estão em [THIRD_PARTY_NOTICES.txt](THIRD_PARTY_NOTICES.txt).

### Licença

O código-fonte do Similaris está disponível sob a [Licença MIT](LICENSE). É
permitido usar, copiar, modificar, mesclar, publicar, distribuir, sublicenciar e
vender cópias, desde que os avisos de copyright e licença sejam preservados. O
software é fornecido sem garantia. Os componentes de terceiros mantêm suas
próprias licenças.

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
- Mejora y amplía fotos o ilustraciones en 2x, 3x o 4x localmente con Real-ESRGAN.
- Convierte vídeos a MP4/H.264 conservando la resolución original.
- Renombra imágenes como `img (N)`.
- Interfaz gráfica en inglés, portugués de Brasil y español.
- Perfiles de detección conservador, equilibrado y sensible.
- Filtrado rápido de candidatos seguido de correspondencia ORB bidireccional,
  alineación MAGSAC, validación de la transformación y comparación estructural.
- Interfaz nativa WinUI 3 para Windows 10/11.

Son compatibles las imágenes JPG, JPEG, PNG, WebP, BMP y TIFF. Similaris
analiza solo los archivos que están directamente en la carpeta seleccionada y
no examina de forma recursiva la carpeta `duplicates`.

### Interfaz gráfica

```powershell
dotnet run --project .\src\Similaris.WinUI\Similaris.WinUI.csproj -c Debug
```

La interfaz detecta automáticamente el idioma del sistema. La navegación lateral
adaptable ofrece Organizar, Convertir, Mejorar y Configuración. El idioma, la
apariencia, el apoyo y los avisos de licencia se administran desde
Configuración. La apariencia sigue el sistema operativo de forma predeterminada
y se puede fijar en Claro u Oscuro.
La pestaña **Apoyar** explica cómo ayudan las contribuciones al proyecto y abre
la página configurada de donación de PayPal en el navegador predeterminado.

La sección **Imágenes** contiene detección de duplicados, renombrado y
sensibilidad. Su modo de organización controla únicamente las
acciones que modifican imágenes: la simulación informa qué se separaría o
renombraría, mientras que aplicar realiza esos cambios.
Al aplicar inmediatamente después, Similaris reutiliza la simulación validada
mientras los archivos no hayan cambiado. También crea `duplicates/report.txt`,
que relaciona cada copia separada con la imagen conservada y sus resoluciones.
La sección **Convertir** agrupa fotos y vídeos en pestañas y siempre conserva los
originales. La sección **Mejora de imágenes** crea archivos PNG en `enhanced`, conserva los
originales y recomienda una GPU compatible con Vulkan. La conversión de vídeos
no compara vídeos.

Cada sección operativa acepta una carpeta de origen completa o archivos elegidos
individualmente y mantiene su propio destino. La comparación requiere al menos
dos imágenes seleccionadas. La selección explícita procesa solo esos archivos.

### Uso desde la terminal

Instale las dependencias y simule la detección sin modificar archivos:

```bash
python3 -m pip install -r requirements.txt
python3 photo_organizer.py /ruta/a/las/fotos
```

Mover duplicados y renombrar las imágenes restantes:

```bash
python3 photo_organizer.py /ruta/a/las/fotos --apply --rename
```

Convertir imágenes y vídeos conservando los originales:

```bash
python3 photo_organizer.py /ruta/a/los/archivos --convert-all --convert-only
```

Mejorar localmente todas las imágenes compatibles en 2x:

```bash
python3 photo_organizer.py /ruta/a/las/imágenes --enhance-images --enhance-only --enhancement-scale 2
```

Use `--jpg-quality 95` para controlar la calidad del JPG y
`--video-quality 18` para controlar el CRF de H.264. Los valores CRF más bajos
producen vídeos de mayor calidad y tamaño; el valor predeterminado es 20.
Ejecute `python3 photo_organizer.py --help` para consultar todas las opciones.
Los nombres antiguos de las opciones en portugués siguen disponibles por
compatibilidad.

### Construcción para Windows

En Windows, instale Python 3 de 64 bits, el .NET SDK y las herramientas de
Windows App SDK. Luego ejecute:

```powershell
.\build_winui3.ps1 -Configuration Release
```

El script genera el core Python con PyInstaller y publica la aplicación WinUI 3 para Windows x64. La primera construcción requiere acceso a Internet para descargar FFmpeg y Real-ESRGAN.

#### Paquete para Microsoft Store

Cree el paquete MSIX x64 desde PowerShell en un equipo con Windows 10/11 SDK
instalado:

```powershell
.\build_winui3.ps1 -Configuration Release -Package
```

Los datos de identidad del paquete se configuran en
`src\Similaris.WinUI\Package.appxmanifest`. La Store firma el paquete después
de la certificación. La versión de cuatro partes debe aumentar con cada envío.

La pestaña de vídeos sirve únicamente para conversión. Similaris no detecta
actualmente vídeos duplicados; crea copias MP4/H.264/AAC en `converted` y
conserva los originales.

Los avisos de licencia están en [THIRD_PARTY_NOTICES.txt](THIRD_PARTY_NOTICES.txt).

### Licencia

El código fuente de Similaris está disponible bajo la [Licencia MIT](LICENSE).
Se permite usar, copiar, modificar, fusionar, publicar, distribuir, sublicenciar
y vender copias siempre que se conserven los avisos de copyright y licencia. El
software se proporciona sin garantía. Los componentes de terceros conservan
sus propias licencias.
