import os
from supabase import create_client
from twilio.rest import Client
from datetime import datetime, timedelta
import pytz

# --- SENHAS ---
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
TWILIO_SID = os.environ.get("TWILIO_SID")
TWILIO_TOKEN = os.environ.get("TWILIO_TOKEN")
TWILIO_FROM = os.environ.get("TWILIO_FROM")

def enviar_alertas_twilio():
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    client = Client(TWILIO_SID, TWILIO_TOKEN)
    
    # Fuso Horário Brasil
    tz_br = pytz.timezone('America/Sao_Paulo')
    agora = datetime.now(tz_br)
    
    # Janela de busca: Agora até +10 minutos
    limite = agora + timedelta(minutes=10)
    
    print(f"🔎 Buscando remédios entre {agora.strftime('%H:%M')} e {limite.strftime('%H:%M')}...")

    # 1. Busca Remédios Pendentes
    # Precisamos apenas dos que estão para vencer agora
    res_med = supabase.table("medicacoes")\
        .select("*")\
        .eq("status", "Pendente")\
        .lte("data_hora_prevista", limite.isoformat())\
        .execute()
        
    remedios = res_med.data
    
    if not remedios: 
        print("✅ Nenhum remédio para agora.")
        return

    # 2. Busca Equipe de Responsáveis
    res_team = supabase.table("equipe_enfermaria").select("*").execute()
    equipe = res_team.data
    
    if not equipe:
        print("❌ Ninguém na lista de responsáveis para receber o aviso!")
        return

    # 3. Processa e Envia
    for med in remedios:
        # Pega dados básicos
        remedio = med['nome_medicamento']
        dose = med['dosagem']
        pid = med['id_participante']
        
        # Formata Data e Hora
        data_prevista_utc = datetime.fromisoformat(med['data_hora_prevista'])
        # Converte para Brasil (caso o banco esteja em UTC)
        data_prevista_br = data_prevista_utc.astimezone(tz_br)
        
        data_str = data_prevista_br.strftime('%d/%m')
        hora_str = data_prevista_br.strftime('%H:%M')

        # --- BUSCA DADOS ATUALIZADOS DO PARTICIPANTE (QUARTO E LIDER) ---
        # Isso garante que se ele mudou de quarto, o aviso vai certo
        try:
            res_part = supabase.table("participantes")\
                .select("nome_completo, quartos(nome, nome_lider)")\
                .eq("id", pid)\
                .execute()
                
            if res_part.data:
                p = res_part.data[0]
                nome_teen = p['nome_completo']
                quarto_dados = p.get('quartos') or {}
                nome_quarto = quarto_dados.get('nome', 'Sem Quarto')
                nome_lider = quarto_dados.get('nome_lider', 'Sem Líder')
            else:
                nome_teen = med['nome_participante']
                nome_quarto = "Não encontrado"
                nome_lider = "-"
        except:
            nome_teen = med['nome_participante']
            nome_quarto = "-"
            nome_lider = "-"

        # --- MONTA A MENSAGEM NO NOVO MODELO ---
        msg_texto = (
            f"🚨 *ALERTA REMÉDIO*\n"
            f"💊 *{remedio}* ({dose})\n"
            f"👤 {nome_teen}\n"
            f"🛏️ {nome_quarto}\n"
            f"🛡️ {nome_lider}\n"
            f"⏰ {data_str} às {hora_str}\n"
            f"⚠️ *Entregar ao acampante*"
        )
        
        # Envia para TODOS os responsáveis da lista
        for membro in equipe:
            tel_cru = str(membro['telefone'])
            # Limpeza do telefone
            tel_limpo = "".join(filter(str.isdigit, tel_cru))
            if not tel_limpo.startswith("55") and len(tel_limpo) > 10: 
                tel_limpo = "55" + tel_limpo
            
            try:
                client.messages.create(
                    from_=TWILIO_FROM,
                    body=msg_texto,
                    to=f"whatsapp:+{tel_limpo}"
                )
                print(f"Enviado para {membro['nome']}")
            except Exception as e:
                print(f"Erro ao enviar para {membro['nome']}: {e}")

if __name__ == "__main__":
    enviar_alertas_twilio()
