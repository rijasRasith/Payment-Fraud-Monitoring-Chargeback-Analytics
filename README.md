# Payment Fraud Monitoring & Chargeback Analytics

> **IMPORTANT: All data in this repository is entirely synthetic and was generated programmatically using a fixed random seed. It does not represent any real transactions, merchants, customers, or financial events.**

---

## Problem Statement

Payment fraud and chargeback disputes are among the costliest operational challenges for acquiring banks and payment processors. Merchants operating in high-risk categories can breach Visa's 1% or Mastercard's 1.5% chargeback ratio thresholds within months of onboarding, triggering remediation programs (VFMP, MATCH listing) that can permanently terminate their processing privileges. Risk and fraud operations teams must simultaneously:

- Monitor merchant-level transaction patterns for early fraud signals
- Detect anomalous individual transactions before they result in chargebacks
- Track every chargeback through its five-stage dispute lifecycle
- Measure recovery rates and identify which reason codes and merchants cause disproportionate losses
- Prioritise analyst effort across hundreds of open dispute tickets

This project simulates the complete workflow of a risk team: from raw transaction data to anomaly detection, chargeback lifecycle modelling, dashboard-ready analytics, and dispute case management.

---

## Repository Structure

```
Payment-Fraud-Monitoring-Chargeback-Analytics/
│
├── generate_data.py                  # Synthetic dataset generator (fixed seed)
├── load_to_mysql.py                  # Schema creation + CSV loader + DQ checks
├── run_all.py                        # End-to-end orchestration script
├── .gitignore
│
├── data/                             # Generated CSV files (git-ignored)
│   ├── merchants.csv
│   ├── customers.csv
│   ├── transactions.csv
│   ├── refunds.csv
│   └── chargebacks.csv
│
├── sql/
│   ├── schema.sql                    # MySQL DDL with FK constraints and indexes
│   └── monitoring_queries.sql        # All 13 monitoring and analytics queries
│
├── analysis/
│   ├── run_analysis.py               # Risk flags, anomaly scoring, charts
│   └── generate_results_notes.py     # Formats results + resume bullets
│
├── outputs/                          # Generated outputs (git-ignored)
│   ├── merchant_risk_metrics.csv
│   ├── rule_flags.csv
│   ├── iso_flags.csv
│   ├── results.json
│   ├── results_notes.md
│   └── charts/
│       ├── chargeback_ratio_by_merchant.png
│       ├── fraud_loss_overview.png
│       ├── reason_code_breakdown.png
│       ├── risk_score_distribution.png
│       ├── recovery_rate_by_stage.png
│       ├── top_risk_merchants.png
│       └── flag_comparison.png
│
└── docs/
    ├── domain_notes.md               # Chargeback domain knowledge (Day 1 notes)
    ├── recommendations.md            # 6 data-backed process improvements
    └── freshdesk_workflow.md         # 15 sample dispute tickets + reply templates
```

---

## How to Run

### Prerequisites

```bash
pip install pandas numpy scikit-learn mysql-connector-python sqlalchemy faker matplotlib seaborn tabulate
```

MySQL must be running locally. Set credentials via environment variables if they differ from the defaults (`root` / empty password):

```powershell
$env:DB_USER = "your_user"
$env:DB_PASSWORD = "your_password"
```

### Step 1 — Generate the synthetic dataset

```bash
python generate_data.py
```

Produces five CSVs in `data/` with a fixed seed for full reproducibility.

### Step 2 — Load into MySQL

```bash
python load_to_mysql.py
```

Creates the `fraud_analytics` database, applies `sql/schema.sql`, loads all tables in FK-safe order, and runs data-quality checks.

### Step 3 — Run the full analysis

```bash
python -X utf8 analysis/run_analysis.py
```

Outputs: merchant risk metrics CSV, rule flag CSV, Isolation Forest flag CSV, `results.json`, and 7 charts in `outputs/charts/`.

### Step 4 — Generate results notes

```bash
python -X utf8 analysis/generate_results_notes.py
```

Prints a formatted results summary and saves `outputs/results_notes.md` with resume-ready bullet points.

### One-command run (Steps 1 + 3 + 4 only, no MySQL required)

```bash
python -X utf8 run_all.py
```

---

## Data Description

| Table          | Rows  | Description                                                                 |
|----------------|-------|-----------------------------------------------------------------------------|
| `merchants`    | 20    | Name, category, MCC code, country, high-risk flag                           |
| `customers`    | 500   | Name, email, card type, billing country                                     |
| `transactions` | 5,127 | Amount, status, datetime, hour, IP/billing country, location mismatch, fraud label |
| `refunds`      | 243   | Linked to refunded transactions with reason and date                        |
| `chargebacks`  | 740   | One row per lifecycle stage per case; reason code, outcome, loss, arb fees  |

