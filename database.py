import os
from typing import Optional, Tuple, List, Dict, Any
import requests
import pandas as pd
from dotenv import load_dotenv

# Carrega variáveis de ambiente do .env
load_dotenv(override=True)

try:
    from supabase import create_client, Client
except ImportError:
    Client = None
    create_client = None

KNOWN_TABLES = [
    "rel_consolidado_agentes",
    "relatorio_chamadas",
    "relatorio_geral_agentes",
    "tableid",
    "listar_agentes",
    "listar_ramais",
    "estatisticas_agente"
]

def clean_table_name(table_name: str) -> str:
    """Remove prefixo 'public.' caso exista."""
    if not table_name:
        return "rel_consolidado_agentes"
    name = table_name.strip()
    if name.startswith("public."):
        name = name.replace("public.", "", 1)
    return name

def get_credentials() -> Tuple[str, str, str]:
    """Recupera as credenciais do Supabase a partir das variáveis de ambiente."""
    load_dotenv(override=True)
    url = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
    key = os.getenv("SUPABASE_KEY", "").strip()
    table = clean_table_name(os.getenv("SUPABASE_TABLE", "rel_consolidado_agentes"))
    return url, key, table

def get_supabase_client() -> Optional["Client"]:
    """Cria e retorna uma instância do cliente Supabase."""
    url, key, _ = get_credentials()
    if not url or not key:
        return None
    if create_client is None:
        raise ImportError("A biblioteca 'supabase' não está instalada. Execute: pip install supabase")
    return create_client(url, key)

def get_available_tables() -> List[str]:
    """Descobre tabelas expostas no PostgREST do Supabase."""
    url, key, _ = get_credentials()
    if not url or not key:
        return KNOWN_TABLES

    try:
        headers = {"apikey": key, "Authorization": f"Bearer {key}"}
        resp = requests.get(f"{url}/rest/v1/", headers=headers, timeout=5)
        if resp.status_code == 200:
            schema = resp.json()
            defs = list(schema.get("definitions", {}).keys())
            if defs:
                return defs
    except Exception:
        pass
    return KNOWN_TABLES

def test_connection(table_name: Optional[str] = None) -> Tuple[bool, str, Dict[str, Any]]:
    """Testa se as credenciais do Supabase são válidas e diagnostica RLS."""
    url, key, default_table = get_credentials()
    target_table = clean_table_name(table_name or default_table)
    
    info: Dict[str, Any] = {"table": target_table, "count": 0, "has_rls_block": False}

    if not url or not key:
        return False, "SUPABASE_URL ou SUPABASE_KEY não configuradas no .env.", info

    try:
        client = get_supabase_client()
        if client is None:
            return False, "Falha ao inicializar o cliente Supabase.", info
        
        # Faz uma consulta count
        res = client.table(target_table).select("*", count="exact").limit(1).execute()
        count = res.count if res.count is not None else len(res.data)
        info["count"] = count

        if count > 0:
            return True, f"Conexão com a tabela '{target_table}' estabelecida com sucesso! ({count} registros encontrados)", info
        else:
            # 0 registros pode ser tabela vazia ou RLS bloqueando a role anon
            is_anon = "role\":\"anon" in key or "role%22%3A%22anon" in key
            if is_anon:
                info["has_rls_block"] = True
                return True, (
                    f"Conexão estabelecida com '{target_table}', porém retornou 0 registros. "
                    "Se sua tabela já possui dados no banco, a política de RLS (Row Level Security) "
                    "pode estar bloqueando a chave 'anon'. Use a chave 'service_role' ou libere leitura pública."
                ), info
            return True, f"Conexão com '{target_table}' bem-sucedida! (Tabela atualmente sem registros)", info
            
    except Exception as e:
        err_msg = str(e)
        return False, f"Erro ao conectar com Supabase na tabela '{target_table}': {err_msg}", info

