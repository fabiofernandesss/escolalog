import json
import urllib.request
import base64
import logging
import os
from datetime import datetime

# Configurar logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Configurações do Supabase
SUPABASE_URL = "https://sntyndufbxfzasnqvayc.supabase.co"
SUPABASE_API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InNudHluZHVmYnhmemFzbnF2YXljIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTYxNzQ2ODcsImV4cCI6MjA3MTc1MDY4N30.Pv9CaNkpo2HMMAtPbyLz2AdR8ZyK1jtHbP78pR5CPSM"

# Timeouts (podem ser ajustados dinamicamente via payload)
# Recomenda-se configurar o timeout da Lambda >= 20s no AWS
SUPABASE_TIMEOUT = 20.0
DEVICE_LOGIN_TIMEOUT_DEFAULT = 6.0
DEVICE_UPDATE_TIMEOUT_DEFAULT = 12.0
DEVICE_RETRIES_DEFAULT = 3

def safe_int_cast(value, default=0):
    """Converte valor para int de forma segura."""
    try:
        return int(value)
    except (ValueError, TypeError):
        return default

def get_student_by_control_id(control_id):
    """Busca aluno pelo id_control_id."""
    try:
        headers = {
            "apikey": SUPABASE_API_KEY,
            "Authorization": f"Bearer {SUPABASE_API_KEY}",
            "Content-Type": "application/json"
        }
        
        # Buscar aluno pelo id_control_id
        url = f"{SUPABASE_URL}/rest/v1/alunos?select=id,nome,id_control_id,foto_url&id_control_id=eq.{control_id}&soft_delete=eq.false"
        
        req = urllib.request.Request(url=url, method="GET", headers=headers)
        
        with urllib.request.urlopen(req, timeout=SUPABASE_TIMEOUT) as response:
            body = response.read().decode()
            data = json.loads(body)
            
            if isinstance(data, list) and len(data) > 0:
                return data[0]
            return None
            
    except Exception as e:
        logger.error(f'Erro ao buscar aluno: {str(e)}')
        return None

def upload_photo_to_storage(file_data, file_name, content_type):
    """Faz upload da foto para o Supabase Storage."""
    try:
        headers = {
            "apikey": SUPABASE_API_KEY,
            "Authorization": f"Bearer {SUPABASE_API_KEY}",
            "Content-Type": content_type
        }
        
        # Upload para o bucket fotos_alunos
        url = f"{SUPABASE_URL}/storage/v1/object/fotos_alunos/alunos/{file_name}"
        
        req = urllib.request.Request(url=url, data=file_data, method="POST", headers=headers)
        
        with urllib.request.urlopen(req, timeout=SUPABASE_TIMEOUT) as response:
            if response.status in [200, 201]:
                # Retornar URL pública
                public_url = f"{SUPABASE_URL}/storage/v1/object/public/fotos_alunos/alunos/{file_name}"
                return public_url
            else:
                logger.error(f'Erro no upload: status={response.status}')
                return None
                
    except Exception as e:
        logger.error(f'Erro ao fazer upload: {str(e)}')
        return None

def update_student_photo_url(student_id, photo_url):
    """Atualiza a URL da foto do aluno no banco de dados."""
    try:
        headers = {
            "apikey": SUPABASE_API_KEY,
            "Authorization": f"Bearer {SUPABASE_API_KEY}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "foto_url": photo_url
        }
        
        url = f"{SUPABASE_URL}/rest/v1/alunos?id=eq.{student_id}"
        
        req = urllib.request.Request(
            url=url, 
            data=json.dumps(payload).encode('utf-8'), 
            method="PATCH", 
            headers=headers
        )
        
        with urllib.request.urlopen(req, timeout=SUPABASE_TIMEOUT) as response:
            return response.status in [200, 204]
            
    except Exception as e:
        logger.error(f'Erro ao atualizar foto no banco: {str(e)}')
        return False