### Injected Fraud Patterns

Four distinct patterns were deliberately embedded to simulate real-world fraud:

1. **Rapid-repeat bursts** — 15 clusters of 5–12 transactions from the same customer at the same merchant within 30 minutes (card-testing and account-takeover simulation)
2. **High-value outliers** — 60 transactions ranging $2,000–$15,000 concentrated at the two high-risk merchants (Gambling, Crypto Exchange)
3. **Unusual-hour transactions** — 80 transactions processed between 2–5 AM with location mismatches
4. **Card-testing sequences** — 30 customers generating 4–8 consecutive declines followed by a successful approval

Merchants 3 and 7 were designated as high-risk at generation time and received elevated fraud injection, higher decline rates, and more chargebacks.

---

## Key Findings

### Merchant Risk Ranking

The composite risk score (decline rate × 25 + refund rate × 20 + location mismatch rate × 25 + chargeback ratio × 300 + high-risk flag × 10) ranked the two injected high-risk merchants in the top two positions, validating the scoring approach.

| Merchant (top 3)         | Category        | CB Ratio | Decline Rate | Risk Score | Total Loss   |
|--------------------------|-----------------|----------|--------------|------------|--------------|
| High-risk merchant #1    | Gambling        | ~16%     | 27%          | 91.3       | $152,471     |
| High-risk merchant #2    | Crypto Exchange | ~12%     | 32%          | ~80        | ~$50,000     |
| Next-highest (non-fraud) | Various         | <3%      | <20%         | <70        | <$5,000      |

Both high-risk merchants significantly exceeded Visa's 1% and Mastercard's 1.5% chargeback ratio thresholds.

### Flag Precision and Recall

| Signal           | Precision | Recall | F1    | ROC-AUC | FP Rate |
|------------------|-----------|--------|-------|---------|---------|
| Rule-Based       | 0.09      | 1.00   | 0.16  | 0.50    | 99.4%   |
| Isolation Forest | 0.36      | 0.33   | 0.35  | 0.64    | 5.6%    |
| **Combined**     | —         | —      | —     | —       | Lower FP with higher recall than ISO alone |

**Trade-off analysis:** The rule-based flags achieve perfect recall — every injected fraud transaction is caught — but at the cost of flagging 99.4% of legitimate transactions as suspicious. This makes them unsuitable as a standalone blocking mechanism but highly valuable as a first-pass triage layer. The Isolation Forest achieves a much lower false-positive rate (5.6%) while still catching one-third of all fraud, with a ROC-AUC of 0.64 demonstrating meaningful discriminatory power beyond random chance.

**Recommendation:** Use rules as a monitoring alert (not a block) and Isolation Forest as the primary anomaly signal for analyst queuing, reserving manual review for transactions where both signals agree.

### Chargeback Lifecycle Metrics

| Metric                   | Value       |
|--------------------------|-------------|
| Total finalized cases    | 290         |
| Won (via representment)  | 63 (21.7%)  |
| Lost                     | 195 (67.2%) |
| Pending                  | 32 (11.0%)  |
| Overall win rate         | 21.72%      |
| Total chargeback loss    | $282,695.52 |
| Total arbitration fees   | $43,923.20  |
| Avg disputed amount      | $1,486.60   |

### Loss by Reason Code

| Reason Code | Type      | Cases | Win Rate | Total Loss   |
|-------------|-----------|-------|----------|--------------|
| MC_4863     | Fraud     | 62    | 17.7%    | $128,437.66  |
| VISA_10.4   | Fraud     | 55    | 16.4%    | $65,018.91   |
| MC_4837     | Fraud     | 47    | 12.8%    | $58,126.19   |
| VISA_10.5   | Fraud     | 46    | 23.9%    | $27,490.43   |
| MC_4855     | Technical | 25    | 36.0%    | $1,569.11    |
| MC_4853     | Technical | 19    | 10.5%    | $1,027.81    |
| VISA_12.1   | Technical | 22    | 40.9%    | $794.09      |
| VISA_12.6   | Technical | 14    | 42.9%    | $231.32      |

Fraud reason codes account for 97.7% of total loss despite being 72% of cases. Technical chargebacks have meaningfully higher win rates (36–43%) compared to fraud codes (12–24%).

### Recovery Rate by Stage

Win rates decline sharply as cases escalate:
- **Representment:** ~45% win rate
- **Pre-arbitration:** ~25% win rate
- **Arbitration:** ~15% win rate

This confirms that early evidence collection and rapid representment response are the highest-ROI interventions in the dispute lifecycle.

---

## Power BI Dashboard

The analysis produces 7 chart files that map directly to Power BI dashboard pages:

| Chart File                            | Dashboard Section               |
|---------------------------------------|---------------------------------|
| `fraud_loss_overview.png`             | Fraud Loss Overview             |
| `chargeback_ratio_by_merchant.png`    | Chargeback Ratio Trend          |
| `recovery_rate_by_stage.png`          | Recovery Rate by Stage          |
| `top_risk_merchants.png`              | Top-Risk Merchants              |
| `reason_code_breakdown.png`           | Reason-Code Breakdown           |
| `risk_score_distribution.png`         | Anomaly Score Distribution      |
| `flag_comparison.png`                 | Rule vs ML Signal Comparison    |

To build the full Power BI report: import `merchant_risk_metrics.csv`, `rule_flags.csv`, `iso_flags.csv`, and the `chargebacks.csv` as data sources and connect the chart visuals using `merchant_id` as the relationship key.

---

## Freshdesk Case Workflow

See [`docs/freshdesk_workflow.md`](docs/freshdesk_workflow.md) for:
- Full setup instructions (custom fields, agent groups, SLA rules)
- 15 sample dispute tickets covering all 8 reason codes across all lifecycle stages
- Merchant-facing reply templates for fraud and technical chargeback types
- Escalation rules for arbitration-stage cases and VFMP monitoring alerts

---

## Recommendations

Six data-backed process improvement recommendations are documented in [`docs/recommendations.md`](docs/recommendations.md):

1. **Tighten merchant onboarding thresholds** for high-risk MCC categories (rolling reserves from day one)
2. **Automate early evidence collection** triggered at authorization for high-risk-score transactions
3. **Implement real-time velocity controls** (soft-decline after 3 approvals/30 min) with 3DS step-up
4. **Define an economic arbitration threshold** (~$350) below which accepting the loss is net-positive
5. **Deploy tiered merchant monitoring** using composite risk scores (Tier 1 weekly / Tier 2 monthly / Tier 3 quarterly)
6. **Pre-approve rebuttal templates** per reason code to reduce preparation time from 2–3 hours to under 30 minutes

---

## Limitations

- All data is synthetic. Fraud patterns, amounts, and ratios were chosen to be illustrative, not calibrated to real industry distributions.
- The Isolation Forest model uses only three features (amount, hour, location mismatch). A production model would incorporate device fingerprinting, velocity features, graph-based merchant/customer relationships, and historical dispute outcomes.
- Rule-based flags were not tuned for precision — they serve as a recall-maximizing triage layer, not a precision-optimised blocking mechanism.
- MySQL loading requires a local MySQL instance. The analysis pipeline (Steps 1, 3, 4) runs without MySQL.
- Power BI screenshots are represented by the PNG chart files in `outputs/charts/`. Full `.pbix` file construction requires Power BI Desktop.

---

## Interview Preparation Notes

See [`docs/domain_notes.md`](docs/domain_notes.md) for full domain reference. Quick answers:

**Q: Walk me through the chargeback stages.**  
Retrieval request → First chargeback → Representment → Pre-arbitration → Arbitration. Each stage has a 15–45 day response window. Arbitration costs $500–$600 in network fees regardless of outcome.

**Q: How do your rules differ from the Isolation Forest, and why use both?**  
Rules are deterministic, interpretable thresholds (e.g., "flag if 3+ transactions in 30 minutes"). They achieve high recall but terrible precision (FPR 99.4%). Isolation Forest is an unsupervised ML method that scores how anomalous a transaction is relative to the distribution — it achieves lower recall (33%) but far better precision (36%) and a 5.6% FPR. Combined, rules surface everything for awareness while ISO prioritises which cases warrant immediate analyst action.

**Q: What do precision and recall mean here?**  
Precision = of all transactions we flag, what fraction are actually fraud. Recall = of all actual fraud transactions, what fraction do we catch. High recall is critical when missing fraud is costly (it escapes detection entirely). High precision matters because false positives harm genuine merchants — freezing a legitimate merchant's payouts damages the relationship and can trigger legal disputes.

**Q: One finding and the process change you recommended.**  
Win rates drop from ~45% at representment to ~15% at arbitration. The process change: trigger automated evidence collection at the moment of authorization for any transaction scoring above the 85th percentile on the composite risk model. Pre-built evidence packages reduce representment preparation time and improve the quality of submissions, shifting more cases toward early-stage resolution.

**Q: How would you speak to a merchant disputing a payout hold?**  
"I understand this creates cash-flow pressure and I want to resolve it as quickly as possible. Your account has been flagged because your chargeback ratio has reached [X]%, which approaches the threshold where our acquiring partner requires us to act. I'd like to walk you through the specific transactions involved and discuss what evidence we can collect to support your representment. In the meantime, here is what the hold covers and here is the timeline for review. My goal is to get this lifted as soon as the risk justifies it."
