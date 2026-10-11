import os
import sys
import json
import warnings
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")

if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (
    precision_score, recall_score, f1_score,
    confusion_matrix, classification_report,
    roc_auc_score,
)
from tabulate import tabulate
from datetime import datetime

warnings.filterwarnings("ignore")

DATA_DIR = "data"
OUTPUT_DIR = "outputs"
CHARTS_DIR = os.path.join(OUTPUT_DIR, "charts")
RESULTS_FILE = os.path.join(OUTPUT_DIR, "results.json")

os.makedirs(CHARTS_DIR, exist_ok=True)

PALETTE = {
    "primary": "#2563EB",
    "danger": "#DC2626",
    "warning": "#D97706",
    "success": "#16A34A",
    "neutral": "#6B7280",
    "bg": "#0F172A",
    "surface": "#1E293B",
    "text": "#F1F5F9",
}

plt.rcParams.update({
    "figure.facecolor": PALETTE["bg"],
    "axes.facecolor": PALETTE["surface"],
    "axes.edgecolor": "#334155",
    "axes.labelcolor": PALETTE["text"],
    "xtick.color": PALETTE["text"],
    "ytick.color": PALETTE["text"],
    "text.color": PALETTE["text"],
    "grid.color": "#334155",
    "grid.alpha": 0.4,
    "font.family": "DejaVu Sans",
    "font.size": 10,
    "axes.titlesize": 12,
    "axes.titleweight": "bold",
})


def load_data():
    merchants = pd.read_csv(f"{DATA_DIR}/merchants.csv")
    customers = pd.read_csv(f"{DATA_DIR}/customers.csv")
    transactions = pd.read_csv(f"{DATA_DIR}/transactions.csv", parse_dates=["txn_datetime"])
    refunds = pd.read_csv(f"{DATA_DIR}/refunds.csv")
    chargebacks = pd.read_csv(f"{DATA_DIR}/chargebacks.csv", parse_dates=["stage_date", "deadline_date"])
    return merchants, customers, transactions, refunds, chargebacks


def compute_merchant_metrics(transactions, chargebacks, merchants):
    approved = transactions[transactions["status"] == "approved"]

    txn_stats = transactions.groupby("merchant_id").agg(
        total_txns=("transaction_id", "count"),
        approved_txns=("status", lambda x: (x == "approved").sum()),
        declined_txns=("status", lambda x: (x == "declined").sum()),
        refunded_txns=("status", lambda x: (x == "refunded").sum()),
        avg_ticket=("amount", lambda x: x[transactions.loc[x.index, "status"] == "approved"].mean()),
        total_volume=("amount", lambda x: x[transactions.loc[x.index, "status"] == "approved"].sum()),
        fraud_txns=("is_fraud", "sum"),
    ).reset_index()

    final_cbs = chargebacks[chargebacks["is_final_stage"] == 1]
    cb_stats = final_cbs.groupby("merchant_id").agg(
        unique_chargebacks=("transaction_id", "nunique"),
        total_loss=("loss_amount", "sum"),
        total_arb_fees=("arbitration_fee", "sum"),
        won_cases=("outcome", lambda x: (x == "won").sum()),
        total_cases=("outcome", "count"),
    ).reset_index()
    cb_stats["win_rate"] = cb_stats["won_cases"] / cb_stats["total_cases"].replace(0, np.nan)
    cb_stats["recovery_rate"] = cb_stats["win_rate"]

    metrics = merchants.merge(txn_stats, on="merchant_id", how="left").merge(
        cb_stats, on="merchant_id", how="left"
    )
    metrics = metrics.fillna(0)

    metrics["decline_rate"] = metrics["declined_txns"] / metrics["total_txns"].replace(0, np.nan)
    metrics["refund_rate"] = metrics["refunded_txns"] / metrics["total_txns"].replace(0, np.nan)
    metrics["chargeback_ratio"] = metrics["unique_chargebacks"] / metrics["approved_txns"].replace(0, np.nan)

    loc_mismatch = (
        transactions[transactions["status"] == "approved"]
        .groupby("merchant_id")["location_mismatch"]
        .mean()
        .reset_index()
        .rename(columns={"location_mismatch": "location_mismatch_rate"})
    )
    metrics = metrics.merge(loc_mismatch, on="merchant_id", how="left").fillna(0)

    metrics["composite_risk_score"] = (
        metrics["decline_rate"] * 25
        + metrics["refund_rate"] * 20
        + metrics["location_mismatch_rate"] * 25
        + metrics["chargeback_ratio"] * 300
        + metrics["is_high_risk"] * 10
    )
    metrics = metrics.fillna(0)
    return metrics


