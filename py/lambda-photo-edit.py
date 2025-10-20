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
# Recomenda-se configurar o timeout da Lambda >= 60s no AWS para múltiplos dispositivos
SUPABASE_TIMEOUT = 30.0
DEVICE_LOGIN_TIMEOUT_DEFAULT = 10.0
DEVICE_UPDATE_TIMEOUT_DEFAULT = 20.0
DEVICE_RETRIES_DEFAULT = 2

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
        
        # Upload para o bucket fotos (corrigido para usar o bucket correto)
        url = f"{SUPABASE_URL}/storage/v1/object/fotos/{file_name}"
        
        req = urllib.request.Request(url=url, data=file_data, method="POST", headers=headers)
        
        with urllib.request.urlopen(req, timeout=SUPABASE_TIMEOUT) as response:
            if response.status in [200, 201]:
                # Retornar URL pública
                public_url = f"{SUPABASE_URL}/storage/v1/object/public/fotos/{file_name}"
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

def get_student_devices(student_id, device_id=None):
    """Busca dispositivos da escola do aluno. Se device_id for especificado, retorna apenas esse dispositivo."""
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
        
        # Construir query baseada se device_id foi especificado
        if device_id:
            # Buscar apenas o dispositivo específico
            url = f"{SUPABASE_URL}/rest/v1/dispositivos?select=id,nome,ip,login,senha,status&escola_id=eq.{escola_id}&id=eq.{device_id}&status=eq.ATIVO"
            logger.info(f'🎯 BUSCANDO DISPOSITIVO ESPECÍFICO: ID {device_id} na escola {escola_id}')
        else:
            # Buscar TODOS os dispositivos ATIVOS da escola
            url = f"{SUPABASE_URL}/rest/v1/dispositivos?select=id,nome,ip,login,senha,status&escola_id=eq.{escola_id}&status=eq.ATIVO"
            logger.info(f'🔍 BUSCANDO TODOS OS DISPOSITIVOS na escola {escola_id}')
        
        req = urllib.request.Request(url=url, method="GET", headers=headers)
        
        with urllib.request.urlopen(req, timeout=SUPABASE_TIMEOUT) as response:
            body = response.read().decode()
            data = json.loads(body)
            
            if isinstance(data, list):
                if device_id:
                    logger.info(f'🔍 DISPOSITIVO ESPECÍFICO: {len(data)} dispositivo(s) encontrado(s)')
                else:
                    logger.info(f'🔍 DISPOSITIVOS ENCONTRADOS: {len(data)} dispositivos ATIVOS na escola {escola_id}')
                
                # Log detalhado de cada dispositivo encontrado
                for i, device in enumerate(data, 1):
                    logger.info(f'📱 Dispositivo {i}: {device["nome"]} (ID: {device["id"]}, IP: {device["ip"]})')
                
                # Transformar os dados para manter compatibilidade com o resto do código
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

def list_student_devices(student_id):
    """Lista todos os dispositivos da escola do aluno para o frontend fazer chamadas individuais."""
    logger.info(f'📋 LISTANDO DISPOSITIVOS para aluno {student_id}')
    
    devices = get_student_devices(student_id)
    
    if not devices:
        logger.error(f'❌ ERRO: Nenhum dispositivo encontrado para aluno {student_id}')
        return []
    
    # Extrair apenas as informações necessárias para o frontend
    device_list = []
    for device in devices:
        device_info = device['dispositivos']
        device_list.append({
            'id': device_info['id'],
            'nome': device_info['nome'],
            'ip': device_info['ip']
        })
    
    logger.info(f'✅ Retornando lista de {len(device_list)} dispositivos')
    return device_list

