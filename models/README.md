# Modelos de Reconhecimento Facial

Esta pasta contém os modelos necessários para o sistema de reconhecimento facial do Escola Log.

## Estrutura

```
models/
├── face-api/
│   ├── weights/          # Pesos dos modelos (arquivos .bin)
│   ├── utils/            # Utilitários e helpers
│   └── README.md         # Documentação específica do face-api
└── README.md             # Este arquivo
```

## Modelos Necessários

### Face-API.js
Para funcionar corretamente, precisamos dos seguintes arquivos na pasta `weights/`:

1. **face_detection_model** - Para detectar rostos
   - `tiny_face_detector_model-weights_manifest.json`
   - `tiny_face_detector_model-shard1`

2. **face_landmark_model** - Para detectar pontos faciais
   - `face_landmark_68_model-weights_manifest.json`
   - `face_landmark_68_model-shard1`

3. **face_recognition_model** - Para reconhecimento facial
   - `face_recognition_model-weights_manifest.json`
   - `face_recognition_model-shard1`
   - `face_recognition_model-shard2`

## Como Baixar os Modelos

Os modelos podem ser baixados do repositório oficial do face-api.js:
https://github.com/justadudewhohacks/face-api.js/tree/master/weights

## Uso

Os modelos são carregados automaticamente pelo sistema quando necessário.
A pasta `utils/` contém funções auxiliares para:
- Carregamento dos modelos
- Processamento de imagens
- Comparação de descritores faciais
- Validação de qualidade das fotos

## Segurança

- Os modelos são executados localmente no navegador
- Nenhuma imagem é enviada para servidores externos
- Apenas os descritores faciais (vetores numéricos) são armazenados no banco de dados
- Total conformidade com LGPD