def build_rule_based_flags(transactions):
    approved = transactions[transactions["status"] == "approved"].copy()
    approved = approved.sort_values("txn_datetime")

    approved["rapid_repeat"] = 0
    for key, group in approved.groupby(["merchant_id", "customer_id"]):
        idx = group.index
        times = group["txn_datetime"]
        for i, (loc, t) in enumerate(zip(idx, times)):
            window = times[(times >= t - pd.Timedelta(minutes=30)) & (times <= t)]
            if len(window) >= 3:
                approved.loc[loc, "rapid_repeat"] = 1

    merchant_stats = (
        approved.groupby("merchant_id")["amount"]
        .agg(["mean", "std"])
        .reset_index()
        .rename(columns={"mean": "m_mean", "std": "m_std"})
    )
    approved = approved.merge(merchant_stats, on="merchant_id", how="left")
    approved["z_score"] = (approved["amount"] - approved["m_mean"]) / approved["m_std"].replace(0, np.nan)
    approved["high_value_outlier"] = (approved["z_score"] > 3.0).astype(int)

    approved["unusual_hour"] = approved["hour_of_day"].apply(lambda h: 1 if 2 <= h <= 5 else 0)

    approved["rule_flag"] = (
        (approved["rapid_repeat"] == 1)
        | (approved["high_value_outlier"] == 1)
        | (approved["unusual_hour"] == 1)
        | (approved["location_mismatch"] == 1)
    ).astype(int)

    return approved


def build_isolation_forest_flags(transactions, contamination=0.08):
    approved = transactions[transactions["status"] == "approved"].copy()

    feature_cols = ["amount", "hour_of_day", "location_mismatch"]
    X = approved[feature_cols].fillna(0)
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    iso = IsolationForest(contamination=contamination, random_state=42, n_estimators=200)
    approved["iso_score"] = iso.fit_predict(X_scaled)
    approved["iso_anomaly"] = (approved["iso_score"] == -1).astype(int)

    raw_scores = iso.score_samples(X_scaled)
    min_s, max_s = raw_scores.min(), raw_scores.max()
    approved["anomaly_score_normalized"] = 1 - (raw_scores - min_s) / (max_s - min_s + 1e-9)

    return approved


def evaluate_flags(flagged_df, label_col="is_fraud", pred_col="rule_flag", label="Rule-Based"):
    y_true = flagged_df[label_col].values
    y_pred = flagged_df[pred_col].values

    precision = precision_score(y_true, y_pred, zero_division=0)
    recall = recall_score(y_true, y_pred, zero_division=0)
    f1 = f1_score(y_true, y_pred, zero_division=0)
    try:
        auc = roc_auc_score(y_true, y_pred)
    except Exception:
        auc = float("nan")

    cm = confusion_matrix(y_true, y_pred)
    tn, fp, fn, tp = cm.ravel()

    print(f"\n{'='*55}")
    print(f"  {label} Evaluation")
    print(f"{'='*55}")
    print(f"  Precision : {precision:.4f}  ({precision*100:.1f}%)")
    print(f"  Recall    : {recall:.4f}  ({recall*100:.1f}%)")
    print(f"  F1 Score  : {f1:.4f}")
    print(f"  ROC-AUC   : {auc:.4f}")
    print(f"  TP={tp}  FP={fp}  TN={tn}  FN={fn}")
    print(f"  False Positive Rate: {fp/(fp+tn)*100:.1f}%  (genuine merchants incorrectly flagged)")

    return {
        "label": label,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "auc": round(auc, 4) if not np.isnan(auc) else None,
        "tp": int(tp), "fp": int(fp), "tn": int(tn), "fn": int(fn),
    }


