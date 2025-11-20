import json
from pathlib import Path
import os

# --- CONFIGURAÇÃO ---
# 1. Altere para o caminho do seu arquivo JSON
ARQUIVO_JSON = Path('bb.json')

# 2. Altere para o caminho do diretório que você quer limpar
DIRETORIO_RENDER = Path('renders/renders_auto_20251117_181630')

# 3. Altere 'path' se a chave no seu JSON tiver um nome diferente
CHAVE_DO_PATH_NO_JSON = 'file_path'
# --------------------


def limpar_arquivos_extras():
    """
    Exclui arquivos do DIRETORIO_RENDER que não estão listados
    no ARQUIVO_JSON.
    """
    
    # --- Passo 1: Ler o JSON e coletar todos os caminhos "úteis" ---
    print(f"🔎 Lendo arquivos 'úteis' de '{ARQUIVO_JSON}'...")
    arquivos_uteis = set()
    
    try:
        with open(ARQUIVO_JSON, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Assumindo que o JSON é uma LISTA de itens
        for item in data:
            if CHAVE_DO_PATH_NO_JSON in item:
                # Converte a string do JSON em um objeto Path
                # Isso normaliza o caminho (ex: 'renders/./img.png' -> 'renders/img.png')
                caminho_util = Path(item[CHAVE_DO_PATH_NO_JSON])
                arquivos_uteis.add(caminho_util)
            
    except FileNotFoundError:
        print(f"❌ ERRO: O arquivo JSON '{ARQUIVO_JSON}' não foi encontrado.")
        return
    except json.JSONDecodeError:
        print(f"❌ ERRO: O arquivo '{ARQUIVO_JSON}' não é um JSON válido.")
        return
    except Exception as e:
        print(f"❌ ERRO inesperado ao ler o JSON: {e}")
        return

    if not arquivos_uteis:
        print("⚠️ Atenção: Nenhum caminho de arquivo foi encontrado no JSON.")
        # Podemos continuar, mas provavelmente todos os arquivos serão marcados para exclusão.
        
    print(f"✅ Encontrados {len(arquivos_uteis)} caminhos de arquivos úteis no JSON.")

    # --- Passo 2: Listar TODOS os arquivos que existem no diretório ---
    print(f"\n🔎 Verificando todos os arquivos existentes em '{DIRETORIO_RENDER}'...")
    
    if not DIRETORIO_RENDER.is_dir():
        print(f"❌ ERRO: O diretório '{DIRETORIO_RENDER}' não existe.")
        return

    arquivos_existentes = set()
    # .rglob('*') busca arquivos no diretório e em TODOS os subdiretórios
    for file_path in DIRETORIO_RENDER.rglob('*'):
        if file_path.is_file():
            arquivos_existentes.add(file_path)

    print(f"✅ Encontrados {len(arquivos_existentes)} arquivos no total no diretório.")

    # --- Passo 3: Calcular a diferença ---
    # (Arquivos que existem na pasta) - (Arquivos que estão no JSON)
    arquivos_para_excluir = arquivos_existentes - arquivos_uteis

    if not arquivos_para_excluir:
        print("\n✨ NENHUM arquivo inútil encontrado. O diretório está limpo!")
        return

    print(f"\n--- ❗ Encontrados {len(arquivos_para_excluir)} arquivos para excluir ---")

    # --- Passo 4: SIMULAÇÃO (Dry Run) ---
    print("\n--- SIMULAÇÃO (DRY RUN) ---")
    print("Os seguintes arquivos SERÃO excluídos (verifique se está correto):")
    
    # Mostra os 20 primeiros para verificação
    for f in sorted(list(arquivos_para_excluir)):
        print(f"  - {f}")
    # if len(arquivos_para_excluir) > 20:
    #     print(f"  - ...e mais {len(arquivos_para_excluir) - 20} arquivos.")

    # --- Passo 5: Confirmação e Exclusão ---
    print("\n" + "="*40)
    print("           ⚠️  AÇÃO DE EXCLUSÃO  ⚠️")
    print("="*40)
    
    try:
        # Pede confirmação ao usuário
        confirm = input(f"Você tem CERTEZA que deseja excluir estes {len(arquivos_para_excluir)} arquivos? \n(Digite 'sim' para confirmar): ").strip().lower()
    except KeyboardInterrupt:
        print("\nCancelado pelo usuário.")
        return

    if confirm == 'sim':
        print("\n--- 🗑️  INICIANDO EXCLUSÃO PERMANENTE ---")
        deleted_count = 0
        error_count = 0
        
        for file_path in arquivos_para_excluir:
            try:
                os.remove(file_path) # Usamos os.remove (ou file_path.unlink())
                print(f"EXCLUÍDO: {file_path}")
                deleted_count += 1
            except OSError as e:
                print(f"ERRO ao excluir {file_path}: {e}")
                error_count += 1
        
        print("\n--- Resumo da Exclusão ---")
        print(f"✅ Arquivos excluídos com sucesso: {deleted_count}")
        print(f"❌ Erros durante a exclusão: {error_count}")
    
    else:
        print("\n🚫 EXCLUSÃO CANCELADA. Nenhum arquivo foi alterado.")


# --- Inicia o script ---
if __name__ == "__main__":
    limpar_arquivos_extras()