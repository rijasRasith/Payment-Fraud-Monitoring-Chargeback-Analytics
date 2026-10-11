# Guide: Payment Fraud Monitoring and Chargeback Dispute Analytics

Repo name: **Payment-Fraud-Monitoring-Chargeback-Analytics**
Effort: about 5 to 7 days. Tools: Python, MySQL, Power BI, Freshdesk (free plan).

## Goal
Simulate how a risk team monitors merchants, flags suspicious transactions, and handles chargebacks, then show the results in a dashboard and a case-tracking workflow.

## Steps

### 1. Learn the domain first (Day 1)
- Chargeback stages: retrieval request, first chargeback, representment, pre-arbitration, arbitration.
- Technical chargebacks versus fraud chargebacks, and the cost of reaching arbitration.
- Fraud reason-code categories (for example Visa 10.4 and Mastercard 4837) and the evidence that helps win disputes.
- Write a one-page notes file in the repo summarizing this in your own words.

### 2. Create the synthetic dataset
- Design tables: merchants, customers, transactions, refunds, disputes/chargebacks.
- Generate realistic data with a script, using a fixed seed.
- Inject known fraud patterns: rapid repeat transactions, unusually high amounts, many declines, mismatched locations, and one or two high-risk merchants.
- Link some fraudulent transactions to chargebacks with stage, reason code, dates, and outcome.
- State clearly in the README that the data is synthetic.

### 3. Load into MySQL
- Create the schema with keys and indexes, and load the data.
- Add basic data-quality checks (no orphan records, no nulls in key fields).

### 4. Write monitoring queries
- Merchant-level metrics: chargeback ratio, refund rate, decline rate, average ticket size.
- Transaction-level checks: rapid repeats, high-value outliers, unusual hours.
- A "merchants to review" query that ranks merchants by risk.

### 5. Build risk flags and anomaly scoring
- Write simple rule-based flags with thresholds.
- Add an Isolation Forest anomaly score as a second signal.
- Compare both against your injected fraud using precision and recall.
- Tune thresholds and note the false-positive trade-off.

### 6. Model the chargeback lifecycle
- Track each case through its stages with deadlines and status.
- Calculate recovery rate, win rate, loss amount, and average resolution time per stage.
- Identify which reason codes and merchants cause the most loss.

### 7. Build the Power BI dashboard
- Pages or sections: fraud loss overview, chargeback ratio trend, recovery rate, top-risk merchants, reason-code breakdown.
- Save screenshots for the README.

### 8. Run a Freshdesk case workflow
- Create a free Freshdesk account.
- Log 10 to 15 sample dispute cases as tickets with priority, status, due dates, and notes.
- Practice writing a short, polite customer or merchant reply for each type of case.
- Capture screenshots.

### 9. Write recommendations
- A short document with 4 to 6 process improvements to reduce losses (for example tighter merchant thresholds, earlier evidence collection, faster response to disputes), each backed by a finding from your data.

### 10. Document and publish
- README with: problem statement, data description, how to run, key findings, flag precision and recall, dashboard screenshots, Freshdesk screenshots, and limitations.
- Keep a `results` notes file with every real number you want on the resume.

## Checklist before updating the resume
- [ ] Synthetic dataset and MySQL schema in the repo
- [ ] Monitoring queries working
- [ ] Rules and anomaly score evaluated with precision and recall
- [ ] Chargeback lifecycle metrics calculated
- [ ] Power BI dashboard screenshots saved
- [ ] Freshdesk tickets logged
- [ ] Recommendations written
- [ ] Real numbers recorded for the resume bullets

## Interview preparation
Be ready to explain:
- The chargeback stages and why each matters.
- How your rules differ from the anomaly score, and why you used both.
- What precision and recall mean here, and the cost of false positives for genuine merchants.
- One finding from your data and the process change you recommended.
- How you would speak to a merchant who disputes a hold on their payouts.
