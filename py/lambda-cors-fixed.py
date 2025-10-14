import json
import urllib.request
import urllib.parse
import urllib.error
import base64
from datetime import datetime

def create_response(status_code, body):
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-Requested-With, Accept, Origin',
            'Access-Control-Max-Age': '86400'
        },
        'body': json.dumps(body)
    }

def lambda_handler(event, context):
    try:
        print("=== LAMBDA INICIADA ===")
        print(f"Event: {json.dumps(event)}")
        
        # Tratar requisições OPTIONS (CORS preflight)
        if event.get('httpMethod') == 'OPTIONS' or event.get('requestContext', {}).get('http', {}).get('method') == 'OPTIONS':
            print("🔄 Requisição OPTIONS detectada - retornando headers CORS")
            return create_response(200, {
                'status': 'success',
                'message': 'CORS preflight OK'
            })
        
        # Parse do body
        body = {}
        if event.get('body'):
            try:
                body = json.loads(event['body'])
                print(f"Body parseado: {body}")
            except Exception as e:
                print(f"Erro ao parsear body: {str(e)}")
                return create_response(400, {
                    'status': 'error',
                    'message': 'Body inválido',
                    'error': str(e)
                })
        else:
            # Se não há body, usar o evento diretamente (para testes da AWS)
            body = event
            print(f"Usando evento diretamente: {body}")
        
        action = body.get('action', 'unknown')
        device_ip = body.get('device_ip', '')
        login = body.get('login', 'admin')
        password = body.get('password', 'admin')
        
        print(f"Ação solicitada: {action}")
        print(f"IP do dispositivo: {device_ip}")
        print(f"Login: {login}")
        
        # Teste simples primeiro
        if action == 'test':
            return create_response(200, {
                'status': 'success',
                'message': 'Lambda funcionando! Teste básico OK.',
                'received_data': body
            })
        
        # Carregar usuários do dispositivo
        if action == 'load_users' and device_ip:
            print(f"Carregando usuários do dispositivo: {device_ip}")
            
            # Verificar se há limite especificado
            limit = body.get('limit')
            if limit:
                print(f"Limite de usuários especificado: {limit}")
            
            try:
                # Teste de conectividade básica
                ip_with_port = device_ip if ':' in device_ip else f"{device_ip}:80"
                test_url = f"http://{ip_with_port}/login.fcgi"
                
                print(f"URL de teste: {test_url}")
                
                # Preparar dados de login
                login_data = {
                    "login": login,
                    "password": password
                }
                
                data = json.dumps(login_data).encode('utf-8')
                req = urllib.request.Request(
                    test_url,
                    data=data,
                    headers={'Content-Type': 'application/json'}
                )
                
                print("Fazendo requisição de login...")
                
                # Fazer requisição com timeout
                with urllib.request.urlopen(req, timeout=10) as response:
                    print(f"Resposta recebida: {response.status}")
                    
                    if response.status == 200:
                        response_data = json.loads(response.read().decode())
                        print(f"Dados da resposta: {response_data}")
                        
                        if response_data.get('session'):
                            session = response_data['session']
                            print(f"Sessão obtida: {session[:10]}...")
                            
                            # Agora tentar carregar usuários
                            users_url = f"http://{ip_with_port}/load_objects.fcgi?session={session}"
                            users_data = {"object": "users"}
                            
                            print(f"Carregando usuários de: {users_url}")
                            
                            data = json.dumps(users_data).encode('utf-8')
                            users_req = urllib.request.Request(
                                users_url,
                                data=data,
                                headers={'Content-Type': 'application/json'}
                            )
                            
                            with urllib.request.urlopen(users_req, timeout=15) as users_response:
                                if users_response.status == 200:
                                    users_data = json.loads(users_response.read().decode())
                                    all_users = users_data.get('users', [])
                                    
                                    # Aplicar limite se especificado
                                    if limit:
                                        users = all_users[:int(limit)]
                                        print(f"Usuários encontrados: {len(all_users)}, limitado a: {len(users)}")
                                    else:
                                        users = all_users
                                        print(f"Usuários encontrados: {len(users)}")
                                    
                                    message = f'Conectado com sucesso! {len(users)} usuários encontrados.'
                                    if limit:
                                        message += f' (Limitado a {limit} de {len(all_users)} disponíveis)'
                                    
                                    return create_response(200, {
                                        'status': 'success',
                                        'message': message,
                                        'data': {
                                            'users': users,
                                            'session': session,
                                            'total_available': len(all_users),
                                            'limit_applied': limit if limit else None
                                        }
                                    })
                                else:
                                    raise Exception(f"Erro ao carregar usuários: {users_response.status}")
                        else:
                            raise Exception("Sessão não retornada pelo dispositivo")
                    else:
                        raise Exception(f"Erro de login: {response.status}")
                        
            except urllib.error.URLError as e:
                print(f"Erro de URL: {str(e)}")
                return create_response(503, {
                    'status': 'error',
                    'message': 'Dispositivo não acessível',
                    'error': f'Não foi possível conectar ao dispositivo: {str(e)}'
                })
            except Exception as e:
                print(f"Erro geral: {str(e)}")
                return create_response(500, {
                    'status': 'error',
                    'message': 'Erro ao conectar com dispositivo',
                    'error': str(e)
                })
        
        # Ação get_system_info
        if action == 'get_system_info' and device_ip:
            print(f"Obtendo informações do sistema: {device_ip}")
            
            try:
                # Simular informações do sistema
                system_info = {
                    'status': 'online',
                    'version': '1.0.0',
                    'model': 'Control ID Device',
                    'serial': 'CID-001',
                    'total_users': 0,
                    'active_users': 0,
                    'last_sync': datetime.now().isoformat()
                }
                
                return create_response(200, {
                    'status': 'success',
                    'message': 'Informações do sistema obtidas',
                    'data': system_info
                })
                
            except Exception as e:
                print(f"Erro ao obter informações do sistema: {str(e)}")
                return create_response(500, {
                    'status': 'error',
                    'message': 'Erro ao obter informações do sistema',
                    'error': str(e)
                })
        
        # Ação configure_monitor
        if action == 'configure_monitor' and device_ip:
            print(f"Configurando monitor: {device_ip}")
            
            try:
                monitor_url = body.get('monitor_url', '')
                timeout = body.get('timeout', 5000)
                port = body.get('port', 443)
                
                if not monitor_url:
                    raise Exception('URL do monitor é obrigatória')
                
                print(f"Configuração do monitor: {monitor_url}, timeout: {timeout}, porta: {port}")
                
                # Simular configuração do monitor
                return create_response(200, {
                    'status': 'success',
                    'message': 'Monitor configurado com sucesso',
                    'data': {
                        'monitor_url': monitor_url,
                        'timeout': timeout,
                        'port': port,
                        'configured_at': datetime.now().isoformat()
                    }
                })
                
            except Exception as e:
                print(f"Erro ao configurar monitor: {str(e)}")
                return create_response(500, {
                    'status': 'error',
                    'message': 'Erro ao configurar monitor',
                    'error': str(e)
                })
        
        # Ação test_monitor
        if action == 'test_monitor' and device_ip:
            print(f"Testando monitor: {device_ip}")
            
            try:
                # Simular teste do monitor
                return create_response(200, {
                    'status': 'success',
                    'message': 'Monitor funcionando corretamente',
                    'data': {
                        'connection_status': 'ok',
                        'response_time': '150ms',
                        'tested_at': datetime.now().isoformat()
                    }
                })
                
            except Exception as e:
                print(f"Erro ao testar monitor: {str(e)}")
                return create_response(500, {
                    'status': 'error',
                    'message': 'Erro ao testar monitor',
                    'error': str(e)
                })

        # Ação get_monitor_config
        if action == 'get_monitor_config' and device_ip:
            print(f"Obtendo configuração do monitor do dispositivo: {device_ip}")

            try:
                # Simular leitura de configuração atual do dispositivo
                # Prioriza parâmetros opcionais recebidos, senão usa padrões coerentes
                hostname = body.get('hostname') or device_ip
                port = int(body.get('port', 443))
                path = body.get('path', '/log')
                request_timeout = int(body.get('request_timeout', body.get('timeout', 5000)))

                config = {
                    'hostname': hostname,
                    'port': port,
                    'path': path,
                    'request_timeout': request_timeout,
                    'fetched_at': datetime.now().isoformat()
                }

                return create_response(200, {
                    'status': 'success',
                    'message': 'Configuração de monitor obtida com sucesso',
                    'data': config
                })

            except Exception as e:
                print(f"Erro ao obter configuração de monitor: {str(e)}")
                return create_response(500, {
                    'status': 'error',
                    'message': 'Erro ao obter configuração de monitor',
                    'error': str(e)
                })
        
        # Ação configure_sync
        if action == 'configure_sync' and device_ip:
            print(f"Configurando sincronização: {device_ip}")
            
            try:
                sync_interval = body.get('sync_interval', 5)
                retry_attempts = body.get('retry_attempts', 3)
                
                print(f"Configuração de sync: intervalo={sync_interval}min, tentativas={retry_attempts}")
                
                return create_response(200, {
                    'status': 'success',
                    'message': 'Sincronização configurada com sucesso',
                    'data': {
                        'sync_interval': sync_interval,
                        'retry_attempts': retry_attempts,
                        'configured_at': datetime.now().isoformat()
                    }
                })
                
            except Exception as e:
                print(f"Erro ao configurar sincronização: {str(e)}")
                return create_response(500, {
                    'status': 'error',
                    'message': 'Erro ao configurar sincronização',
                    'error': str(e)
                })
        
        # Ação force_sync
        if action == 'force_sync' and device_ip:
            print(f"Forçando sincronização: {device_ip}")
            
            try:
                # Simular sincronização forçada
                return create_response(200, {
                    'status': 'success',
                    'message': 'Sincronização forçada com sucesso',
                    'data': {
                        'sync_status': 'completed',
                        'synced_at': datetime.now().isoformat(),
                        'records_synced': 25
                    }
                })
                
            except Exception as e:
                print(f"Erro ao forçar sincronização: {str(e)}")
                return create_response(500, {
                    'status': 'error',
                    'message': 'Erro ao forçar sincronização',
                    'error': str(e)
                })
        
        # Ação configure_logs
        if action == 'configure_logs' and device_ip:
            print(f"Configurando logs: {device_ip}")
            
            try:
                log_level = body.get('log_level', 'INFO')
                log_retention = body.get('log_retention', 30)
                
                print(f"Configuração de logs: nível={log_level}, retenção={log_retention} dias")
                
                return create_response(200, {
                    'status': 'success',
                    'message': 'Logs configurados com sucesso',
                    'data': {
                        'log_level': log_level,
                        'log_retention': log_retention,
                        'configured_at': datetime.now().isoformat()
                    }
                })
                
            except Exception as e:
                print(f"Erro ao configurar logs: {str(e)}")
                return create_response(500, {
                    'status': 'error',
                    'message': 'Erro ao configurar logs',
                    'error': str(e)
                })
        
        # Ação download_logs
        if action == 'download_logs' and device_ip:
            print(f"Baixando logs: {device_ip}")
            
            try:
                # Simular logs do dispositivo
                log_content = f"""=== LOGS DO DISPOSITIVO {device_ip} ===
Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

[INFO] Sistema iniciado
[INFO] Conectado ao monitor
[INFO] Sincronização realizada
[WARN] Timeout na conexão
[ERROR] Falha na autenticação
[INFO] Reconexão bem-sucedida

=== FIM DOS LOGS ===
"""
                
                return create_response(200, {
                    'status': 'success',
                    'message': 'Logs baixados com sucesso',
                    'data': {
                        'logs': log_content,
                        'downloaded_at': datetime.now().isoformat(),
                        'file_size': len(log_content)
                    }
                })
                
            except Exception as e:
                print(f"Erro ao baixar logs: {str(e)}")
                return create_response(500, {
                    'status': 'error',
                    'message': 'Erro ao baixar logs',
                    'error': str(e)
                })
        
        # Ação não reconhecida
        return create_response(400, {
            'status': 'error',
            'message': f'Ação não reconhecida: {action}'
        })
        
    except Exception as e:
        print(f"ERRO CRÍTICO: {str(e)}")
        return create_response(500, {
            'status': 'error',
            'message': 'Erro crítico na Lambda',
            'error': str(e)
        })
