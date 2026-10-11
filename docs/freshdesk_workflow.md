# Freshdesk Dispute Case Workflow

## Setup

1. Create a free Freshdesk account at https://freshdesk.com/signup
2. Set the helpdesk name to **FraudOps Dispute Center**
3. Create the following custom ticket fields:
   - `Merchant ID` (text)
   - `Transaction ID` (text)
   - `Disputed Amount` (decimal)
   - `Reason Code` (dropdown: VISA_10.4, VISA_10.5, VISA_12.1, VISA_12.6, MC_4837, MC_4853, MC_4855, MC_4863)
   - `Chargeback Stage` (dropdown: retrieval_request, first_chargeback, representment, pre_arbitration, arbitration)
   - `Deadline Date` (date)
4. Create agent groups: `Fraud Review Team`, `Merchant Relations`
5. Create ticket priorities: Low, Medium, High, Urgent

---

## Sample Dispute Tickets

### Ticket #001
**Subject:** VISA_10.4 Chargeback — Merchant ID 3 — TXN #4821 — $3,450.00  
**Priority:** Urgent  
**Status:** Open  
**Assigned to:** Fraud Review Team  
**Deadline:** 2024-03-15  
**Tags:** fraud, visa, high-value, high-risk-merchant

**Description:**  
Received first chargeback notification for TXN #4821 processed by Merchant #3 (Crypto Exchange) on 2024-02-18 for $3,450.00 under reason code VISA 10.4 (Other Fraud — Card Absent). Cardholder claims no authorization was given. Transaction shows location mismatch (IP: NG, Billing: US) and was processed at 3:42 AM local time.

**Action Required:** Pull 3DS auth logs, AVS/CVV response, device fingerprint. Prepare representment package by deadline.

---

**Merchant Reply Template (for step-up inquiry):**
> Dear [Merchant Name],  
> We are reaching out regarding chargeback case CB-001 for transaction #4821 dated February 18, 2024. The cardholder's issuing bank has filed a dispute citing unauthorized card use.  
> To support your representment, please provide within 7 business days: (1) any 3D Secure authentication confirmation, (2) your delivery or access logs confirming service was rendered, and (3) any cardholder communication acknowledging the transaction.  
> Our team is here to assist. Please reply to this ticket or call your account manager.  
> Best regards, FraudOps Dispute Team

---

### Ticket #002
**Subject:** MC_4837 Chargeback — Merchant ID 7 — TXN #2190 — $890.00  
**Priority:** High  
**Status:** In Progress  
**Assigned to:** Fraud Review Team  
**Deadline:** 2024-04-02  
**Tags:** fraud, mastercard, no-auth

**Description:**  
Mastercard 4837 (No Cardholder Authorization) filed against Merchant #7 (Gambling platform) for TXN #2190. Cardholder denies recognizing the charge. Multiple rapid-repeat transactions from same customer (6 transactions in 22 minutes) preceded this charge.

**Action Required:** Check if 3DS was enforced. Review IP logs. Flag the customer account for enhanced monitoring. Compile representment.

---

### Ticket #003
**Subject:** VISA_12.6 Duplicate Processing — Merchant ID 11 — TXN #5530 — $120.00  
**Priority:** Medium  
**Status:** Open  
**Assigned to:** Merchant Relations  
**Deadline:** 2024-05-10  
**Tags:** technical, duplicate, low-value

**Description:**  
Merchant #11 (Retail) submitted a duplicate charge of $120.00 for TXN #5530. Cardholder was billed twice for the same order. This is a technical chargeback — straightforward to resolve.

**Action Required:** Verify duplicate transaction, issue refund for second charge, submit proof of single authorization to issuer.

---