def fetch_data(table_name: Optional[str] = None, limit: int = 2000) -> Tuple[pd.DataFrame, bool, str]:
    """
    Busca registros da tabela do Supabase.
    Retorna uma tupla: (DataFrame, is_real_data, status_message)
    Se a tabela estiver vazia ou com RLS restritivo, gera dados sintéticos baseados no schema real.
    """
    _, _, default_table = get_credentials()
    target_table = clean_table_name(table_name or default_table)

    client = get_supabase_client()
    if client:
        try:
            res = client.table(target_table).select("*").limit(limit).execute()
            data = res.data
            if data and len(data) > 0:
                df = pd.DataFrame(data)
                return df, True, f"Dados reais carregados da tabela '{target_table}' ({len(df)} registros)."
            else:
                sample_df = generate_realistic_telephony_data(target_table)
                return sample_df, False, (
                    f"A tabela '{target_table}' retornou 0 linhas (possível política de RLS bloqueando a chave anon). "
                    "Exibindo dados simulados com a estrutura real desta tabela."
                )
        except Exception as e:
            sample_df = generate_realistic_telephony_data(target_table)
            return sample_df, False, f"Aviso ao consultar '{target_table}': {str(e)}. Exibindo simulação."
    
    sample_df = generate_realistic_telephony_data(target_table)
    return sample_df, False, "Credenciais do Supabase ausentes no .env. Exibindo dados de demonstração."

