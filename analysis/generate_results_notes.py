import os
import json
import pandas as pd
from tabulate import tabulate
from datetime import datetime

OUTPUT_DIR = "outputs"
RESULTS_FILE = os.path.join(OUTPUT_DIR, "results.json")
RESULTS_NOTES_FILE = os.path.join(OUTPUT_DIR, "results_notes.md")


def load_results():
    with open(RESULTS_FILE, "r") as f:
        return json.load(f)


def generate_resume_bullets(results):
    ds = results["dataset"]
    rb = results["rule_based_evaluation"]
    iso = results["isolation_forest_evaluation"]
    lc = results["chargeback_lifecycle"]

    bullets = [
        f"Generated a synthetic payment dataset of {ds['transactions']:,} transactions across {ds['merchants']} merchants and {ds['customers']} customers, with an injected fraud rate of {ds['fraud_rate_pct']}%.",
        f"Designed a MySQL schema with 5 normalized tables (merchants, customers, transactions, refunds, chargebacks) including foreign-key constraints, composite indexes, and automated data-quality checks.",
        f"Built rule-based fraud detection flags (rapid repeat, high-value outliers, unusual hours, location mismatch) achieving Precision={rb['precision']:.2f}, Recall={rb['recall']:.2f}, F1={rb['f1']:.2f} against labeled fraud ground truth.",
        f"Trained an Isolation Forest anomaly model (contamination={0.08}) achieving Precision={iso['precision']:.2f}, Recall={iso['recall']:.2f}, F1={iso['f1']:.2f}, providing a complementary signal to reduce false negatives.",
        f"Modeled the full 5-stage chargeback lifecycle (retrieval → arbitration) across {lc['total_cases']} finalized cases; overall win rate {lc['win_rate_pct']}%, total chargeback loss ${lc['total_loss_usd']:,.2f}, total arbitration fees ${lc['total_arb_fees_usd']:,.2f}.",
        f"Identified two high-risk merchants (Gambling and Crypto Exchange) whose chargeback ratios exceeded Visa's 1% and Mastercard's 1.5% remediation thresholds; recommended rolling reserve policy and velocity controls.",
        f"Developed a composite merchant risk score (weighted: decline rate 25%, refund rate 20%, location mismatch 25%, chargeback ratio 30%) to power a tiered monitoring program with weekly/monthly/quarterly review cadences.",
        f"Logged 15 Freshdesk dispute tickets covering all 8 reason codes across the chargeback lifecycle; drafted merchant-facing rebuttal templates for fraud and technical dispute categories.",
        f"Authored 6 data-backed process improvement recommendations including early evidence automation, real-time velocity controls, and an economic arbitration threshold to eliminate net-negative dispute escalations.",
        f"Produced 7 analytical charts (loss overview, chargeback ratio trend, reason code breakdown, recovery rate by stage, risk score distributions, flag comparison) for a Power BI-style dashboard.",
    ]
    return bullets


def print_results_table(results):
    ds = results["dataset"]
    rb = results["rule_based_evaluation"]
    iso = results["isolation_forest_evaluation"]
    lc = results["chargeback_lifecycle"]

    print("\n" + "="*70)
    print("  RESULTS SUMMARY — Payment Fraud Monitoring & Chargeback Analytics")
    print("="*70)

    print("\n  Dataset Statistics:")
    dataset_rows = [
        ["Merchants", ds["merchants"]],
        ["Customers", ds["customers"]],
        ["Total Transactions", f"{ds['transactions']:,}"],
        ["Fraud Transactions", f"{ds['fraud_transactions']:,} ({ds['fraud_rate_pct']}%)"],
        ["Refunds", f"{ds['refunds']:,}"],
        ["Chargeback Cases (Final)", f"{lc['total_cases']:,}"],
    ]
    print(tabulate(dataset_rows, tablefmt="rounded_outline"))

    print("\n  Model Evaluation:")
    eval_rows = [
        ["Metric", "Rule-Based", "Isolation Forest"],
        ["Precision", f"{rb['precision']:.4f}", f"{iso['precision']:.4f}"],
        ["Recall",    f"{rb['recall']:.4f}",    f"{iso['recall']:.4f}"],
        ["F1 Score",  f"{rb['f1']:.4f}",        f"{iso['f1']:.4f}"],
        ["ROC-AUC",   f"{rb['auc']}",            f"{iso['auc']}"],
        ["TP",        rb["tp"],                  iso["tp"]],
        ["FP",        rb["fp"],                  iso["fp"]],
        ["FN",        rb["fn"],                  iso["fn"]],
    ]
    print(tabulate(eval_rows, headers="firstrow", tablefmt="rounded_outline"))

    print("\n  Chargeback Lifecycle:")
    lc_rows = [
        ["Total Finalized Cases", f"{lc['total_cases']:,}"],
        ["Won", f"{lc['won_cases']:,}"],
        ["Lost", f"{lc['lost_cases']:,}"],
        ["Win Rate", f"{lc['win_rate_pct']}%"],
        ["Total Loss (USD)", f"${lc['total_loss_usd']:,.2f}"],
        ["Total Arbitration Fees", f"${lc['total_arb_fees_usd']:,.2f}"],
        ["Avg Disputed Amount", f"${lc['avg_disputed_amount']:,.2f}"],
    ]
    print(tabulate(lc_rows, tablefmt="rounded_outline"))


def save_results_notes(results, bullets):
    lines = [
        "# Results Notes",
        f"\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "\n## Resume Bullet Points\n",
    ]
    for i, bullet in enumerate(bullets, 1):
        lines.append(f"{i}. {bullet}")

    ds = results["dataset"]
    rb = results["rule_based_evaluation"]
    iso = results["isolation_forest_evaluation"]
    lc = results["chargeback_lifecycle"]

    lines.extend([
        "\n## Key Numbers for Resume\n",
        f"- Transactions: {ds['transactions']:,}",
        f"- Merchants: {ds['merchants']}",
        f"- Fraud Rate: {ds['fraud_rate_pct']}%",
        f"- Rule-Based Precision: {rb['precision']:.2f}",
        f"- Rule-Based Recall: {rb['recall']:.2f}",
        f"- Rule-Based F1: {rb['f1']:.2f}",
        f"- Isolation Forest Precision: {iso['precision']:.2f}",
        f"- Isolation Forest Recall: {iso['recall']:.2f}",
        f"- Isolation Forest F1: {iso['f1']:.2f}",
        f"- Chargeback Cases: {lc['total_cases']}",
        f"- Win Rate: {lc['win_rate_pct']}%",
        f"- Total Loss: ${lc['total_loss_usd']:,.2f}",
        f"- Arbitration Fees: ${lc['total_arb_fees_usd']:,.2f}",
    ])

    with open(RESULTS_NOTES_FILE, "w") as f:
        f.write("\n".join(lines))

    print(f"\nResults notes saved to {RESULTS_NOTES_FILE}")


def main():
    if not os.path.exists(RESULTS_FILE):
        print(f"Results file not found at {RESULTS_FILE}. Run analysis/run_analysis.py first.")
        return

    results = load_results()
    print_results_table(results)

    bullets = generate_resume_bullets(results)
    print("\n  Resume Bullets:")
    for i, b in enumerate(bullets, 1):
        print(f"\n  {i}. {b}")

    save_results_notes(results, bullets)


if __name__ == "__main__":
    main()