def update_single_device_photo(student_id, device_id, photo_data, retries=DEVICE_RETRIES_DEFAULT, login_timeout=DEVICE_LOGIN_TIMEOUT_DEFAULT, update_timeout=DEVICE_UPDATE_TIMEOUT_DEFAULT):
    """Atualiza foto em um dispositivo específico."""
    logger.info(f'🚀 INICIANDO SINCRONIZAÇÃO DE FOTO para aluno {student_id} no dispositivo {device_id}')
    
    devices = get_student_devices(student_id, device_id)
    
    if not devices:
        logger.error(f'❌ ERRO: Dispositivo {device_id} não encontrado para aluno {student_id}')
        return False
    
    if len(devices) != 1:
        logger.error(f'❌ ERRO: Esperado 1 dispositivo, encontrados {len(devices)}')
        return False
    
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
    
    device = devices[0]
    device_info = device['dispositivos']
    device_ip = device_info['ip'].rstrip('/')
    device_name = device_info['nome']
    
    # Usar id_control_id do aluno como student_device_id
    student_device_id = student_control_id
    
    logger.info(f'📱 PROCESSANDO DISPOSITIVO: {device_name}')
    logger.info(f'   ├─ ID: {device_id}')
    logger.info(f'   ├─ IP: {device_ip}')
    logger.info(f'   ├─ Login: {device_info["login"]}')
    logger.info(f'   └─ Student Device ID: {student_device_id}')
    
    try:
        # Obter sessão com retries
        logger.info(f'🔐 Obtendo sessão para {device_name}...')
        session = get_device_session(device_ip, device_info['login'], device_info['senha'], retries=retries, timeout_seconds=login_timeout)
        if not session:
            logger.error(f'❌ FALHA ao obter sessão do dispositivo {device_name} ({device_ip})')
            return False
        
        logger.info(f'✅ Sessão obtida para {device_name}: {session[:10]}...')
        
        # Atualizar foto com retries
        logger.info(f'📸 Atualizando foto no dispositivo {device_name}...')
        if update_photo_on_device(device_ip, student_device_id, session, photo_data, retries=retries, timeout_seconds=update_timeout):
            logger.info(f'✅ SUCESSO: Foto atualizada no dispositivo {device_name}')
            return True
        else:
            logger.error(f'❌ FALHA: Não foi possível atualizar foto no dispositivo {device_name}')
            return False
            
    except Exception as e:
        logger.error(f'❌ ERRO CRÍTICO ao processar dispositivo: {str(e)}')
        return False

def download_photo(photo_url):
    """Baixa foto da URL fornecida."""
    try:
        logger.info(f'📥 Baixando imagem da URL: {photo_url}')
        
        # Verificar se a URL é válida
        if not photo_url.startswith(('http://', 'https://')):
            logger.error(f'❌ URL inválida (não começa com http/https): {photo_url}')
            return None
        
        logger.info(f'🌐 Fazendo requisição HTTP para: {photo_url}')
        req = urllib.request.Request(photo_url)
        req.add_header('User-Agent', 'Mozilla/5.0 (compatible; EscolaLog/1.0)')
        
        with urllib.request.urlopen(req, timeout=15) as response:
            logger.info(f'📡 Resposta HTTP recebida: status {response.status}')
            if response.status == 200:
                photo_data = response.read()
                logger.info(f'✅ Imagem baixada com sucesso (tamanho: {len(photo_data)} bytes)')
                return photo_data
            else:
                logger.error(f'❌ Erro HTTP ao baixar imagem: status {response.status}')
                return None
                
    except urllib.error.HTTPError as e:
        logger.error(f'Erro HTTP ao baixar imagem: {e.code} - {e.reason}')
        logger.error(f'URL que causou erro: {photo_url}')
        return None
    except urllib.error.URLError as e:
        logger.error(f'Erro de URL ao baixar imagem: {e.reason}')
        logger.error(f'URL que causou erro: {photo_url}')
        return None
    except Exception as e:
        logger.error(f'Erro inesperado ao baixar imagem: {e}')
        logger.error(f'URL que causou erro: {photo_url}')
        return None

def update_devices_photos(student_id, photo_data, retries=DEVICE_RETRIES_DEFAULT, login_timeout=DEVICE_LOGIN_TIMEOUT_DEFAULT, update_timeout=DEVICE_UPDATE_TIMEOUT_DEFAULT):
    """Atualiza foto em todos os dispositivos da escola do aluno."""
    logger.info(f'🚀 INICIANDO SINCRONIZAÇÃO DE FOTOS para aluno {student_id}')
    
    devices = get_student_devices(student_id)
    
    if not devices:
        logger.error(f'❌ ERRO: Nenhum dispositivo encontrado para aluno {student_id}')
        return False
    
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
    
    success_count = 0
    total_devices = len(devices)
    
    logger.info(f'📱 PROCESSANDO {total_devices} DISPOSITIVOS:')
    
    for i, device in enumerate(devices, 1):
        device_info = device['dispositivos']
        device_ip = device_info['ip'].rstrip('/')
        device_name = device_info['nome']
        
        # Usar id_control_id do aluno como student_device_id
        student_device_id = student_control_id
        
        logger.info(f'📱 PROCESSANDO DISPOSITIVO {i}/{total_devices}: {device_name}')
        logger.info(f'   ├─ ID: {device_info["id"]}')
        logger.info(f'   ├─ IP: {device_ip}')
        logger.info(f'   ├─ Login: {device_info["login"]}')
        logger.info(f'   └─ Student Device ID: {student_device_id}')
        
        try:
            # Obter sessão com retries
            logger.info(f'🔐 Obtendo sessão para {device_name}...')
            session = get_device_session(device_ip, device_info['login'], device_info['senha'], retries=retries, timeout_seconds=login_timeout)
            if not session:
                logger.error(f'❌ FALHA ao obter sessão do dispositivo {device_name} ({device_ip})')
                continue
            
            logger.info(f'✅ Sessão obtida para {device_name}: {session[:10]}...')
            
            # Atualizar foto com retries
            logger.info(f'📸 Atualizando foto no dispositivo {device_name}...')
            if update_photo_on_device(device_ip, student_device_id, session, photo_data, retries=retries, timeout_seconds=update_timeout):
                logger.info(f'✅ SUCESSO: Foto atualizada no dispositivo {device_name}')
                success_count += 1
            else:
                logger.error(f'❌ FALHA: Não foi possível atualizar foto no dispositivo {device_name}')
                
        except Exception as e:
            logger.error(f'❌ ERRO CRÍTICO ao processar dispositivo {device_name}: {str(e)}')
            continue
    
    logger.info(f'📊 RESULTADO FINAL: {success_count}/{total_devices} dispositivos atualizados com sucesso')
    
    if success_count > 0:
        logger.info(f'🎉 SINCRONIZAÇÃO CONCLUÍDA: Pelo menos um dispositivo foi atualizado')
        return True
    else:
        logger.error(f'❌ SINCRONIZAÇÃO FALHOU: Nenhum dispositivo foi atualizado')
        return False

