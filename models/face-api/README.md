# Face-API.js - Modelos e Utilitários

Esta pasta contém os modelos e utilitários para o sistema de reconhecimento facial baseado em face-api.js.

## Arquivos Necessários

### Pasta `weights/`
Contém os arquivos de pesos dos modelos:

1. **Tiny Face Detector** (Detecção de rostos)
   - `tiny_face_detector_model-weights_manifest.json`
   - `tiny_face_detector_model-shard1`

2. **Face Landmark 68** (Pontos faciais)
   - `face_landmark_68_model-weights_manifest.json`
   - `face_landmark_68_model-shard1`

3. **Face Recognition** (Reconhecimento)
   - `face_recognition_model-weights_manifest.json`
   - `face_recognition_model-shard1`
   - `face_recognition_model-shard2`

### Pasta `utils/`
Contém utilitários JavaScript para:
- Carregamento dos modelos
- Processamento de imagens
- Validação de qualidade
- Comparação de descritores

## Como Baixar os Modelos

1. Acesse: https://github.com/justadudewhohacks/face-api.js/tree/master/weights
2. Baixe os arquivos listados acima
3. Coloque-os na pasta `weights/`

## Configuração

Os modelos são carregados automaticamente quando o sistema é inicializado.
O caminho base é configurado para apontar para esta pasta.

## Performance

- **Tiny Face Detector**: Mais rápido, menor precisão
- **SSD MobileNet**: Mais lento, maior precisão
- **MTCNN**: Melhor precisão, mais lento

Para o ambiente escolar, recomendamos o Tiny Face Detector por ser mais rápido e suficiente para a precisão necessária.
