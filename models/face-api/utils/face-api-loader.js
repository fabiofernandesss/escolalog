/**
 * Face-API.js Model Loader
 * Utilitário para carregar e gerenciar os modelos de reconhecimento facial
 */

class FaceAPILoader {
    constructor() {
        this.modelsLoaded = false;
        this.loadingPromise = null;
        // Usar caminho absoluto para evitar problemas de roteamento
        this.basePath = '/models/face-api/weights/';
    }

    /**
     * Carrega todos os modelos necessários
     * @returns {Promise<boolean>} True se todos os modelos foram carregados
     */
    async loadModels() {
        if (this.modelsLoaded) {
            return true;
        }

        if (this.loadingPromise) {
            return this.loadingPromise;
        }

        this.loadingPromise = this._loadAllModels();
        return this.loadingPromise;
    }

    /**
     * Carrega todos os modelos em paralelo
     * @private
     */
    async _loadAllModels() {
        try {
            console.log('🤖 Carregando modelos de reconhecimento facial...');

            // Carregar modelos em paralelo para melhor performance
            await Promise.all([
                faceapi.nets.tinyFaceDetector.loadFromUri(this.basePath),
                faceapi.nets.faceLandmark68Net.loadFromUri(this.basePath),
                faceapi.nets.faceRecognitionNet.loadFromUri(this.basePath)
            ]);

            this.modelsLoaded = true;
            console.log('✅ Modelos de reconhecimento facial carregados com sucesso!');
            return true;

        } catch (error) {
            console.error('❌ Erro ao carregar modelos:', error);
            throw new Error('Falha ao carregar modelos de reconhecimento facial');
        }
    }

    /**
     * Verifica se os modelos estão carregados
     * @returns {boolean}
     */
    isLoaded() {
        return this.modelsLoaded;
    }

    /**
     * Detecta rostos em uma imagem
     * @param {HTMLImageElement|HTMLCanvasElement} input - Imagem para processar
     * @param {Object} options - Opções de detecção
     * @returns {Promise<Array>} Array de detecções faciais
     */
    async detectFaces(input, options = {}) {
        if (!this.modelsLoaded) {
            await this.loadModels();
        }

        const defaultOptions = {
            inputSize: 224,
            scoreThreshold: 0.5
        };

        const detectionOptions = { ...defaultOptions, ...options };

        try {
            const detections = await faceapi.detectAllFaces(input, new faceapi.TinyFaceDetectorOptions(detectionOptions))
                .withFaceLandmarks()
                .withFaceDescriptors();

            return detections;
        } catch (error) {
            console.error('❌ Erro ao detectar rostos:', error);
            throw error;
        }
    }

    /**
     * Detecta um único rosto em uma imagem
     * @param {HTMLImageElement|HTMLCanvasElement} input - Imagem para processar
     * @param {Object} options - Opções de detecção
     * @returns {Promise<Object|null>} Detecção facial ou null se não encontrado
     */
    async detectSingleFace(input, options = {}) {
        if (!this.modelsLoaded) {
            await this.loadModels();
        }

        const defaultOptions = {
            inputSize: 224,
            scoreThreshold: 0.5
        };

        const detectionOptions = { ...defaultOptions, ...options };

        try {
            const detection = await faceapi.detectSingleFace(input, new faceapi.TinyFaceDetectorOptions(detectionOptions))
                .withFaceLandmarks()
                .withFaceDescriptor();

            return detection;
        } catch (error) {
            console.error('❌ Erro ao detectar rosto único:', error);
            throw error;
        }
    }

    /**
     * Calcula a distância entre dois descritores faciais
     * @param {Float32Array} descriptor1 - Primeiro descritor
     * @param {Float32Array} descriptor2 - Segundo descritor
     * @returns {number} Distância euclidiana
     */
    calculateDistance(descriptor1, descriptor2) {
        if (!descriptor1 || !descriptor2) {
            return Infinity;
        }

        if (descriptor1.length !== descriptor2.length) {
            console.warn('⚠️ Descritores com tamanhos diferentes');
            return Infinity;
        }

        let sum = 0;
        for (let i = 0; i < descriptor1.length; i++) {
            const diff = descriptor1[i] - descriptor2[i];
            sum += diff * diff;
        }

        return Math.sqrt(sum);
    }

    /**
     * Compara dois descritores faciais
     * @param {Float32Array} descriptor1 - Primeiro descritor
     * @param {Float32Array} descriptor2 - Segundo descritor
     * @param {number} threshold - Limite de similaridade (padrão: 0.6)
     * @returns {boolean} True se os rostos são similares
     */
    isSameFace(descriptor1, descriptor2, threshold = 0.6) {
        const distance = this.calculateDistance(descriptor1, descriptor2);
        return distance < threshold;
    }

    /**
     * Valida a qualidade de uma detecção facial
     * @param {Object} detection - Detecção facial
     * @returns {Object} Resultado da validação
     */
    validateFaceQuality(detection) {
        if (!detection) {
            return {
                isValid: false,
                reason: 'Nenhuma face detectada'
            };
        }

        const { detection: faceDetection, landmarks } = detection;
        
        if (!faceDetection || !landmarks) {
            return {
                isValid: false,
                reason: 'Dados de detecção incompletos'
            };
        }

        // Verificar tamanho da face
        const { width, height } = faceDetection.box;
        const minSize = 50; // Tamanho mínimo em pixels
        
        if (width < minSize || height < minSize) {
            return {
                isValid: false,
                reason: 'Face muito pequena'
            };
        }

        // Verificar confiança da detecção
        if (faceDetection.score < 0.5) {
            return {
                isValid: false,
                reason: 'Baixa confiança na detecção'
            };
        }

        // Verificar se os olhos estão visíveis (pontos 36-47)
        const leftEye = landmarks.getLeftEye();
        const rightEye = landmarks.getRightEye();
        
        if (!leftEye || !rightEye || leftEye.length === 0 || rightEye.length === 0) {
            return {
                isValid: false,
                reason: 'Olhos não detectados'
            };
        }

        return {
            isValid: true,
            confidence: faceDetection.score,
            faceSize: { width, height }
        };
    }
}

// Instância global do loader
window.faceAPILoader = new FaceAPILoader();

// Exportar para uso em módulos
if (typeof module !== 'undefined' && module.exports) {
    module.exports = FaceAPILoader;
}