def compute_chargeback_lifecycle(chargebacks):
    final = chargebacks[chargebacks["is_final_stage"] == 1].copy()

    stage_order = ["retrieval_request", "first_chargeback", "representment", "pre_arbitration", "arbitration"]
    stage_metrics = chargebacks.groupby("stage").agg(
        records=("chargeback_id", "count"),
        avg_days=("chargeback_id", lambda x: chargebacks.loc[x.index, "deadline_date"].sub(
            chargebacks.loc[x.index, "stage_date"]).dt.days.mean()),
        total_loss=("loss_amount", "sum"),
        total_arb_fees=("arbitration_fee", "sum"),
    ).reset_index()

    win_by_stage = chargebacks[chargebacks["is_final_stage"] == 1].groupby("stage").apply(
        lambda g: pd.Series({
            "won": (g["outcome"] == "won").sum(),
            "lost": (g["outcome"] == "lost").sum(),
        })
    ).reset_index()

    overall = {
        "total_cases": int(final.shape[0]),
        "won_cases": int((final["outcome"] == "won").sum()),
        "lost_cases": int((final["outcome"] == "lost").sum()),
        "pending_cases": int((final["outcome"] == "pending").sum()),
        "total_loss_usd": round(final["loss_amount"].sum(), 2),
        "total_arb_fees_usd": round(chargebacks["arbitration_fee"].sum(), 2),
        "win_rate_pct": round((final["outcome"] == "won").mean() * 100, 2),
        "recovery_rate_pct": round((final["outcome"] == "won").mean() * 100, 2),
        "avg_disputed_amount": round(final["disputed_amount"].mean(), 2),
    }

    reason_metrics = final.groupby(["reason_code", "reason_description", "chargeback_type"]).agg(
        total_cases=("chargeback_id", "count"),
        won=("outcome", lambda x: (x == "won").sum()),
        lost=("outcome", lambda x: (x == "lost").sum()),
        total_loss=("loss_amount", "sum"),
    ).reset_index()
    reason_metrics["win_rate_pct"] = round(reason_metrics["won"] / reason_metrics["total_cases"] * 100, 1)

    return overall, stage_metrics, reason_metrics


