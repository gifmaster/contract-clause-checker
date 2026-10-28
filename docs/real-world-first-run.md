| Document | Kind | Missed (FN) | Wrongly flagged (FP) | Clauses found | Other |
|---|---|---|---|---|---|
| commonpaper_cloud_service_agreement_v1.txt | main | - | missing_governing_law, no_liability_cap, transfer_without_safeguards | 6/7 | DPA elsewhere: got False, want True |
| bonterms_cloud_terms_v1.txt | main | auto_renewal | missing_confidentiality, missing_governing_law, missing_liability | 1/8 | DPA elsewhere: got False, want True |
| github_corporate_terms.txt | main | unilateral_changes, vendor_may_end_anytime | missing_confidentiality, missing_governing_law, missing_liability, no_dpa, transfer_without_safeguards | 1/5 | DPA elsewhere: got False, want True |
| commonpaper_ai_addendum_v1.txt | addendum | ai_training_on_data | - | 0/0 | - |
| commonpaper_dpa_v1.txt | dpa | - | missing_confidentiality, missing_governing_law, missing_termination, no_liability_cap, non_eu_law | 0/0 | Recognised as DPA: got False, want True; GDPR pack FN - FP ['gdpr_subprocessor_flowdown'] |
| bonterms_dpa_v1.txt | dpa | - | missing_governing_law, missing_liability, non_eu_law, vendor_may_end_anytime | 0/0 | Recognised as DPA: got False, want True; GDPR pack FN - FP ['gdpr_processing_details', 'gdpr_subprocessor_flowdown'] |
| 13_cloudharbor_msa_US_EN.txt | main | auto_renewal, short_liability_cap, transfer_without_safeguards, vendor_may_end_anytime | missing_termination, no_liability_cap | 5/5 | DPA elsewhere: got False, want True |

Core checks: precision 0.21 (6 right, 22 wrongly flagged), recall 0.43 (8 missed)
GDPR pack on the two real DPAs: precision 0.50, recall 1.00 (FP 3, FN 0)
Clause detection: 13 of 25
