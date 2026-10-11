# Payment Fraud and Chargeback Domain Notes

## Chargeback Lifecycle Stages

A chargeback is a payment reversal initiated by the card-issuing bank on behalf of the cardholder.
The dispute moves through up to five escalating stages:

1. **Retrieval Request** — The issuing bank asks the merchant for transaction documentation before filing a formal dispute. Responding quickly here can prevent escalation to a full chargeback.

2. **First Chargeback** — The issuer formally reverses the transaction and debits the acquirer. The merchant has a limited window (typically 30-45 days) to respond with rebuttal evidence. If they do not respond, the case resolves in the cardholder favour.

3. **Representment** — The merchant (or their acquirer) submits a rebuttal package disputing the chargeback. Evidence includes signed receipts, AVS/CVV matches, delivery confirmation, and communication logs. If accepted, the funds are returned.

4. **Pre-Arbitration** — If the issuer rejects the representment, they may escalate to pre-arbitration. Both sides have one more opportunity to settle before Visa or Mastercard adjudicates.

5. **Arbitration** — The card network (Visa, Mastercard) makes a binding ruling. Fees for arbitration can reach $500-$600 USD regardless of outcome, making this stage extremely costly. Losing merchants face both the chargeback amount and the arbitration fee.

## Technical vs. Fraud Chargebacks

- **Fraud chargebacks** arise from unauthorized card use - stolen card numbers, account takeovers, or card-not-present attacks. Reason codes: Visa 10.4, Mastercard 4837.
- **Technical chargebacks** arise from processing errors - duplicate processing, incorrect amounts. Reason codes: Visa 12.1, Visa 12.6.

## Key Fraud Reason Codes

| Network    | Code | Description                         |
|------------|------|-------------------------------------|
| Visa       | 10.4 | Other Fraud - Card Absent           |
| Visa       | 10.5 | Visa Fraud Monitoring Program       |
| Visa       | 12.1 | Late Presentment                    |
| Visa       | 12.6 | Duplicate Processing                |
| Mastercard | 4837 | No Cardholder Authorization         |
| Mastercard | 4853 | Cardholder Dispute                  |
| Mastercard | 4855 | Non-Receipt of Merchandise          |
| Mastercard | 4863 | Cardholder Does Not Recognize       |

## Key Risk Metrics

- **Chargeback Ratio** = Chargebacks / Transactions in prior month
- **Refund Rate** = Refunds issued / Total transactions
- **Decline Rate** = Declined authorizations / Total authorization attempts
- **Recovery Rate** = Chargebacks won via representment / Total chargebacks disputed

## Common Fraud Pattern Indicators

- Rapid repeat transactions from the same card or device within minutes
- Unusually high ticket amounts compared to merchant average order value
- High decline rate followed by a successful authorization (card testing)
- Transactions at unusual hours (3-5 AM) inconsistent with business type
- Mismatched billing/shipping addresses or IP geolocation mismatch