def get_student_school_id(student_id):
    """Busca o ID da escola do aluno."""
    try:
        headers = {
            "apikey": SUPABASE_API_KEY,
            "Authorization": f"Bearer {SUPABASE_API_KEY}",
            "Content-Type": "application/json"
        }
        
        # Buscar escola do aluno
        url = f"{SUPABASE_URL}/rest/v1/alunos?select=escola_id&id=eq.{student_id}"
        
        req = urllib.request.Request(url=url, method="GET", headers=headers)
        
        with urllib.request.urlopen(req, timeout=SUPABASE_TIMEOUT) as response:
            body = response.read().decode()
            data = json.loads(body)
            
            if isinstance(data, list) and len(data) > 0:
                return data[0].get('escola_id')
            return None
            
    except Exception as e:
        logger.error(f'Erro ao buscar escola do aluno: {str(e)}')
        return None

def get_student_devices(student_id):
    """Busca todos os dispositivos da escola do aluno para sincronização completa."""
    try:
        headers = {
            "apikey": SUPABASE_API_KEY,
            "Authorization": f"Bearer {SUPABASE_API_KEY}",
            "Content-Type": "application/json"
        }
        
        # Primeiro, buscar a escola do aluno
        escola_id = get_student_school_id(student_id)
        if not escola_id:
            logger.error(f'Não foi possível encontrar a escola do aluno {student_id}')
            return []
        
        logger.info(f'Aluno {student_id} pertence à escola {escola_id}')
        
        # Buscar TODOS os dispositivos ATIVOS da escola (não apenas os do aluno específico)
        # Isso garante que a foto seja sincronizada em todos os dispositivos da escola
        url = f"{SUPABASE_URL}/rest/v1/dispositivos?select=id,nome,ip,login,senha,status&escola_id=eq.{escola_id}&status=eq.ATIVO"
        
        req = urllib.request.Request(url=url, method="GET", headers=headers)
        
        with urllib.request.urlopen(req, timeout=SUPABASE_TIMEOUT) as response:
            body = response.read().decode()
            data = json.loads(body)
            
            if isinstance(data, list):
                logger.info(f'🔍 DISPOSITIVOS ENCONTRADOS: {len(data)} dispositivos ATIVOS na escola {escola_id}')
                
                # Log detalhado de cada dispositivo encontrado
                for i, device in enumerate(data, 1):
                    logger.info(f'📱 Dispositivo {i}: {device["nome"]} (ID: {device["id"]}, IP: {device["ip"]})')
                
                # Transformar os dados para manter compatibilidade com o resto do código
                # Cada dispositivo precisa ter um id_do_aluno_no_dispositivo (usaremos o id_control_id do aluno)
                formatted_devices = []
                for device in data:
                    formatted_device = {
                        'id_do_aluno_no_dispositivo': None,  # Será preenchido com id_control_id na função update_devices_photos
                        'dispositivos': device
                    }
                    formatted_devices.append(formatted_device)
                
                logger.info(f'✅ Retornando {len(formatted_devices)} dispositivos formatados para sincronização')
                return formatted_devices
            else:
                logger.warning(f'⚠️ Resposta inesperada da API: {data}')
                return []
            
    except Exception as e:
        logger.error(f'Erro ao buscar dispositivos da escola: {str(e)}')
        return []

