import subprocess
import sys
import os


def run(cmd, description):
    print(f"\n{'='*60}")
    print(f"  {description}")
    print(f"{'='*60}")
    result = subprocess.run(
        [sys.executable, "-X", "utf8"] + cmd,
        cwd=os.path.dirname(os.path.abspath(__file__)),
    )
    if result.returncode != 0:
        print(f"\nStep failed with return code {result.returncode}. Exiting.")
        sys.exit(result.returncode)


def main():
    print("\nPayment Fraud Monitoring & Chargeback Analytics")
    print("End-to-End Pipeline\n")

    run(["generate_data.py"], "Step 1/3: Generating synthetic dataset")
    run(["analysis/run_analysis.py"], "Step 2/3: Running risk flags, anomaly scoring & charts")
    run(["analysis/generate_results_notes.py"], "Step 3/3: Generating results notes & resume bullets")

    print("\n" + "="*60)
    print("  Pipeline complete.")
    print("  Outputs: outputs/results.json")
    print("           outputs/results_notes.md")
    print("           outputs/merchant_risk_metrics.csv")
    print("           outputs/charts/  (7 charts)")
    print("="*60)
    print("\nFor MySQL load, run separately:")
    print("  python load_to_mysql.py")


if __name__ == "__main__":
    main()
