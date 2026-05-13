import argparse
import time
from backend.agent.orchestrator import get_orchestrator

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mission", required=True)
    args = parser.parse_args()
    
    orchestrator = get_orchestrator()
    if args.mission == "TEST_REASONING_2026":
        query = "Une cliente a la peau sèche après son soin Top Sourcils. Quel produit SkinMinute de ma formation dois-je lui conseiller ?"
        result = orchestrator.process(query, "test")
        print(f"⏱️  [TTFT] Premier mot en : {result.ttft_ms:.2f}ms")
        print(f"📝 [RESPONSE] Mina : {result.response[:100]}...")
        
        if result.ttft_ms < 600:
            print("✅ [PERF] On est dans la zone LIVE !")
        else:
            print("⚠️ [PERF] Encore trop lent pour le vocal.")

if __name__ == "__main__":
    main()