def get_device_session(device_ip, login, password, retries=DEVICE_RETRIES_DEFAULT, timeout_seconds=DEVICE_LOGIN_TIMEOUT_DEFAULT):
    """Obtém sessão de autenticação do dispositivo com tentativas.
    Tenta primeiro via JSON (como usado no frontend), depois faz fallback para form-url-encoded.
    """
    ip_with_port = device_ip if ':' in device_ip else f"{device_ip}:80"
    url = f"http://{ip_with_port}/login.fcgi"

    for attempt in range(1, retries + 1):
        # 1) Tentativa com JSON
        try:
            json_body = json.dumps({"login": login, "password": password}).encode('utf-8')
            req_json = urllib.request.Request(
                url=url,
                data=json_body,
                method="POST",
                headers={'Content-Type': 'application/json'}
            )
            with urllib.request.urlopen(req_json, timeout=timeout_seconds) as response:
                body = response.read().decode()
                try:
                    data = json.loads(body)
                    session = data.get('session')
                    if session:
                        logger.info(f'Sessão (JSON) obtida para {device_ip}: {session[:10]}... (tentativa {attempt})')
                        return session
                    else:
                        logger.warning(f'Resposta JSON sem sessão de {device_ip} (tentativa {attempt})')
                except Exception:
                    logger.warning(f'Resposta não-JSON recebida de {device_ip} (tentativa {attempt})')
        except Exception as e:
            logger.warning(f'Erro JSON ao obter sessão de {device_ip} (tentativa {attempt}): {str(e)}')

        # 2) Fallback com form-url-encoded
        try:
            login_data = f"login={login}&password={password}".encode('utf-8')
            req_form = urllib.request.Request(
                url=url,
                data=login_data,
                method="POST",
                headers={'Content-Type': 'application/x-www-form-urlencoded'}
            )
            with urllib.request.urlopen(req_form, timeout=timeout_seconds) as response:
                body = response.read().decode()
                # Alguns firmwares retornam 'session=...' em texto puro
                for line in body.split('\n'):
                    if line.strip().startswith('session='):
                        session = line.split('=', 1)[1].strip()
                        logger.info(f'Sessão (form) obtida para {device_ip}: {session[:10]}... (tentativa {attempt})')
                        return session
                logger.warning(f'Sessão não encontrada na resposta (form) de {device_ip} (tentativa {attempt})')
        except Exception as e:
            logger.warning(f'Erro form ao obter sessão de {device_ip} (tentativa {attempt}): {str(e)}')

    logger.error(f'Falha ao obter sessão de {device_ip} após {retries} tentativas')
    return None

def update_photo_on_device(device_ip, student_device_id, session, photo_data, retries=DEVICE_RETRIES_DEFAULT, timeout_seconds=DEVICE_UPDATE_TIMEOUT_DEFAULT):
    """Atualiza foto no dispositivo de controle de acesso com tentativas."""
    ip_with_port = device_ip if ':' in device_ip else f"{device_ip}:80"
    timestamp = int(datetime.now().timestamp())
    url = f"http://{ip_with_port}/user_set_image.fcgi?user_id={student_device_id}&session={session}&timestamp={timestamp}"
    headers = {
        'Content-Type': 'application/octet-stream',
        'Content-Length': str(len(photo_data))
    }
    
    for attempt in range(1, retries + 1):
        try:
            req = urllib.request.Request(
                url=url,
                data=photo_data,
                method="POST",
                headers=headers
            )
            with urllib.request.urlopen(req, timeout=timeout_seconds) as response:
                if response.status == 200:
                    logger.info(f'Foto atualizada no dispositivo {device_ip} (tentativa {attempt}) para usuário {student_device_id}')
                    return True
                else:
                    logger.warning(f'Status {response.status} ao atualizar foto no dispositivo {device_ip} (tentativa {attempt})')
        except Exception as e:
            logger.warning(f'Erro ao atualizar foto no dispositivo {device_ip} (tentativa {attempt}): {str(e)}')
    
    logger.error(f'Falha ao atualizar foto no dispositivo {device_ip} após {retries} tentativas')
    return False

