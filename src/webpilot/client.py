# client.py
import asyncio
import sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
SERVER_SCRIPT_PATH = SCRIPT_DIR / "server.py"

server_params = StdioServerParameters(
    command=sys.executable,
    args=[str(SERVER_SCRIPT_PATH)],
    env=None
)

async def run_client():
    print(f"Démarrage du client et lancement du serveur '{SERVER_SCRIPT_PATH}' en sous-processus...")
    
    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                print("Connecté au serveur !")

                # --- Test 1 ---
                print("\nTest de l'outil 'add(10, 5)'...")
                result_add = await session.call_tool(
                    "add", 
                    arguments={"a": 10, "b": 5}
                )
                print(f"-> Résultat : {result_add.data}")
                
                # --- Test 2 (Décommenté) ---
                print("\nTest de la ressource 'greeting://Monde'...")
                result_greeting_list = await session.read_resource("greeting://Monde")
                print(f"-> Résultat : {result_greeting_list[0].text}")

    except Exception as e:
        print(f"\n--- ERREUR ---")
        print(f"Une erreur est survenue : {e}")
        print("Vérifiez que 'server.py' est bien dans le même dossier que 'client.py'.")

if __name__ == "__main__":
    asyncio.run(run_client())