def lambda_handler(event, context):
    """Handler principal da Lambda para sincronização de fotos com dispositivos."""
    
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
        
        # Parse do body
        body = json.loads(event.get('body', '{}'))
        
        # Verificar se é uma operação de listagem de dispositivos
        operation = body.get('operation', 'update_photo')
        
        if operation == 'list_devices':
            # Operação para listar dispositivos
            student_id = body.get('student_id')
            
            if not student_id:
                return safe_response(400, {'error': 'student_id é obrigatório para listar dispositivos'})
            
            logger.info(f'📋 LISTANDO DISPOSITIVOS para aluno: {student_id}')
            
            devices = list_student_devices(student_id)
            
            return safe_response(200, {
                'devices': devices,
                'total': len(devices)
            })
            
        elif operation == 'update_single_device':
            # Operação para atualizar um dispositivo específico
            student_id = body.get('student_id')
            device_id = body.get('device_id')
            photo_url = body.get('photo_url')
            
            if not student_id or not device_id or not photo_url:
                return safe_response(400, {'error': 'student_id, device_id e photo_url são obrigatórios'})
            
            # Parâmetros opcionais com valores padrão
            retries = body.get('retries', DEVICE_RETRIES_DEFAULT)
            device_login_timeout = body.get('device_login_timeout', DEVICE_LOGIN_TIMEOUT_DEFAULT)
            device_update_timeout = body.get('device_update_timeout', DEVICE_UPDATE_TIMEOUT_DEFAULT)
            
            logger.info(f'📋 CONFIGURAÇÕES RECEBIDAS PARA DISPOSITIVO ÚNICO:')
            logger.info(f'   ├─ Student ID: {student_id}')
            logger.info(f'   ├─ Device ID: {device_id}')
            logger.info(f'   ├─ Photo URL: {photo_url}')
            logger.info(f'   ├─ Retries: {retries}')
            logger.info(f'   ├─ Device Login Timeout: {device_login_timeout}s')
            logger.info(f'   └─ Device Update Timeout: {device_update_timeout}s')
            
            # Download da foto
            photo_data = download_photo(photo_url)
            if not photo_data:
                return safe_response(400, {'error': 'Não foi possível baixar a foto'})
            
            # Atualizar dispositivo específico
            success = update_single_device_photo(
                student_id=student_id,
                device_id=device_id,
                photo_data=photo_data,
                retries=retries,
                login_timeout=device_login_timeout,
                update_timeout=device_update_timeout
            )
            
            if success:
                return safe_response(200, {'message': f'Foto atualizada com sucesso no dispositivo {device_id}'})
            else:
                return safe_response(500, {'error': f'Falha ao atualizar foto no dispositivo {device_id}'})
        
        else:
            # Operação padrão (manter compatibilidade com versão anterior)
            student_id = body.get('student_id')
            photo_url = body.get('photo_url')
            
            if not student_id or not photo_url:
                return safe_response(400, {'error': 'student_id e photo_url são obrigatórios'})
            
            # Para compatibilidade, retornar erro sugerindo usar as novas operações
            return safe_response(400, {'error': 'Use operation=list_devices para listar dispositivos ou operation=update_single_device para atualizar um dispositivo específico'})
            
    except json.JSONDecodeError:
        return safe_response(400, {'error': 'JSON inválido no body da requisição'})
    except Exception as e:
        logger.error(f'❌ ERRO CRÍTICO: {str(e)}')
        return safe_response(500, {'error': f'Erro interno: {str(e)}'})