def generate_realistic_telephony_data(table_name: str) -> pd.DataFrame:
    """Gera dados realistas no formato do schema real da OftalmoPlus."""
    import random
    from datetime import datetime, timedelta

    target = clean_table_name(table_name)

    if target == "rel_consolidado_agentes":
        agentes = [
            ("Amanda Vieira", "101", "Recepção / Agendamentos"),
            ("Beatriz Lima", "102", "Exames Oftalmológicos"),
            ("Carlos Eduardo", "103", "Cirurgias & Convênios"),
            ("Daniela Santos", "104", "SAC & Retornos"),
            ("Eduardo Ferreira", "105", "Recepção / Agendamentos"),
            ("Fernanda Souza", "106", "Exames Oftalmológicos"),
            ("Gabriel Ceruti", "107", "Supervisão & Suporte"),
            ("Juliana Ramos", "108", "Call Center Geral")
        ]
        records = []
        for idx, (name, endpoint, queues) in enumerate(agentes, 1):
            total_in = random.randint(40, 110)
            total_out = random.randint(15, 45)
            total_calls = total_in + total_out

            ans_in = int(total_in * random.uniform(0.85, 0.98))
            ans_out = int(total_out * random.uniform(0.70, 0.90))
            calls_answered = ans_in + ans_out

            lost_in = total_in - ans_in
            lost_out = total_out - ans_out
            calls_lost = lost_in + lost_out

            prod_in = round((ans_in / total_in) * 100, 1) if total_in else 0.0
            prod_out = round((ans_out / total_out) * 100, 1) if total_out else 0.0

            time_logged_sec = random.randint(25000, 28800) # ~7 a 8 horas
            time_paused_sec = random.randint(2000, 4500)
            time_spoken_sec = int(calls_answered * random.uniform(110, 220))
            time_avail_sec = max(0, time_logged_sec - time_paused_sec - time_spoken_sec)

            tma_in_sec = int(time_spoken_sec / max(1, ans_in))
            tma_out_sec = int((time_spoken_sec * 0.3) / max(1, ans_out))
            tma_sec = int(time_spoken_sec / max(1, calls_answered))

            records.append({
                "id": idx,
                "name": name,
                "endpoint": endpoint,
                "total_calls": total_calls,
                "total_calls_in": total_in,
                "total_calls_out": total_out,
                "calls_answered": calls_answered,
                "calls_answered_in": ans_in,
                "calls_answered_out": ans_out,
                "calls_lost": calls_lost,
                "calls_lost_in": lost_in,
                "calls_lost_out": lost_out,
                "percent_productivity_in": prod_in,
                "percent_productivity_out": prod_out,
                "total_time_logged": str(timedelta(seconds=time_logged_sec)),
                "total_time_paused": str(timedelta(seconds=time_paused_sec)),
                "total_time_spoken": str(timedelta(seconds=time_spoken_sec)),
                "total_time_spoken_in": str(timedelta(seconds=int(time_spoken_sec * 0.75))),
                "total_time_spoken_out": str(timedelta(seconds=int(time_spoken_sec * 0.25))),
                "total_time_available": str(timedelta(seconds=time_avail_sec)),
                "tma": f"{tma_sec // 60:02d}:{tma_sec % 60:02d}",
                "tma_in": f"{tma_in_sec // 60:02d}:{tma_in_sec % 60:02d}",
                "tma_out": f"{tma_out_sec // 60:02d}:{tma_out_sec % 60:02d}",
                "queues": queues,
                "update_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
        return pd.DataFrame(records)

    elif target == "relatorio_chamadas":
        agentes = ["Amanda Vieira", "Beatriz Lima", "Carlos Eduardo", "Daniela Santos", "Eduardo Ferreira", "Fernanda Souza"]
        filas = ["Agendamento de Consultas", "Exames Oftalmológicos", "Cirurgias", "Cancelamento & Dúvidas", "Convênios"]
        reasons = ["Desligado pelo Atendente", "Desligado pelo Cliente", "Tempo Limite Fila", "Transferido"]
        directions = ["Entrante", "Sainte"]
        
        base_time = datetime.now() - timedelta(days=7)
        records = []
        for i in range(1, 151):
            t_call = base_time + timedelta(minutes=random.randint(0, 7 * 24 * 60))
            ta_sec = random.randint(45, 480) # tempo de atendimento
            teu_sec = random.randint(5, 120)  # tempo de espera
            disp = random.choices(["ANSWERED", "NO ANSWER", "BUSY", "ABANDONED"], weights=[78, 10, 4, 8])[0]
            agent = random.choice(agentes) if disp == "ANSWERED" else "Nenhum"
            fila = random.choice(filas)
            direction = random.choice(directions)

            records.append({
                "id": i,
                "agent_name": agent,
                "init_time": t_call.strftime("%Y-%m-%d %H:%M:%S"),
                "final_time": (t_call + timedelta(seconds=ta_sec + teu_sec)).strftime("%Y-%m-%d %H:%M:%S"),
                "src": f"1198{random.randint(1000000, 9999999)}",
                "dst": "0800-OFTALMO" if direction == "Entrante" else f"1197{random.randint(1000000, 9999999)}",
                "teu": teu_sec,
                "tef": random.randint(0, 15),
                "tt": ta_sec + teu_sec,
                "queuename": fila,
                "ta": ta_sec if disp == "ANSWERED" else 0,
                "tet": teu_sec,
                "disposition": disp,
                "reason_end_call": random.choice(reasons),
                "status_call": "Atendida" if disp == "ANSWERED" else "Perdida / Abandonada",
                "dstchannel": f"PJSIP/{random.randint(101, 108)}-00000{i:03d}",
                "call_direction": direction,
                "has_intelligence": random.choice([True, False]),
                "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
        return pd.DataFrame(records)

    elif target == "tableid":
        filas = ["Agendamento de Consultas", "Exames Oftalmológicos", "Cirurgias", "Cancelamento & Dúvidas", "Convênios"]
        records = []
        for idx, f in enumerate(filas, 1):
            rec = random.randint(150, 450)
            ans = int(rec * random.uniform(0.85, 0.95))
            ans_30s = int(ans * random.uniform(0.80, 0.90))
            records.append({
                "id": idx,
                "name": f,
                "waiting_calls": random.randint(0, 5),
                "members_online": random.randint(4, 8),
                "members_offline": random.randint(1, 3),
                "received": rec,
                "answered": ans,
                "answered_less_30s": ans_30s,
                "percent_answered": round((ans / rec) * 100, 1),
                "abandon_more_30s": rec - ans,
                "ns_30s": round((ans_30s / rec) * 100, 1),
                "ns_goal": 85.0,
                "tma": f"00:03:{random.randint(10, 50):02d}",
                "tme": f"00:00:{random.randint(15, 45):02d}",
                "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
        return pd.DataFrame(records)

    else:
        # Fallback genérico
        return generate_sample_data()

def generate_sample_data(num_records: int = 100) -> pd.DataFrame:
    """Gera DataFrame de fallback."""
    import random
    from datetime import datetime, timedelta

    agentes = ["Amanda Vieira", "Beatriz Lima", "Carlos Eduardo", "Daniela Santos", "Eduardo Ferreira"]
    filas = ["Agendamento Oftalmo", "Exames & Laudos", "Cirurgias", "SAC", "Recepção"]
    records = []
    base_time = datetime.now() - timedelta(days=10)

    for i in range(1, num_records + 1):
        dt = base_time + timedelta(minutes=random.randint(0, 10 * 24 * 60))
        ta = random.randint(60, 600)
        te = random.randint(5, 120)
        records.append({
            "id": i,
            "data_hora": dt.strftime("%Y-%m-%d %H:%M:%S"),
            "agente": random.choice(agentes),
            "fila": random.choice(filas),
            "status": random.choice(["Atendida", "Abandonada", "Transferida"]),
            "duracao_segundos": ta,
            "tempo_espera_segundos": te,
            "satisfacao": random.choices([1, 2, 3, 4, 5], weights=[2, 5, 15, 40, 38])[0]
        })
    return pd.DataFrame(records)