**Merchant Reply Template (duplicate charge):**
> Dear [Merchant Name],  
> We have identified that transaction #5530 was processed twice on March 28, 2024, resulting in a duplicate charge of $120.00. We will initiate a full refund for the duplicate within 3–5 business days.  
> To prevent future occurrences, please ensure your payment terminal does not retry failed authorizations without cardholder confirmation. We are happy to review your integration settings.  
> Apologies for the inconvenience. FraudOps Dispute Team

---

### Ticket #004
**Subject:** MC_4855 Non-Receipt — Merchant ID 14 — TXN #7710 — $240.00  
**Priority:** Medium  
**Status:** Pending Merchant Response  
**Assigned to:** Merchant Relations  
**Deadline:** 2024-04-28  
**Tags:** dispute, non-receipt, goods

**Description:**  
Customer filed MC 4855 claiming merchandise was never received. Merchant has not yet provided shipping confirmation or tracking number.

**Action Required:** Contact merchant for proof of delivery. If merchant cannot provide tracking, recommend accepting the chargeback to avoid escalation costs.

---

### Ticket #005
**Subject:** VISA_10.4 Pre-Arbitration — Merchant ID 3 — TXN #3302 — $5,100.00  
**Priority:** Urgent  
**Status:** Escalated  
**Assigned to:** Fraud Review Team  
**Deadline:** 2024-06-05  
**Tags:** pre-arbitration, fraud, visa, critical

**Description:**  
Issuer rejected our representment for TXN #3302 and has escalated to pre-arbitration. Disputed amount is $5,100. Arbitration fee risk is $550. Net loss if we lose at arbitration = $5,650. Review evidence package for strengthening before Visa submits to arbitration.

**Action Required:** Senior analyst review. Decision needed: proceed to arbitration or accept loss. Economic breakeven is approximately $550 recovery above loss — escalation is justified here given amount.

---

### Ticket #006
**Subject:** MC_4863 Does Not Recognize — Merchant ID 7 — TXN #6640 — $315.00  
**Priority:** High  
**Status:** Open  
**Assigned to:** Fraud Review Team  
**Deadline:** 2024-04-18  
**Tags:** fraud, mastercard, unrecognized

**Action Required:** Pull login event logs and device fingerprint at time of transaction. If different device/location than cardholder profile, prepare chargeback acceptance. If same device, prepare representment with device match evidence.

---

### Ticket #007
**Subject:** VISA_12.1 Late Presentment — Merchant ID 9 — TXN #8820 — $78.00  
**Priority:** Low  
**Status:** Resolved  
**Assigned to:** Merchant Relations  
**Deadline:** 2024-03-20 (past — resolved)  
**Tags:** technical, late-presentment, resolved

**Description:**  
Merchant submitted transaction #8820 for settlement 8 days after authorization expired. Chargeback was accepted. Merchant advised to submit within 7 days per Visa operating rules.

**Outcome:** Loss accepted. Merchant educated. No escalation.

---

### Ticket #008
**Subject:** MC_4853 Cardholder Dispute — Merchant ID 16 — TXN #9010 — $195.00  
**Priority:** Medium  
**Status:** In Progress  
**Assigned to:** Merchant Relations  
**Deadline:** 2024-05-25  
**Tags:** dispute, goods-services, mc

**Action Required:** Request merchant ToS acceptance log, fulfillment confirmation, and any cardholder communication. Prepare representment package.

---

### Ticket #009
**Subject:** VISA_10.4 Fraud — Merchant ID 3 — Burst Pattern — TXN #5500–#5506 — $1,820.00  
**Priority:** Urgent  
**Status:** Open  
**Assigned to:** Fraud Review Team  
**Deadline:** 2024-07-01  
**Tags:** fraud, burst-pattern, visa, multiple-transactions

**Description:**  
Seven transactions from Customer #241 at Merchant #3 within 18 minutes totaling $1,820. All approved. Five have now resulted in chargebacks. Pattern consistent with card testing leading to fraudulent purchases.

**Action Required:** Freeze Customer #241 account. Block future transactions at Merchant #3 from this customer. Compile consolidated representment for all five TXNs. Notify merchant of card-testing indicators.