def update_devices_photos(student_id, photo_data, retries=DEVICE_RETRIES_DEFAULT, login_timeout=DEVICE_LOGIN_TIMEOUT_DEFAULT, update_timeout=DEVICE_UPDATE_TIMEOUT_DEFAULT):
    """Atualiza foto em todos os dispositivos da escola do aluno. Falha se nenhum dispositivo sincronizar."""
    logger.info(f'🚀 INICIANDO SINCRONIZAÇÃO DE FOTO para aluno {student_id}')
    
    devices = get_student_devices(student_id)
    
    if not devices:
        logger.error(f'❌ ERRO: Nenhum dispositivo encontrado para aluno {student_id}')
        return False
    
    logger.info(f'📊 TOTAL DE DISPOSITIVOS PARA SINCRONIZAÇÃO: {len(devices)}')
    
    # Buscar o id_control_id do aluno para usar como student_device_id
    student_data = None
    try:
        headers = {
            "apikey": SUPABASE_API_KEY,
            "Authorization": f"Bearer {SUPABASE_API_KEY}",
            "Content-Type": "application/json"
        }
        
        url = f"{SUPABASE_URL}/rest/v1/alunos?select=id_control_id,nome&id=eq.{student_id}"
        req = urllib.request.Request(url=url, method="GET", headers=headers)
        
        with urllib.request.urlopen(req, timeout=SUPABASE_TIMEOUT) as response:
            body = response.read().decode()
            data = json.loads(body)
            
            if isinstance(data, list) and len(data) > 0:
                student_data = data[0]
    except Exception as e:
        logger.error(f'❌ Erro ao buscar dados do aluno: {str(e)}')
        return False
    
    if not student_data or not student_data.get('id_control_id'):
        logger.error(f'❌ id_control_id não encontrado para aluno {student_id}')
        return False
    
    student_control_id = student_data['id_control_id']
    student_name = student_data.get('nome', 'Nome não encontrado')
    logger.info(f'👤 ALUNO: {student_name} (ID Control: {student_control_id})')
    logger.info(f'🔄 Usando id_control_id {student_control_id} para sincronização em TODOS os dispositivos da escola')
    
    success_count = 0
    failed_count = 0
    total_devices = len(devices)
    
    logger.info(f'🎯 INICIANDO PROCESSO DE SINCRONIZAÇÃO EM {total_devices} DISPOSITIVOS:')
    
    for i, device in enumerate(devices, 1):
        try:
            device_info = device['dispositivos']
            device_ip = device_info['ip'].rstrip('/')
            device_name = device_info['nome']
            device_id = device_info['id']
            
            # Usar id_control_id do aluno como student_device_id para todos os dispositivos da escola
            student_device_id = device.get('id_do_aluno_no_dispositivo') or student_control_id
            
            logger.info(f'📱 [{i}/{total_devices}] PROCESSANDO DISPOSITIVO: {device_name}')
            logger.info(f'   ├─ ID: {device_id}')
            logger.info(f'   ├─ IP: {device_ip}')
            logger.info(f'   ├─ Login: {device_info["login"]}')
            logger.info(f'   └─ Student Device ID: {student_device_id}')
            
            # Obter sessão com retries
            logger.info(f'🔐 Obtendo sessão para {device_name}...')
            session = get_device_session(device_ip, device_info['login'], device_info['senha'], retries=retries, timeout_seconds=login_timeout)
            if not session:
                logger.error(f'❌ [{i}/{total_devices}] FALHA ao obter sessão do dispositivo {device_name} ({device_ip})')
                failed_count += 1
                continue
            
            logger.info(f'✅ Sessão obtida para {device_name}: {session[:10]}...')
            
            # Atualizar foto com retries
            logger.info(f'📸 Atualizando foto no dispositivo {device_name}...')
            if update_photo_on_device(device_ip, student_device_id, session, photo_data, retries=retries, timeout_seconds=update_timeout):
                success_count += 1
                logger.info(f'✅ [{i}/{total_devices}] SUCESSO: Foto atualizada no dispositivo {device_name}')
            else:
                failed_count += 1
                logger.error(f'❌ [{i}/{total_devices}] FALHA: Não foi possível atualizar foto no dispositivo {device_name}')
                
        except Exception as e:
            failed_count += 1
            logger.error(f'❌ [{i}/{total_devices}] ERRO CRÍTICO ao processar dispositivo: {str(e)}')
    
    # Log final detalhado
    logger.info(f'📊 RESULTADO FINAL DA SINCRONIZAÇÃO:')
    logger.info(f'   ├─ Total de dispositivos: {total_devices}')
    logger.info(f'   ├─ Sucessos: {success_count}')
    logger.info(f'   ├─ Falhas: {failed_count}')
    logger.info(f'   └─ Taxa de sucesso: {(success_count/total_devices*100):.1f}%')
    
    if success_count > 0:
        logger.info(f'✅ SINCRONIZAÇÃO CONCLUÍDA: {success_count}/{total_devices} dispositivos atualizados com sucesso')
        return True
    else:
        logger.error(f'❌ SINCRONIZAÇÃO FALHOU: Nenhum dispositivo foi atualizado com sucesso')
        return False

