import os
from supabase import create_client
from twilio.rest import Client
from datetime import datetime, timedelta
import pytz

# --- SENHAS DO GITHUB ---
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
TWILIO_SID = os.environ.get("TWILIO_SID")
TWILIO_TOKEN = os.environ.get("TWILIO_TOKEN")
TWILIO_FROM = os.environ.get("TWILIO_FROM")

def enviar_alertas_twilio():
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    client = Client(TWILIO_SID, TWILIO_TOKEN)
    
    # Janela de 10 min (5 min antes até 5 min depois)
    agora = datetime.now(pytz.timezone('America/Sao_Paulo'))
    limite = agora + timedelta(minutes=10)
    
    print(f"🔎 Buscando remédios até {limite.strftime('%H:%M')}...")

    # 1. Busca Remédios Pendentes
    res_med = supabase.table("medicacoes").select("*").eq("status", "Pendente").lte("data_hora_prevista", limite.isoformat()).execute()
    remedios = res_med.data
    
    if not remedios: return

    # 2. Busca Equipe de Enfermagem
    res_team = supabase.table("equipe_enfermaria").select("*").execute()
    equipe = res_team.data
    
    if not equipe:
        print("❌ Ninguém na equipe para avisar!")
        return

    # 3. Dispara Mensagens
    for med in remedios:
        nome_paciente = med['nome_participante']
        remedio = med['nome_medicamento']
        dose = med['dosagem']
        hora = datetime.fromisoformat(med['data_hora_prevista']).strftime('%H:%M')
        
        msg_texto = (
            f"🚨 *ALERTA ENFERMARIA*\n"
            f"💊 *{remedio}* ({dose})\n"
            f"👤 {nome_paciente}\n"
            f"⏰ Horário: {hora}\n"
            f"⚠️ *Entregar Agora!*"
        )
        
        # Envia para CADA membro da equipe
        for membro in equipe:
            tel = "".join(filter(str.isdigit, str(membro['telefone'])))
            if not tel.startswith("55"): tel = "55" + tel
            
            try:
                client.messages.create(
                    from_=TWILIO_FROM,
                    body=msg_texto,
                    to=f"whatsapp:+{tel}"
                )
                print(f"Enviado para {membro['nome']}")
            except Exception as e:
                print(f"Erro ao enviar para {membro['nome']}: {e}")

if __name__ == "__main__":
    enviar_alertas_twilio()
