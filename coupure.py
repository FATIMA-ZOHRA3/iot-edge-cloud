import argparse
import subprocess
import time
import sys

def simuler_coupure(duree: int):
    print(f"🔌 [TEST] Début de la simulation de coupure Cloud pour {duree} secondes...")
    try:
        # On demande à Docker d'arrêter le conteneur cloud
        subprocess.run(["docker", "compose", "stop", "cloud"], check=True)
        print("❌ [TEST] Le service Cloud est COUPÉ (Panne Internet simulée).")
        print("👉 Regardez Grafana : la courbe du Cloud doit s'arrêter, mais l'Edge continue !")
        
        # On attend la durée spécifiée
        time.sleep(duree) 
        
        print("\n🔌 [TEST] Rétablissement de la connexion...")
        # On redémarre le conteneur cloud
        subprocess.run(["docker", "compose", "start", "cloud"], check=True)
        print("✅ [TEST] Le service Cloud est RÉTABLI. Fin du test.")
        
    except subprocess.CalledProcessError as e:
        print(f"Erreur lors de la commande Docker : {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nArrêt manuel du test. N'oubliez pas de relancer le cloud avec 'docker compose start cloud'.")
        sys.exit(0)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Simule une coupure du service Cloud.")
    parser.add_argument("--duree", type=int, default=20, 
                        help="Durée de la coupure en secondes (défaut : 20)")
    
    args = parser.parse_args()
    
    if args.duree < 1:
        print("Erreur : La durée doit être au moins de 1 seconde.")
        sys.exit(1)
        
    simuler_coupure(args.duree)