def plot_chargeback_ratio_by_merchant(metrics):
    top = metrics.nlargest(15, "chargeback_ratio").copy()
    top["chargeback_ratio_pct"] = top["chargeback_ratio"] * 100

    fig, ax = plt.subplots(figsize=(12, 6))
    colors = [PALETTE["danger"] if hr else PALETTE["primary"] for hr in top["is_high_risk"]]
    bars = ax.barh(top["merchant_name"], top["chargeback_ratio_pct"], color=colors)

    ax.axvline(x=1.0, color=PALETTE["warning"], linestyle="--", linewidth=1.5, label="Visa threshold (1%)")
    ax.axvline(x=1.5, color=PALETTE["danger"], linestyle=":", linewidth=1.5, label="Mastercard threshold (1.5%)")

    ax.set_xlabel("Chargeback Ratio (%)", labelpad=10)
    ax.set_title("Chargeback Ratio by Merchant (Top 15)", pad=15)
    ax.legend(loc="lower right")
    ax.grid(axis="x")
    ax.invert_yaxis()
    fig.tight_layout()
    path = os.path.join(CHARTS_DIR, "chargeback_ratio_by_merchant.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return path


def plot_fraud_loss_overview(chargebacks):
    monthly = chargebacks[chargebacks["is_final_stage"] == 1].copy()
    monthly["month"] = monthly["stage_date"].dt.to_period("M")
    monthly_loss = monthly.groupby("month")["loss_amount"].sum().reset_index()
    monthly_loss["month_str"] = monthly_loss["month"].astype(str)

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    ax = axes[0]
    ax.bar(monthly_loss["month_str"], monthly_loss["loss_amount"], color=PALETTE["danger"], alpha=0.85)
    ax.set_title("Monthly Fraud Loss (USD)")
    ax.set_xlabel("Month")
    ax.set_ylabel("Loss (USD)")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x:,.0f}"))
    ax.tick_params(axis="x", rotation=45)
    ax.grid(axis="y")

    final = chargebacks[chargebacks["is_final_stage"] == 1]
    outcome_counts = final["outcome"].value_counts()
    colors_pie = [PALETTE["success"], PALETTE["danger"], PALETTE["warning"]]
    ax2 = axes[1]
    wedges, texts, autotexts = ax2.pie(
        outcome_counts.values,
        labels=outcome_counts.index,
        autopct="%1.1f%%",
        colors=colors_pie[:len(outcome_counts)],
        startangle=90,
    )
    for t in autotexts:
        t.set_color(PALETTE["text"])
    ax2.set_title("Chargeback Outcome Distribution")

    fig.tight_layout()
    path = os.path.join(CHARTS_DIR, "fraud_loss_overview.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return path


def plot_reason_code_breakdown(chargebacks):
    final = chargebacks[chargebacks["is_final_stage"] == 1]
    rc = final.groupby("reason_code")["loss_amount"].sum().reset_index().sort_values("loss_amount", ascending=False)

    fig, ax = plt.subplots(figsize=(10, 5))
    bars = ax.bar(rc["reason_code"], rc["loss_amount"], color=PALETTE["warning"], alpha=0.9)
    ax.set_title("Total Loss Amount by Reason Code")
    ax.set_xlabel("Reason Code")
    ax.set_ylabel("Total Loss (USD)")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x:,.0f}"))
    ax.tick_params(axis="x", rotation=20)
    ax.grid(axis="y")
    fig.tight_layout()
    path = os.path.join(CHARTS_DIR, "reason_code_breakdown.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return path


def plot_risk_score_distribution(transactions, rule_flagged, iso_flagged):
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    ax = axes[0]
    fraud = transactions[transactions["is_fraud"] == 1]["amount"]
    legit = transactions[transactions["is_fraud"] == 0]["amount"]
    ax.hist(np.log1p(legit), bins=50, color=PALETTE["primary"], alpha=0.6, label="Legitimate")
    ax.hist(np.log1p(fraud), bins=50, color=PALETTE["danger"], alpha=0.7, label="Fraud")
    ax.set_title("Transaction Amount Distribution (log scale)")
    ax.set_xlabel("log(1 + Amount)")
    ax.set_ylabel("Frequency")
    ax.legend()
    ax.grid(axis="y")

    ax2 = axes[1]
    if "anomaly_score_normalized" in iso_flagged.columns:
        fraud_scores = iso_flagged[iso_flagged["is_fraud"] == 1]["anomaly_score_normalized"]
        legit_scores = iso_flagged[iso_flagged["is_fraud"] == 0]["anomaly_score_normalized"]
        ax2.hist(legit_scores, bins=50, color=PALETTE["primary"], alpha=0.6, label="Legitimate")
        ax2.hist(fraud_scores, bins=50, color=PALETTE["danger"], alpha=0.7, label="Fraud")
        ax2.set_title("Isolation Forest Anomaly Score Distribution")
        ax2.set_xlabel("Normalized Anomaly Score (higher = more anomalous)")
        ax2.set_ylabel("Frequency")
        ax2.legend()
        ax2.grid(axis="y")

    fig.tight_layout()
    path = os.path.join(CHARTS_DIR, "risk_score_distribution.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return path


def plot_recovery_rate_by_stage(chargebacks):
    final = chargebacks[chargebacks["is_final_stage"] == 1]
    stage_order = ["first_chargeback", "representment", "pre_arbitration", "arbitration"]
    stage_win = []
    for stage in stage_order:
        sub = final[final["stage"] == stage]
        if len(sub) == 0:
            continue
        win_rate = (sub["outcome"] == "won").mean() * 100
        stage_win.append({"stage": stage, "win_rate_pct": win_rate, "n": len(sub)})

    df_stage = pd.DataFrame(stage_win)
    fig, ax = plt.subplots(figsize=(9, 5))
    bars = ax.bar(df_stage["stage"], df_stage["win_rate_pct"], color=PALETTE["success"], alpha=0.85)
    for bar, row in zip(bars, df_stage.itertuples()):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.5,
                f"n={row.n}", ha="center", va="bottom", fontsize=9)
    ax.set_title("Win Rate by Chargeback Stage")
    ax.set_xlabel("Stage")
    ax.set_ylabel("Win Rate (%)")
    ax.set_ylim(0, 100)
    ax.grid(axis="y")
    fig.tight_layout()
    path = os.path.join(CHARTS_DIR, "recovery_rate_by_stage.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return path


def plot_top_risk_merchants(metrics):
    top = metrics.nlargest(10, "composite_risk_score")[
        ["merchant_name", "composite_risk_score", "is_high_risk"]
    ].copy()

    fig, ax = plt.subplots(figsize=(10, 6))
    colors = [PALETTE["danger"] if hr else PALETTE["warning"] for hr in top["is_high_risk"]]
    ax.barh(top["merchant_name"], top["composite_risk_score"], color=colors)
    ax.set_title("Top 10 Merchants by Composite Risk Score")
    ax.set_xlabel("Risk Score")
    ax.grid(axis="x")
    ax.invert_yaxis()
    fig.tight_layout()
    path = os.path.join(CHARTS_DIR, "top_risk_merchants.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return path


def plot_flag_comparison(rule_eval, iso_eval):
    metrics_labels = ["Precision", "Recall", "F1"]
    rule_vals = [rule_eval["precision"], rule_eval["recall"], rule_eval["f1"]]
    iso_vals = [iso_eval["precision"], iso_eval["recall"], iso_eval["f1"]]

    x = np.arange(len(metrics_labels))
    width = 0.35

    fig, ax = plt.subplots(figsize=(8, 5))
    bars1 = ax.bar(x - width / 2, rule_vals, width, label="Rule-Based", color=PALETTE["primary"], alpha=0.9)
    bars2 = ax.bar(x + width / 2, iso_vals, width, label="Isolation Forest", color=PALETTE["warning"], alpha=0.9)

    for bar in bars1 + bars2:
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.01,
                f"{bar.get_height():.2f}", ha="center", va="bottom", fontsize=9)

    ax.set_xticks(x)
    ax.set_xticklabels(metrics_labels)
    ax.set_ylim(0, 1.15)
    ax.set_title("Rule-Based vs Isolation Forest: Precision, Recall, F1")
    ax.set_ylabel("Score")
    ax.legend()
    ax.grid(axis="y")
    fig.tight_layout()
    path = os.path.join(CHARTS_DIR, "flag_comparison.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return path


def print_table(df, title, max_rows=15):
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}")
    print(tabulate(df.head(max_rows), headers="keys", tablefmt="grid", showindex=False, floatfmt=".2f"))


def main():
    print("\nLoading datasets...")
    merchants, customers, transactions, refunds, chargebacks = load_data()

    print(f"\nDataset Summary:")
    print(f"  Merchants    : {len(merchants):,}")
    print(f"  Customers    : {len(customers):,}")
    print(f"  Transactions : {len(transactions):,}")
    print(f"    - Fraud    : {transactions['is_fraud'].sum():,} ({transactions['is_fraud'].mean()*100:.1f}%)")
    print(f"    - Approved : {(transactions['status']=='approved').sum():,}")
    print(f"    - Declined : {(transactions['status']=='declined').sum():,}")
    print(f"  Refunds      : {len(refunds):,}")
    print(f"  Chargeback records: {len(chargebacks):,}")

    print("\nComputing merchant risk metrics...")
    metrics = compute_merchant_metrics(transactions, chargebacks, merchants)
    metrics.to_csv(f"{OUTPUT_DIR}/merchant_risk_metrics.csv", index=False)
    print_table(
        metrics.nlargest(15, "composite_risk_score")[
            ["merchant_name", "category", "is_high_risk", "chargeback_ratio",
             "decline_rate", "refund_rate", "composite_risk_score", "total_loss"]
        ],
        "Top 15 Merchants by Risk Score",
    )

    print("\nBuilding rule-based flags...")
    rule_flagged = build_rule_based_flags(transactions)
    rule_flagged.to_csv(f"{OUTPUT_DIR}/rule_flags.csv", index=False)
    rule_eval = evaluate_flags(rule_flagged, label_col="is_fraud", pred_col="rule_flag", label="Rule-Based Flags")

    print("\nBuilding Isolation Forest anomaly flags...")
    iso_flagged = build_isolation_forest_flags(transactions, contamination=0.08)
    iso_flagged.to_csv(f"{OUTPUT_DIR}/iso_flags.csv", index=False)
    iso_eval = evaluate_flags(iso_flagged, label_col="is_fraud", pred_col="iso_anomaly", label="Isolation Forest")

    print("\nComputing chargeback lifecycle metrics...")
    lifecycle_overall, stage_metrics, reason_metrics = compute_chargeback_lifecycle(chargebacks)
    print(f"\n  Overall Chargeback Summary:")
    for k, v in lifecycle_overall.items():
        print(f"    {k:30s}: {v}")

    print_table(
        reason_metrics.sort_values("total_loss", ascending=False)[
            ["reason_code", "chargeback_type", "total_cases", "won", "lost", "win_rate_pct", "total_loss"]
        ],
        "Loss and Win Rate by Reason Code",
    )

    print("\nGenerating charts...")
    plot_chargeback_ratio_by_merchant(metrics)
    plot_fraud_loss_overview(chargebacks)
    plot_reason_code_breakdown(chargebacks)
    plot_risk_score_distribution(transactions, rule_flagged, iso_flagged)
    plot_recovery_rate_by_stage(chargebacks)
    plot_top_risk_merchants(metrics)
    plot_flag_comparison(rule_eval, iso_eval)
    print(f"  Charts saved to {CHARTS_DIR}/")

    results = {
        "generated_at": datetime.now().isoformat(),
        "dataset": {
            "merchants": len(merchants),
            "customers": len(customers),
            "transactions": len(transactions),
            "fraud_transactions": int(transactions["is_fraud"].sum()),
            "fraud_rate_pct": round(transactions["is_fraud"].mean() * 100, 2),
            "refunds": len(refunds),
            "chargeback_records": len(chargebacks),
        },
        "rule_based_evaluation": rule_eval,
        "isolation_forest_evaluation": iso_eval,
        "chargeback_lifecycle": lifecycle_overall,
        "top_risk_merchants": metrics.nlargest(5, "composite_risk_score")[
            ["merchant_id", "merchant_name", "composite_risk_score", "chargeback_ratio", "total_loss"]
        ].to_dict(orient="records"),
    }

    with open(RESULTS_FILE, "w") as f:
        json.dump(results, f, indent=2, default=str)

    print(f"\nResults saved to {RESULTS_FILE}")
    print("\nAnalysis complete.")


if __name__ == "__main__":
    main()
