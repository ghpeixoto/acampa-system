import os
import requests
from supabase import create_client
from datetime import datetime, timedelta
import pytz

# --- CONFIGURAÇÕES ---
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def agora_br():
    # Define fuso horário de Brasília
    return datetime.now(pytz.timezone('America/Sao_Paulo'))

def enviar_aviso_grupo():
    # Conecta no Banco
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    # Define janela de tempo: Agora até daqui a 20 min
    agora = agora_br()
    limite_futuro = agora + timedelta(minutes=20)
    
    print(f"🔎 Buscando remédios entre {agora.strftime('%H:%M')} e {limite_futuro.strftime('%H:%M')}...")

    try:
        # Busca remédios PENDENTES nesse horário
        response = supabase.table("medicacoes")\
            .select("*")\
            .eq("status", "Pendente")\
            .gte("data_hora_prevista", agora.isoformat())\
            .lte("data_hora_prevista", limite_futuro.isoformat())\
            .execute()
        
        remedios = response.data
        
        if not remedios:
            print("✅ Nenhum remédio próximo para avisar.")
            return

        print(f"🚨 Encontrados {len(remedios)} remédios!")

        for item in remedios:
            # Recupera dados
            paciente = item['nome_participante'] # Ex: João (Quarto 1)
            remedio = item['nome_medicamento']
            dose = item['dosagem']
            resp_nome = item.get('nome_lider', 'Resp.') # Nome do responsável
            
            # Formata hora
            hora_iso = item['data_hora_prevista']
            hora_obj = datetime.fromisoformat(hora_iso)
            hora_fmt = hora_obj.strftime('%H:%M')

            # Cria a Mensagem
            msg = (
                f"🚨 *ALERTA DE MEDICAÇÃO*\n\n"
                f"💊 *{remedio}* ({dose})\n"
                f"👤 {paciente}\n"
                f"⏰ Horário: *{hora_fmt}*\n"
                f"👨‍👩‍👧 Resp: {resp_nome}\n\n"
                f"⚠️ *Entregar em 5-10 min!*"
            )
            
            # Link para abrir o sistema direto
            link_sistema = "https://acampateens.streamlit.app/"
            
            payload = {
                "chat_id": TELEGRAM_CHAT_ID,
                "text": msg,
                "parse_mode": "Markdown",
                "reply_markup": {
                    "inline_keyboard": [[
                        {"text": "🔗 Abrir Enfermaria", "url": link_sistema}
                    ]]
                }
            }

            # Envia
            requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", json=payload)
            print(f"Mensagem enviada para {paciente}")
            
    except Exception as e:
        print(f"Erro no script: {e}")

if __name__ == "__main__":
    enviar_aviso_grupo()