import subprocess
import sys
import os
from datetime import datetime

log_file = os.path.join(os.path.dirname(__file__), 'agendador_debug.log')

with open(log_file, 'a', encoding='utf-8') as f:
    f.write(f"\n{'='*60}\n")
    f.write(f"Execução: {datetime.now()}\n")
    f.write(f"{'='*60}\n")
    f.write(f"Python: {sys.executable}\n")
    f.write(f"Diretório: {os.getcwd()}\n")
    f.write(f"Arquivo: {__file__}\n\n")
    
    try:
        # Substitua 'seu_script.py' pelo nome do seu script real
        caminho_script = os.path.join(os.path.dirname(__file__), 'telegram_sender.py')
        
        f.write(f"Tentando executar: {caminho_script}\n\n")
        
        # Executa o script e captura saída
        resultado = subprocess.run(
            [sys.executable, caminho_script],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        f.write(f"Status Code: {resultado.returncode}\n\n")
        f.write("STDOUT:\n")
        f.write(resultado.stdout + "\n\n")
        f.write("STDERR:\n")
        f.write(resultado.stderr + "\n\n")
        
        if resultado.returncode == 0:
            f.write("✅ SUCESSO!\n")
        else:
            f.write(f"❌ ERRO (código: {resultado.returncode})\n")
    
    except subprocess.TimeoutExpired:
        f.write("❌ ERRO: Script excedeu timeout (60 segundos)\n")
    except FileNotFoundError as e:
        f.write(f"❌ ERRO: Arquivo não encontrado - {e}\n")
    except Exception as e:
        f.write(f"❌ ERRO GERAL: {str(e)}\n")
        import traceback
        f.write(traceback.format_exc())

print("Log salvo em: " + log_file)