---

### Ticket #010
**Subject:** MC_4837 First Chargeback — Merchant ID 7 — TXN #2840 — $450.00  
**Priority:** High  
**Status:** Open  
**Assigned to:** Fraud Review Team  
**Deadline:** 2024-06-15  
**Tags:** fraud, mastercard, first-chargeback

**Action Required:** Standard fraud representment flow. Collect 3DS, AVS, IP, device data. Submit within deadline.

---

### Ticket #011
**Subject:** VISA_10.4 High-Value Outlier — Merchant ID 3 — TXN #1190 — $12,300.00  
**Priority:** Urgent  
**Status:** Open  
**Assigned to:** Fraud Review Team  
**Deadline:** 2024-08-10  
**Tags:** fraud, visa, high-value, outlier

**Description:**  
Transaction amount of $12,300 is 14 standard deviations above Merchant #3 average ticket of $680. Transaction processed at 4:15 AM. Location mismatch: IP country ZA, billing country US.

**Action Required:** Immediate manual review before representment. High priority due to amount. Prepare full evidence dossier.

---

### Ticket #012
**Subject:** MC_4855 Non-Receipt — Merchant ID 18 — TXN #6210 — $88.00  
**Priority:** Low  
**Status:** Pending  
**Assigned to:** Merchant Relations  
**Deadline:** 2024-06-30  
**Tags:** dispute, non-receipt, low-value

**Action Required:** Economic assessment — total dispute amount $88. Arbitration risk $550. Recommendation: accept if merchant cannot provide delivery proof within 5 business days.

---

### Ticket #013
**Subject:** VISA_10.5 VFMP Alert — Merchant ID 3 — Monthly Review  
**Priority:** Urgent  
**Status:** Open  
**Assigned to:** Fraud Review Team  
**Deadline:** 2024-07-31  
**Tags:** vfmp, visa, remediation-program

**Description:**  
Merchant #3 has received a Visa Fraud Monitoring Program (VFMP) notification. Chargeback ratio has exceeded 0.9% for two consecutive months. If it reaches 1% for a third month, Visa will impose VFMP fines and potential network termination.

**Action Required:** Immediate merchant meeting. Review all open fraud cases. Discuss rolling reserve increase to 20%. Consider temporary transaction limit of $500 per transaction until ratio drops below 0.5%.

---

### Ticket #014
**Subject:** VISA_12.6 Duplicate — Merchant ID 5 — TXN #3390 — $55.00  
**Priority:** Low  
**Status:** Resolved  
**Assigned to:** Merchant Relations  
**Deadline:** N/A — resolved  
**Tags:** technical, duplicate, resolved

**Outcome:** Duplicate confirmed. Refund issued. Case closed. Merchant integration reviewed.

---

### Ticket #015
**Subject:** MC_4837 Arbitration Ruling Received — Merchant ID 7 — TXN #1805 — $720.00  
**Priority:** High  
**Status:** Closed — Lost  
**Assigned to:** Fraud Review Team  
**Tags:** arbitration, lost, mc

**Description:**  
Mastercard issued arbitration ruling in favor of cardholder. Merchant #7 loses $720 disputed amount plus $550 arbitration fee = $1,270 total loss.

**Outcome:** Loss recorded. Case closed. Added to merchant's cumulative loss tally. Risk threshold review triggered for Merchant #7.

---

## Workflow Notes

- All tickets with disputed amounts above $500 are escalated to **Urgent** priority and require a senior analyst review before any representment is submitted.
- Tickets approaching their deadline with no merchant response are automatically escalated via Freshdesk automation rules (SLA breach trigger).
- Losing cases at arbitration automatically trigger a merchant risk review workflow tagged with `risk-review-required`.
- Weekly Freshdesk report exported to `outputs/` as a summary CSV showing open vs closed cases, win rate, and total loss for the week.