def lambda_handler(event, context):
    """Handler principal da Lambda para edição de fotos."""
    
    # CORS ultra-robusto: configuração específica para escolalog.com.br
    headers_in = event.get('headers') or {}
    # Normalizar headers para case-insensitive
    headers_normalized = {k.lower(): v for k, v in headers_in.items()}
    origin = headers_normalized.get('origin', '')
    
    # Lista de origens permitidas (incluindo variações)
    allowed_origins = [
        'https://www.escolalog.com.br',
        'https://escolalog.com.br',
        'http://localhost:3000',
        'http://127.0.0.1:3000',
        'http://localhost:5500',
        'http://127.0.0.1:5500',
        'http://localhost:8080',
        'http://127.0.0.1:8080'
    ]
    
    # Determinar origem para CORS
    if origin in allowed_origins:
        cors_origin = origin
    elif origin.endswith('.escolalog.com.br'):
        cors_origin = origin
    else:
        cors_origin = '*'
    
    # Headers CORS mais robustos
    requested_headers = headers_normalized.get('access-control-request-headers', 'Content-Type,Authorization,X-Requested-With')
    
    cors_headers = {
        'Access-Control-Allow-Origin': cors_origin,
        'Access-Control-Allow-Headers': f'{requested_headers},Content-Type,Authorization,X-Requested-With,Accept,Origin',
        'Access-Control-Allow-Methods': 'GET,POST,OPTIONS,PUT,DELETE,PATCH',
        'Access-Control-Allow-Credentials': 'true',
        'Access-Control-Max-Age': '86400',
        'Access-Control-Expose-Headers': 'Content-Length,Content-Type',
        'Vary': 'Origin,Access-Control-Request-Headers,Access-Control-Request-Method',
        'Content-Type': 'application/json',
        'Cache-Control': 'no-cache, no-store, must-revalidate'
    }
    
    # Log do evento recebido para debug
    logger.info(f'Evento recebido: {json.dumps(event)}')
    logger.info(f'Headers recebidos: {headers_in}')
    logger.info(f'Origin detectado: {origin}')
    logger.info(f'CORS headers configurados: {cors_headers}')
    
    # Wrapper para garantir CORS em qualquer situação
    def safe_response(status_code, body):
        return {
            'statusCode': status_code,
            'headers': cors_headers,
            'body': json.dumps(body) if isinstance(body, dict) else body
        }
    
    try:
        # Tratar OPTIONS (preflight) - suporte para diferentes formatos de evento
        http_method = (
            event.get('httpMethod') or 
            event.get('requestContext', {}).get('http', {}).get('method') or
            event.get('requestContext', {}).get('httpMethod') or
            'POST'  # Default para POST se não detectado
        )
        logger.info(f'Método HTTP detectado: {http_method}')
        logger.info(f'Event keys: {list(event.keys())}')
        logger.info(f'RequestContext: {event.get("requestContext", {})}')
        
        if http_method == 'OPTIONS':
            logger.info('Processando requisição OPTIONS (preflight) - retornando CORS completo')
            return safe_response(204, '')
        
        # Verificar método HTTP (aceitar POST ou qualquer método)
        if http_method and http_method not in ['POST', 'GET']:
            logger.info(f'Método HTTP recebido: {http_method} - processando como POST')
        
        # Continuar processamento independente do método
        
        # Processar dados do corpo da requisição
        body = event.get('body', '')
        logger.info(f'Corpo da requisição recebido (primeiros 200 chars): {str(body)[:200]}...')
        
        if not body:
            logger.error('Corpo da requisição vazio')
            return safe_response(400, {'error': 'Corpo da requisição é obrigatório'})
        
        # Tentar decodificar base64 se necessário
        if event.get('isBase64Encoded', False):
            try:
                logger.info('Decodificando corpo base64...')
                body = base64.b64decode(body).decode('utf-8')
                logger.info('Decodificação base64 bem-sucedida')
            except Exception as e:
                logger.error(f'Erro ao decodificar base64: {str(e)}')
                return safe_response(400, {'error': 'Erro na decodificação base64'})
        
        # Parse JSON
        try:
            logger.info('Fazendo parse do JSON...')
            if isinstance(body, str):
                data = json.loads(body)
            else:
                data = body
            logger.info('Parse JSON bem-sucedido')
        except json.JSONDecodeError as e:
            logger.error(f'Erro ao fazer parse do JSON: {str(e)}')
            logger.error(f'Corpo que causou erro: {body[:500]}...')
            return safe_response(400, {'error': f'JSON inválido: {str(e)}'})
        
        logger.info(f'Dados recebidos - id_control_id: {data.get("id_control_id", "N/A")}, photo_base64 length: {len(data.get("photo_base64", ""))}, sync_only: {data.get("sync_only", False)}')

        # Validar parâmetros obrigatórios
        control_id = data.get('id_control_id')
        photo_base64 = data.get('photo_base64')
        photo_url = data.get('photo_url')  # Nova opção para sync_only
        
        # Log da photo_url ANTES da limpeza
        if photo_url:
            logger.info(f'🔍 PHOTO_URL EXTRAÍDA DO JSON: {repr(photo_url)}')
        
        # Limpar photo_url removendo caracteres especiais que podem causar problemas
        if photo_url:
            original_url = photo_url
            # Limpeza mais robusta: remover backticks, aspas, espaços e caracteres de controle
            photo_url = photo_url.strip()  # Remove espaços das extremidades
            
            # Remover backticks múltiplos
            while '`' in photo_url:
                photo_url = photo_url.replace('`', '')
            
            # Remover aspas múltiplas
            while '"' in photo_url:
                photo_url = photo_url.replace('"', '')
            
            while "'" in photo_url:
                photo_url = photo_url.replace("'", '')
            
            # Remover espaços extras novamente
            photo_url = photo_url.strip()
            
            logger.info(f'🧹 LIMPEZA ROBUSTA DA URL:')
            logger.info(f'   ├─ Original: {repr(original_url)}')
            logger.info(f'   ├─ Tamanho original: {len(original_url)}')
            logger.info(f'   ├─ Limpa: {repr(photo_url)}')
            logger.info(f'   └─ Tamanho limpa: {len(photo_url)}')
        
        sync_only = bool(data.get('sync_only', False))  # Modo apenas sincronização
        file_extension = data.get('file_extension', 'jpg')
        # Permitir controle via payload; padrão True para ambientes administrados
        sync_devices = bool(data.get('sync_devices', True))
        # Ajustes dinâmicos de timeout/retries vindos do payload
        device_retries = int(data.get('device_retries', DEVICE_RETRIES_DEFAULT))
        device_timeout_seconds = data.get('device_timeout_seconds')
        device_login_timeout = float(data.get('device_login_timeout', DEVICE_LOGIN_TIMEOUT_DEFAULT))
        device_update_timeout = float(data.get('device_update_timeout', DEVICE_UPDATE_TIMEOUT_DEFAULT))
        if device_timeout_seconds:
            # Se um timeout geral for informado, usar para ambas etapas
            try:
                device_timeout_seconds = float(device_timeout_seconds)
                device_login_timeout = device_timeout_seconds
                device_update_timeout = device_timeout_seconds
            except Exception:
                logger.warning('Valor inválido para device_timeout_seconds; usando padrões')
        supabase_timeout = float(data.get('supabase_timeout', SUPABASE_TIMEOUT))
        try:
            globals()['SUPABASE_TIMEOUT'] = supabase_timeout
        except Exception:
            logger.warning('Não foi possível ajustar SUPABASE_TIMEOUT dinamicamente')
        logger.info(f'Sincronização com dispositivos (sync_devices): {sync_devices}')
        logger.info(f'Modo sync_only: {sync_only}')
        logger.info(f'Config timeouts: retries={device_retries}, login_timeout={device_login_timeout}s, update_timeout={device_update_timeout}s, supabase_timeout={SUPABASE_TIMEOUT}s')

        # Validar campos obrigatórios
        if not control_id:
            logger.error('Campo id_control_id ausente ou vazio')
            return safe_response(400, {'error': 'id_control_id é obrigatório'})

        # Se for modo sync_only, não precisa de photo_base64, mas precisa de photo_url
        if sync_only:
            if not photo_url:
                logger.error('Campo photo_url ausente para modo sync_only')
                return safe_response(400, {'error': 'photo_url é obrigatório para sync_only'})
        else:
            if not photo_base64:
                logger.error('Campo photo_base64 ausente para modo normal')
                return safe_response(400, {'error': 'photo_base64 é obrigatório'})

        # Buscar aluno pelo id_control_id
        logger.info(f'🔍 Buscando aluno com id_control_id: {control_id}')
        student = get_student_by_control_id(control_id)
        if not student:
            logger.error(f'❌ Aluno não encontrado para id_control_id: {control_id}')
            return safe_response(404, {'error': 'Aluno não encontrado'})
        
        logger.info(f'✅ Aluno encontrado: {student["nome"]} (ID: {student["id"]})')

        # Se for modo sync_only, usar photo_url fornecida e pular upload
        if sync_only:
            logger.info('🔄 MODO SYNC_ONLY ATIVADO - usando photo_url fornecida')
            logger.info(f'📸 Photo URL para sincronização: {photo_url}')
            final_photo_url = photo_url
            photo_data = None  # Não temos dados da imagem em modo sync_only
            
            # Para sync_only, precisamos baixar a imagem da URL para sincronizar com dispositivos
            if sync_devices:
                logger.info('🔄 SINCRONIZAÇÃO COM DISPOSITIVOS HABILITADA')
                try:
                    logger.info(f'📥 Baixando imagem da URL para sincronização: {photo_url}')
                    
                    # Verificar se a URL é válida
                    if not photo_url.startswith(('http://', 'https://')):
                        logger.error(f'❌ URL inválida (não começa com http/https): {photo_url}')
                        photo_data = None
                    else:
                        logger.info(f'🌐 Fazendo requisição HTTP para: {photo_url}')
                        req = urllib.request.Request(photo_url)
                        req.add_header('User-Agent', 'Mozilla/5.0 (compatible; EscolaLog/1.0)')
                        
                        with urllib.request.urlopen(req, timeout=15) as response:
                            logger.info(f'📡 Resposta HTTP recebida: status {response.status}')
                            if response.status == 200:
                                photo_data = response.read()
                                logger.info(f'✅ Imagem baixada com sucesso para sincronização (tamanho: {len(photo_data)} bytes)')
                            else:
                                logger.error(f'❌ Erro HTTP ao baixar imagem: status {response.status}')
                                photo_data = None
                except urllib.error.HTTPError as e:
                    logger.error(f'Erro HTTP ao baixar imagem: {e.code} - {e.reason}')
                    logger.error(f'URL que causou erro: {photo_url}')
                    photo_data = None
                except urllib.error.URLError as e:
                    logger.error(f'Erro de URL ao baixar imagem: {e.reason}')
                    logger.error(f'URL que causou erro: {photo_url}')
                    photo_data = None
                except Exception as e:
                    logger.error(f'Erro inesperado ao baixar imagem para sincronização: {e}')
                    logger.error(f'URL que causou erro: {photo_url}')
                    photo_data = None
        else:
            # Modo normal - decodificar imagem base64
            logger.info('Processando imagem base64...')
            try:
                # Remover prefixo data:image se existir
                if ',' in photo_base64:
                    logger.info('Removendo prefixo data:image da string base64')
                    photo_base64 = photo_base64.split(',')[1]
                
                logger.info(f'Decodificando base64 (tamanho: {len(photo_base64)} chars)')
                photo_data = base64.b64decode(photo_base64)
                logger.info(f'Imagem decodificada com sucesso (tamanho: {len(photo_data)} bytes)')
            except Exception as e:
                logger.error(f'Erro ao decodificar imagem base64: {str(e)}')
                return safe_response(400, {'error': f'Formato de imagem inválido: {str(e)}'})

            # Gerar nome único para o arquivo
            timestamp = int(datetime.now().timestamp())
            file_name = f"aluno_{control_id}_{timestamp}.{file_extension}"
            logger.info(f'Nome do arquivo gerado: {file_name}')

            # Determinar content-type
            content_type_map = {
                'jpg': 'image/jpeg',
                'jpeg': 'image/jpeg',
                'png': 'image/png',
                'gif': 'image/gif'
            }
            content_type = content_type_map.get(file_extension.lower(), 'image/jpeg')
            logger.info(f'Content-type determinado: {content_type}')

            # Upload da foto
            logger.info('Iniciando upload da foto para o storage...')
            final_photo_url = upload_photo_to_storage(photo_data, file_name, content_type)
            if not final_photo_url:
                logger.error('Falha no upload da foto')
                return safe_response(500, {'error': 'Erro ao fazer upload da foto'})
            
            logger.info(f'Upload concluído com sucesso. URL: {final_photo_url}')

            # Atualizar URL no banco de dados (apenas em modo normal)
            logger.info('Atualizando URL da foto no banco de dados...')
            if not update_student_photo_url(student['id'], final_photo_url):
                logger.error('Falha ao atualizar URL da foto no banco')
                return safe_response(500, {'error': 'Erro ao atualizar foto no banco de dados'})
            
            logger.info('URL da foto atualizada no banco com sucesso')

        # Sincronização com dispositivos (se habilitada)
        devices_updated = None
        logger.info(f'🔧 VERIFICANDO SINCRONIZAÇÃO COM DISPOSITIVOS - sync_devices: {sync_devices}')
        
        if sync_devices:
            logger.info(f'📱 SINCRONIZAÇÃO HABILITADA - verificando dados da imagem...')
            logger.info(f'📊 Status dos dados: photo_data disponível: {photo_data is not None}')
            
            if photo_data:
                logger.info(f'✅ Dados da imagem disponíveis ({len(photo_data)} bytes) - iniciando sincronização...')
                logger.info(f'⚙️ Parâmetros: retries={device_retries}, login_timeout={device_login_timeout}s, update_timeout={device_update_timeout}s')
                
                try:
                    devices_updated = update_devices_photos(student['id'], photo_data, retries=device_retries, login_timeout=device_login_timeout, update_timeout=device_update_timeout)
                    if not devices_updated:
                        logger.warning('⚠️ Nenhum dispositivo foi atualizado.')
                    else:
                        logger.info('🎉 Sincronização com dispositivos concluída com sucesso')
                except Exception as e:
                    logger.error(f'❌ Erro durante sincronização com dispositivos: {str(e)}')
                    devices_updated = False
            else:
                logger.warning('⚠️ Sincronização solicitada mas dados da imagem não disponíveis (falha no download)')
                devices_updated = False
        else:
            logger.info('🚫 Sincronização de dispositivos desativada pelo cliente.')

        # Preparar resposta com informações sobre dispositivos
        logger.info('Preparando resposta final...')
        response_data = {
            'success': True,
            'message': 'Sincronização concluída com sucesso' if sync_only else 'Foto atualizada com sucesso',
            'student': {
                'id': student['id'],
                'nome': student['nome'],
                'id_control_id': student['id_control_id'],
                'foto_url': final_photo_url
            },
            'devices_updated': bool(devices_updated) if devices_updated is not None else False,
            'sync_devices': sync_devices,
            'sync_only': sync_only,
            'partial_success': (sync_devices and not devices_updated) if devices_updated is not None else False
        }

        # Ajustar mensagem conforme sincronização
        if sync_devices:
            if devices_updated:
                response_data['message'] += ' e sincronizada com dispositivos'
            else:
                response_data['message'] += ' (dispositivos não sincronizados)'

        logger.info(f'Operação concluída com sucesso. Resposta: {json.dumps(response_data, indent=2)}')
        
        # Sucesso
        return safe_response(200, response_data)
        
    except Exception as e:
        import traceback
        error_traceback = traceback.format_exc()
        logger.error(f'Erro crítico na Lambda: {str(e)}')
        logger.error(f'Traceback completo: {error_traceback}')
        
        # Garantir que sempre temos CORS headers, mesmo em erro crítico
        try:
            error_headers = cors_headers
        except:
            # Fallback se cors_headers não foi definido
            error_headers = {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type,Authorization',
                'Access-Control-Allow-Methods': 'GET,POST,OPTIONS,PUT,DELETE',
                'Access-Control-Allow-Credentials': 'true',
                'Content-Type': 'application/json'
            }
        
        error_response = {
            'error': f'Erro interno: {str(e)}',
            'type': type(e).__name__,
            'traceback': error_traceback.split('\n')[-10:]  # Últimas 10 linhas do traceback
        }
        
        return safe_response(500, error_response)