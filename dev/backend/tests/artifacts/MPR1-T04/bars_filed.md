# MPR1-T04 BARS — FILED BEFORE THE CODE (2026-08-14)

Filed first, per brief section TASK.1. No route/service code existed when this was written;
`app/api/v1/routes/tray.py`, `app/services/tray_messages.py` and `app/services/allowlist.py`
were all created AFTER this file. Every bar below is realised in
`dev/backend/tests/test_tray_slots.py` with the bar id in the test name.

All bars run against a MOCKED sidecar (`_FakeAsyncClient`, mirroring the
`tests/test_pill_v2.py` idiom). No service is started; :8100 / :8101 are never contacted.

| Bar | Name | Asserts |
|-----|------|---------|
| B01 | slot_mapping_well_k_to_slot_k_plus_1 | all six wells 0..5 emit slot 1..6, in order, `well` echoed |
| B02 | verdict_verify_message | decision verify -> key `tray.slot.verify`, alert `ok`, matched_din canonical, terminal False |
| B03 | verdict_reject_message | decision reject -> key `tray.slot.reject`, alert `danger`, matched_din None |
| B04 | verdict_abstain_ask_to_flip_message | abstain+ask_to_flip -> key `tray.slot.abstain.ask_to_flip`, action `flip_reshoot`, never collapses to reject |
| B05 | verdict_abstain_shortlist_message | abstain+shortlist -> key `tray.slot.abstain.shortlist`, action `shortlist` |
| B06 | verdict_abstain_bare_message | abstain+abstain_action=None -> key `tray.slot.abstain`, action `retry` |
| B07 | occupied_with_error_isolated | one well's `error` set -> that slot verdict `error`, key `tray.slot.error`; siblings unaffected; HTTP 200 |
| B08 | unoccupied_slot_message | occupied False -> verdict `empty`, key `tray.slot.empty`, no Analysis row |
| B09 | none_faces_retry_route_default | every face presence NONE -> key `tray.presence.none_retry` (PROVISIONAL), terminal False, action `flip_reshoot` (Muthu call 3) |
| B10 | none_faces_terminal_route_param | `none_route=terminal` -> key `pill.presence.none`, terminal True, action `ask_pharmacist` |
| B11 | unreadable_faces_message | UNREADABLE face -> key `pill.presence.unreadable`, params faces_seen + unseen_face_possible |
| B12 | token_form_regression_padded_and_bare | profile DINs "00013803" and "13803" BOTH reach the sidecar mock as `DIN13803` (din_utils.to_sb2_token) |
| B13 | excluded_din_never_sent_and_notice_emitted | excluded DIN2306409 absent from sidecar payload; `pill.scope.unsupported_note` note emitted with counts |
| B14 | all_unsupported_profile_short_circuits | profile of only excluded DINs -> sidecar NEVER constructed, `pill.scope.unsupported`, terminal True |
| B15 | empty_profile_short_circuits | no confirmed DINs -> sidecar NEVER constructed, `pill.scope.no_profile`, terminal True |
| B16 | frame_level_4xx_passthrough | sidecar 422 {"error":...} -> same status + body passed through verbatim |
| B17 | per_slot_persistence_n_rows | N occupied slots -> N Analysis rows, each tagged tray/slot in label_info; empty wells persist nothing |
| B18 | requires_auth | unauthenticated POST -> 403 |
| B19 | sidecar_unreachable_503 | httpx.ConnectError -> 503 BRAINS_UNAVAILABLE |
| B20 | allowlist_integrity_11_supported_4_excluded | promoted CSV yields 11 supported, 4 excluded, and the four named excluded DINs |
| B21 | pharmacist_hedge_present_on_every_slot | every slot carries a non-empty `pharmacist_hedge` (Muthu call 2) |
| B22 | slot_count_always_six | short frame from the sidecar still yields exactly 6 slots |

## MUTATION TEST (3 injected defects -> 3 reds)

| Mut | Injected defect | Bar that must go red |
|-----|-----------------|----------------------|
| M1 | `slot = well` (drop the +1) in tray.py | B01 |
| M2 | send the UNFILTERED profile to the sidecar (skip the allowlist filter) | B13 |
| M3 | ignore `none_route` and always route NONE to the terminal message | B09 |

Runner: `tests/mutation_t04.py`. Reds captured to `red_M1.txt` / `red_M2.txt` / `red_M3.txt`
in this directory. The runner restores the pristine source in a `finally` block and verifies the
sha256 matches before exiting.

## D-7 BARS — FILED AFTER MUTHU'S RULING, BEFORE THE DOWNGRADE CODE (2026-08-14)

Decision D-7 (Muthu, binding) closes the question T04's report left open as deviation (4):
a slot whose record fails C6 validation must NEVER carry verdict `verify`. These three bars were
written and RUN RED before `slot_verdict`'s downgrade branch existed.

| Bar | Name | Asserts |
|-----|------|---------|
| D7a | contract_error_downgrades_sb2_verify | invalid record + SB2 `verify` -> verdict `error`, matched_din/breakdown None, decision "verify" still recorded, action `ask_pharmacist`, alert `warning` |
| D7b | contract_error_downgrades_sb2_reject | invalid record + SB2 `reject` -> verdict `error` too. UNIFORM: the downgrade must not vary with the decision, or the verdict itself leaks what the invalid record said |
| D7c | valid_record_still_verifies | the control -- a well-formed C6 record with SB2 `verify` is untouched, so the rule cannot be satisfied by breaking verify everywhere |

| Mut | Injected defect | Bar that must go red |
|-----|-----------------|----------------------|
| M4 | skip the downgrade branch entirely | D7a |

