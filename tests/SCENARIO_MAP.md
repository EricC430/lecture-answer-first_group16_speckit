# Scenario 對應表（001-activity-session、003-round-submission、004-ranking-review）

依憲章原則 VI，spec 的每個 Acceptance Scenario 至少對應一個自動化測試；測試函式的 docstring 寫 `Scenario: USn-ASm`。本表由 `tests/` 掃描產生（2026-11-24，003 T059）。001 與 003 的編號各自獨立：003 新增的測試檔歸 003，其餘歸 001。

## 001-activity-session

| Scenario | 測試 |
|---|---|
| US1-AS1 | `tests/integration/test_us1_teacher.py::test_second_activity_gets_distinct_valid_code`<br>`tests/unit/core/test_input_rules_max_groups.py::test_create_records_max_groups`<br>`tests/unit/core/test_state_machine_create_and_permissions.py::test_create_activity_starts_preparing` |
| US1-AS2 | `tests/integration/test_us1_teacher.py::test_same_token_in_new_client_keeps_teacher_identity`<br>`tests/browser/test_teacher_restore.py::test_teacher_page_without_code_returns_to_last_activity` |
| US1-AS3 | `tests/integration/test_us1_teacher.py::test_client_without_token_is_rejected` |
| US1-AS4 | `tests/integration/test_us1_teacher.py::test_student_device_token_is_rejected`<br>`tests/unit/core/test_state_machine_create_and_permissions.py::test_non_teacher_is_rejected_without_change` |
| US1-AS5 | `tests/integration/test_us1_teacher.py::test_other_activity_teacher_is_rejected`<br>`tests/unit/core/test_state_machine_create_and_permissions.py::test_non_teacher_is_rejected_without_change` |
| US1-AS6 | `tests/integration/test_us1_teacher.py::test_code_only_request_gets_teacher_required_message`<br>`tests/unit/core/test_state_machine_create_and_permissions.py::test_non_teacher_is_rejected_without_change` |
| US1-AS7 | `tests/unit/core/test_input_rules_max_groups.py::test_create_with_boundary_max_groups`<br>`tests/unit/core/test_input_rules_max_groups.py::test_create_with_invalid_max_groups_is_rejected` |
| US1-AS8 | `tests/integration/test_us1_teacher.py::test_after_cancel_same_browser_can_create_again`<br>`tests/integration/test_us1_teacher.py::test_same_browser_cannot_create_second_live_activity`<br>`tests/integration/test_us1_teacher.py::test_unknown_previous_token_allows_create` |
| US2-AS1 | `tests/integration/test_us2_join.py::test_join_with_fullwidth_number_creates_group`<br>`tests/unit/core/test_state_machine_join.py::test_new_group_number_creates_group_and_device` |
| US2-AS2 | `tests/integration/test_us2_join.py::test_second_device_with_credential_shares_group`<br>`tests/unit/core/test_state_machine_join.py::test_existing_group_with_correct_credential_adds_device` |
| US2-AS3 | `tests/integration/test_us2_join.py::test_credentials_visible_to_own_group_and_teacher_only`<br>`tests/unit/core/test_snapshot_view_groups.py::test_group_view_contains_only_own_group_with_credential` |
| US2-AS4 | `tests/integration/test_us2_join.py::test_existing_number_without_credential_is_rejected`<br>`tests/unit/core/test_state_machine_join.py::test_existing_group_without_or_wrong_credential_rejected`<br>`tests/unit/core/test_state_machine_open_joining.py::test_group_with_a_device_still_requires_credential` |
| US2-AS5 | `tests/integration/test_us2_join.py::test_invalid_code_number_or_credential_changes_nothing`<br>`tests/unit/core/test_state_machine_join.py::test_invalid_group_number_rejected` |
| US2-AS6 | `tests/integration/test_us2_join.py::test_join_rejected_after_cancel`<br>`tests/unit/core/test_state_machine_join.py::test_terminal_stage_rejects_join` |
| US2-AS7 | `tests/integration/test_us2_join.py::test_join_during_round_sees_current_stage`<br>`tests/unit/core/test_state_machine_join.py::test_join_during_round_open_keeps_stage` |
| US2-AS8 | `tests/integration/test_us2_join.py::test_identity_restored_over_websocket` |
| US2-AS9 | `tests/integration/test_us2_join.py::test_member_device_cannot_join_again`<br>`tests/unit/core/test_state_machine_join.py::test_device_already_in_group_cannot_join_again` |
| US2-AS10 | `tests/unit/core/test_state_machine_open_joining.py::test_last_device_leaving_unsubmitted_group_releases_number`<br>`tests/unit/core/test_state_machine_open_joining.py::test_group_with_submissions_keeps_credential_after_all_devices_leave`<br>`tests/unit/core/test_state_machine_open_joining.py::test_leaving_with_other_devices_keeps_group_and_credential`<br>`tests/integration/test_us7_group_correction.py::test_last_leave_releases_unsubmitted_group_number`<br>`tests/integration/test_us7_group_correction.py::test_group_with_submissions_requires_credential_after_everyone_leaves`<br>`tests/integration/test_us7_group_correction.py::test_closing_the_page_is_not_leaving` |
| US3-AS1 | `tests/integration/test_us3_open_round.py::test_open_panel_defaults`<br>`tests/unit/core/test_state_machine_open_round.py::test_default_selects_all_unsolved_without_fair_mode_or_countdown` |
| US3-AS2 | `tests/integration/test_us3_open_round.py::test_open_two_questions_pushes_round_open_to_all`<br>`tests/unit/core/test_state_machine_open_round.py::test_open_two_questions_creates_round_one_with_baseline` |
| US3-AS3 | `tests/integration/test_us3_open_round.py::test_no_imported_questions`<br>`tests/unit/core/test_state_machine_open_round.py::test_no_questions_is_rejected` |
| US3-AS4 | `tests/integration/test_us3_open_round.py::test_invalid_selection_rejected`<br>`tests/unit/core/test_state_machine_open_round.py::test_invalid_open_is_rejected_without_change` |
| US3-AS5 | `tests/integration/test_us3_open_round.py::test_rules_locked_during_round`<br>`tests/unit/core/test_state_machine_open_round.py::test_open_again_during_round_is_rules_locked` |
| US3-AS6 | `tests/integration/test_us3_open_round.py::test_countdown_range`<br>`tests/unit/core/test_input_rules_round.py::test_invalid_countdown`<br>`tests/unit/core/test_state_machine_open_round.py::test_invalid_countdown_creates_no_round` |
| US3-AS7 | `tests/integration/test_us3_open_round.py::test_resent_open_creates_one_round` |
| US4-AS1 | `tests/integration/test_us4_close_finalize.py::test_teacher_close`<br>`tests/unit/core/test_state_machine_close_finalize.py::test_teacher_close_moves_to_result_pending` |
| US4-AS2 | `tests/integration/test_us4_close_finalize.py::test_deadline_closes_round`<br>`tests/unit/core/test_state_machine_close_finalize.py::test_system_close_only_after_deadline` |
| US4-AS3 | `tests/integration/test_us4_close_finalize.py::test_simultaneous_close_and_deadline`<br>`tests/unit/app/test_concurrent_close.py::test_close_and_deadline_race_closes_once_50_times`<br>`tests/unit/core/test_state_machine_close_finalize.py::test_second_close_is_idempotent` |
| US4-AS4 | `tests/integration/test_us4_close_finalize.py::test_no_auto_finalize`<br>`tests/unit/core/test_state_machine_close_finalize.py::test_result_pending_never_moves_by_itself` |
| US4-AS5 | `tests/integration/test_us4_close_finalize.py::test_open_next_round_before_finalize_rejected`<br>`tests/unit/core/test_state_machine_close_finalize.py::test_open_during_result_pending_rejected` |
| US4-AS6 | `tests/integration/test_us4_close_finalize.py::test_finalize_then_next_round`<br>`tests/unit/core/test_state_machine_close_finalize.py::test_finalize_then_next_round_only_unsolved` |
| US5-AS1 | `tests/integration/test_us5_end_cancel.py::test_end_shows_unsolved_on_all_pages`<br>`tests/unit/core/test_state_machine_end_cancel.py::test_end_after_finalize_lists_unsolved` |
| US5-AS2 | `tests/integration/test_us5_end_cancel.py::test_export_view_available_after_end` |
| US5-AS3 | `tests/integration/test_us5_end_cancel.py::test_end_during_round_or_pending_rejected`<br>`tests/unit/core/test_state_machine_end_cancel.py::test_end_during_round_or_pending_rejected` |
| US5-AS4 | `tests/integration/test_us5_end_cancel.py::test_cancel_while_preparing`<br>`tests/unit/core/test_state_machine_end_cancel.py::test_cancel_while_preparing_then_everything_rejected` |
| US5-AS5 | `tests/integration/test_us5_end_cancel.py::test_ended_rejects_submission_and_join`<br>`tests/unit/core/test_state_machine_end_cancel.py::test_ended_rejects_join` |
| US5-AS6 | `tests/integration/test_us5_end_cancel.py::test_end_while_preparing_rejected`<br>`tests/unit/core/test_state_machine_end_cancel.py::test_end_while_preparing_rejected` |
| US6-AS1 | `tests/integration/test_us6_sync.py::test_close_reaches_all_three_pages_with_same_version` |
| US6-AS2 | `tests/integration/test_us6_sync.py::test_failed_connection_does_not_affect_others` |
| US6-AS3 | `tests/integration/test_us6_sync.py::test_reconnect_gets_latest_snapshot_first` |
| US6-AS4 | `tests/integration/test_us6_sync.py::test_restart_makes_old_identities_gone` |
| US6-AS5 | `tests/integration/test_us6_sync.py::test_student_messages_never_contain_other_groups` |
| US7-AS1 | `tests/integration/test_us7_group_correction.py::test_leave_notifies_device_and_keeps_group`<br>`tests/unit/core/test_state_machine_group_correction.py::test_leave_removes_only_that_device`<br>`tests/unit/core/test_state_machine_open_joining.py::test_leave_group_stages_follow_joining` |
| US7-AS2 | `tests/integration/test_us7_group_correction.py::test_after_leave_device_joins_correct_group`<br>`tests/unit/core/test_state_machine_group_correction.py::test_after_leaving_device_can_join_another_group` |
| US7-AS3 | `tests/integration/test_us7_group_correction.py::test_leave_rejected_during_round`<br>`tests/unit/core/test_state_machine_group_correction.py::test_leave_during_round_open_is_rejected` |
| US7-AS4 | `tests/integration/test_us7_group_correction.py::test_submissions_remain_with_original_group`<br>`tests/unit/core/test_state_machine_group_correction.py::test_submissions_stay_with_original_group_after_leave` |
| US7-AS5 | `tests/integration/test_us7_group_correction.py::test_delete_group_with_devices_notifies_devices`<br>`tests/unit/core/test_state_machine_group_correction.py::test_delete_empty_group_removes_group_and_devices_and_frees_number`<br>`tests/unit/core/test_state_machine_open_joining.py::test_delete_group_with_devices_and_no_submissions` |
| US7-AS6 | `tests/integration/test_us7_group_correction.py::test_delete_group_with_submissions_rejected`<br>`tests/unit/core/test_state_machine_group_correction.py::test_delete_group_with_submissions_is_rejected`<br>`tests/unit/core/test_state_machine_open_joining.py::test_delete_group_with_submissions_is_still_rejected` |
| US7-AS7 | `tests/integration/test_us7_group_correction.py::test_delete_group_is_rejected_during_round`<br>`tests/unit/core/test_state_machine_open_joining.py::test_delete_group_is_rejected_during_round` |
| US7-AS8 | `tests/unit/core/test_state_machine_open_joining.py::test_deleted_group_number_can_be_recreated_with_a_new_credential` |
| US8-AS1 | `tests/unit/core/test_state_machine_open_joining.py::test_open_joining_moves_prepared_activity_to_joining` |
| US8-AS2 | `tests/unit/core/test_state_machine_open_joining.py::test_open_joining_requires_imported_questions` |
| US8-AS3 | `tests/unit/core/test_state_machine_open_joining.py::test_open_joining_is_teacher_only`<br>`tests/unit/core/test_state_machine_open_joining.py::test_open_joining_only_from_preparing`<br>`tests/unit/core/test_state_machine_open_joining.py::test_system_actor_cannot_open_joining` |
| US8-AS4 | `tests/unit/core/test_state_machine_open_joining.py::test_join_before_joining_is_open_is_rejected` |
| US8-AS5 | `tests/unit/core/test_state_machine_open_joining.py::test_join_allowed_once_joining_is_open` |
| US8-AS6 | `tests/unit/core/test_state_machine_open_joining.py::test_open_round_requires_joining_stage` |
| US8-AS7 | `tests/unit/core/test_state_machine_open_joining.py::test_cancel_and_replace_questions_allowed_before_first_round`<br>`tests/unit/core/test_state_machine_open_joining.py::test_end_activity_before_first_round_says_cancel_instead` |

共 57 個 Scenario，未對應：無。

## 003-round-submission

| Scenario | 測試 |
|---|---|
| US1-AS1 | `tests/contract/test_http_submissions.py::test_accepted_returns_201_without_sequence`<br>`tests/integration/test_us1_question_shapes.py::test_question_shapes_in_snapshots`<br>`tests/unit/app/round_submission/test_submit_us1.py::test_accepted_submission_is_stored_and_pushed`<br>`tests/unit/core/round_submission/test_decide_us1.py::test_any_order_is_accepted` |
| US1-AS2 | `tests/unit/core/round_submission/test_decide_us1.py::test_partial_set_leaves_others_open` |
| US1-AS3 | `tests/contract/test_http_submissions.py::test_invalid_content_is_400`<br>`tests/unit/app/round_submission/test_submit_us1.py::test_rejected_submission_changes_nothing`<br>`tests/unit/core/round_submission/test_answer_rules.py::test_blank_cell_lists_every_empty_blank`<br>`tests/unit/core/round_submission/test_decide_us1.py::test_rejected_attempt_does_not_consume_chance` |
| US1-AS4 | `tests/contract/test_http_submissions.py::test_invalid_content_is_400`<br>`tests/unit/core/round_submission/test_answer_rules.py::test_wrong_blank_count`<br>`tests/unit/core/round_submission/test_decide_us1.py::test_wrong_count_reports_expected` |
| US1-AS5 | `tests/contract/test_http_submissions.py::test_invalid_content_is_400`<br>`tests/unit/core/round_submission/test_decide_us1.py::test_question_not_open_or_unknown` |
| US1-AS6 | `tests/unit/core/round_submission/test_answer_rules.py::test_whitespace_only_is_blank` |
| US1-AS7 | `tests/unit/core/round_submission/test_decide_us1.py::test_nonsense_answer_is_accepted_as_text` |
| US2-AS1 | `tests/integration/test_submission_visibility.py::test_teacher_board_and_same_group_device_update`<br>`tests/integration/test_us2_submission_once.py::test_resend_returns_200_with_original`<br>`tests/unit/app/round_submission/test_submit_concurrency.py::test_two_devices_race_keeps_one` |
| US2-AS2 | `tests/integration/test_us2_submission_once.py::test_resend_returns_200_with_original`<br>`tests/unit/app/round_submission/test_submit_concurrency.py::test_resend_returns_original` |
| US2-AS3 | `tests/unit/core/round_submission/test_decide_us2.py::test_next_round_gives_a_new_chance` |
| US2-AS4 | `tests/unit/core/round_submission/test_decide_us2.py::test_existing_submission_wins_regardless_of_content` |
| US2-AS5 | `tests/unit/core/round_submission/test_decide_us2.py::test_invalid_then_valid_is_accepted` |
| US2-AS6 | `tests/integration/test_us5_published.py::test_submission_stays_with_original_group_after_leaving` |
| US2-AS7 | `tests/integration/test_us2_submission_once.py::test_cannot_delete_group_with_submissions` |
| US3-AS1 | `tests/unit/app/round_submission/test_submit_deadline.py::test_one_ms_before_deadline_is_accepted` |
| US3-AS2 | `tests/unit/app/round_submission/test_submit_deadline.py::test_at_or_after_deadline_is_rejected`<br>`tests/unit/core/round_submission/test_decide_us3.py::test_not_accepting_is_round_closed` |
| US3-AS3 | `tests/contract/test_http_submissions.py::test_stale_round_and_closed_are_409`<br>`tests/unit/app/round_submission/test_submit_deadline.py::test_no_countdown_accepts_until_teacher_closes`<br>`tests/unit/core/round_submission/test_decide_us3.py::test_not_accepting_is_round_closed` |
| US3-AS4 | `tests/contract/test_http_submissions.py::test_stale_round_and_closed_are_409`<br>`tests/unit/core/round_submission/test_decide_us3.py::test_stale_round` |
| US3-AS5 | `tests/unit/core/round_submission/test_decide_us3.py::test_order_by_received_at_then_sequence` |
| US3-AS6 | `tests/unit/app/round_submission/test_close_vs_submit.py::test_close_and_submit_race_50_times` |
| US3-AS7 | `tests/contract/test_http_submissions.py::test_client_fields_are_ignored` |
| US4-AS1 | `tests/unit/core/round_submission/test_view_open_round.py::test_student_sees_only_own_group` |
| US4-AS2 | `tests/integration/test_submission_visibility.py::test_student_gets_nothing_from_other_groups` |
| US4-AS3 | `tests/unit/core/round_submission/test_view_open_round.py::test_student_sees_only_own_group` |
| US4-AS4 | `tests/integration/test_submission_visibility.py::test_teacher_board_and_same_group_device_update`<br>`tests/unit/core/round_submission/test_view_open_round.py::test_teacher_sees_all_groups_with_order_but_no_rank` |
| US4-AS5 | `tests/unit/core/round_submission/test_view_open_round.py::test_teacher_sees_all_groups_with_order_but_no_rank` |
| US4-AS6 | `tests/integration/test_submission_visibility.py::test_teacher_board_and_same_group_device_update` |
| US5-AS1 | `tests/integration/test_us5_published.py::test_close_publishes_to_every_student`<br>`tests/unit/core/round_submission/test_view_published.py::test_closed_round_is_published_to_every_group` |
| US5-AS2 | `tests/unit/core/round_submission/test_view_published.py::test_closed_round_is_published_to_every_group` |
| US5-AS3 | `tests/integration/test_us5_published.py::test_second_round_keeps_history_and_hides_new_answers`<br>`tests/unit/core/round_submission/test_view_published.py::test_history_visible_but_new_round_stays_private` |
| US5-AS4 | `tests/integration/test_us5_published.py::test_close_publishes_to_every_student` |
| US5-AS5 | `tests/unit/core/round_submission/test_view_published.py::test_judged_wrong_field_follows_constant` |
| US6-AS1 | `tests/architecture/test_static_text_safety.py::test_no_html_parsing_apis`<br>`tests/integration/test_us6_safe_display.py::test_markup_answer_is_kept_verbatim` |
| US6-AS2 | `tests/architecture/test_static_text_safety.py::test_deadline_disables_forms_and_open_ended_round_is_labelled`<br>`tests/integration/test_us6_safe_display.py::test_round_with_countdown_exposes_backend_deadline` |
| US6-AS3 | `tests/architecture/test_static_text_safety.py::test_deadline_disables_forms_and_open_ended_round_is_labelled`<br>`tests/integration/test_us6_safe_display.py::test_round_without_countdown_accepts_until_teacher_closes` |
| US6-AS4 | `tests/architecture/test_static_text_safety.py::test_network_error_is_reported_as_unconfirmed`<br>`tests/architecture/test_static_text_safety.py::test_submitted_shown_only_after_success_or_from_snapshot` |
| US6-AS5 | `tests/integration/test_us6_safe_display.py::test_reconnect_shows_submissions_made_while_disconnected` |

共 37 個 Scenario，未對應：無。

## 003 對應的 OpenSpec Scenario（round-submission，14 個）

| OpenSpec Requirement | OpenSpec Scenario | 對應的 Acceptance Scenario | 有測試 |
|---|---|---|---|
| 多題作答與題組完整提交 | 不同順序作答 | US1-AS1、US1-AS2 | 是 |
| 多題作答與題組完整提交 | 題組少一格 | US1-AS3 | 是 |
| 每組每題每輪一次 | 同組兩裝置競爭 | US2-AS1 | 是 |
| 每組每題每輪一次 | 回應遺失後重送 | US2-AS2 | 是 |
| 每組每題每輪一次 | 下一輪重新作答 | US2-AS3 | 是 |
| 後端截止與接收順序 | 截止邊界 | US3-AS1、US3-AS2 | 是 |
| 後端截止與接收順序 | 舊輪次頁面提交 | US3-AS4 | 是 |
| 後端截止與接收順序 | 同時間戳 | US3-AS5 | 是 |
| 搶答中依角色限制資料 | 檢查學生資料回應 | US4-AS1、US4-AS2、US4-AS3 | 是 |
| 搶答中依角色限制資料 | 老師即時看板 | US4-AS4、US4-AS5 | 是 |
| 關輪公開結果與版本一致 | 結果公布與後續輪次 | US5-AS1、US5-AS3 | 是 |
| 關輪公開結果與版本一致 | 延遲回應 | US5-AS4 | 是 |
| 倒數與輸入安全顯示 | 特殊文字答案 | US6-AS1 | 是 |
| 倒數與輸入安全顯示 | 無倒數輪次 | US6-AS3 | 是 |

共 14 個 OpenSpec Scenario，未對應：無。

## 004-ranking-review

004 的 Scenario 編號獨立（US1-AS1～US7-AS14）；測試檔為 `tests/**/ranking_review/`、`test_us2_ranking_snapshot.py`、`test_us3_fair_snapshot.py`、`test_us4_judgement.py`、`test_us5_recalc.py`、`test_us6_two_rounds.py`、`test_us7_safe_display.py`、`test_ranking_*.py` 與 `tests/contract/test_http_ranking_review*.py`（2026-11-24，004 T079）。

| Scenario | 測試 |
|---|---|
| US1-AS1 | `tests/integration/test_us6_two_rounds.py::test_success_counts_feed_next_round_baseline`<br>`tests/unit/app/ranking_review/test_baseline_us1.py::test_three_cell_question_counts_once_not_three_times` |
| US1-AS2 | `tests/integration/test_us6_two_rounds.py::test_success_counts_feed_next_round_baseline`<br>`tests/unit/app/ranking_review/test_baseline_us1.py::test_speed_mode_successes_count_toward_baseline` |
| US1-AS3 | `tests/unit/app/ranking_review/test_baseline_us1.py::test_unfinalized_result_never_changes_baseline_or_success_counts`<br>`tests/unit/core/ranking_review/test_baseline.py::test_initial_counts_copies_baseline_and_does_not_mutate_input` |
| US1-AS4 | `tests/unit/app/ranking_review/test_baseline_us1.py::test_group_joining_after_round_opened_starts_at_zero`<br>`tests/unit/core/ranking_review/test_baseline.py::test_group_missing_from_baseline_starts_at_zero` |
| US2-AS1 | `tests/integration/test_us2_ranking_snapshot.py::test_ranking_appears_in_both_roles_after_close_within_two_seconds`<br>`tests/unit/core/ranking_review/test_order.py::test_order_follows_earliest_accepted_submission_per_question` |
| US2-AS2 | `tests/integration/test_us2_ranking_snapshot.py::test_ranking_appears_in_both_roles_after_close_within_two_seconds`<br>`tests/unit/core/ranking_review/test_order.py::test_questions_without_submissions_go_last_sorted_by_number` |
| US2-AS3 | `tests/integration/test_us2_ranking_snapshot.py::test_ranking_appears_in_both_roles_after_close_within_two_seconds`<br>`tests/unit/core/ranking_review/test_recompute_speed.py::test_earliest_submission_judged_wrong_keeps_question_order` |
| US2-AS4 | `tests/integration/test_us2_ranking_snapshot.py::test_ranking_appears_in_both_roles_after_close_within_two_seconds`<br>`tests/unit/core/ranking_review/test_rank_speed.py::test_same_group_fastest_on_two_questions_wins_both` |
| US2-AS5 | `tests/integration/test_us2_ranking_snapshot.py::test_ranking_appears_in_both_roles_after_close_within_two_seconds`<br>`tests/unit/core/ranking_review/test_rank_speed.py::test_three_candidates_get_ranks_one_two_three_and_only_first_wins` |
| US2-AS6 | `tests/unit/core/ranking_review/test_rank_speed.py::test_equal_receive_time_is_decided_by_sequence` |
| US2-AS7 | `tests/unit/core/ranking_review/test_rank_speed.py::test_speed_mode_ignores_success_counts` |
| US3-AS1 | `tests/integration/test_us3_fair_snapshot.py::test_fair_round_snapshot_has_counts_reasons_and_group_counts`<br>`tests/unit/core/ranking_review/test_rank_fair.py::test_fair_two_questions_split_between_groups` |
| US3-AS2 | `tests/unit/core/ranking_review/test_rank_fair.py::test_equal_count_and_time_is_decided_by_sequence` |
| US3-AS3 | `tests/unit/core/ranking_review/test_rank_fair.py::test_lower_baseline_beats_earlier_submission` |
| US3-AS4 | `tests/integration/test_us3_fair_snapshot.py::test_fair_round_snapshot_has_counts_reasons_and_group_counts`<br>`tests/unit/core/ranking_review/test_rank_fair.py::test_count_at_processing_reflects_earlier_wins_in_the_round` |
| US3-AS5 | `tests/unit/core/ranking_review/test_rank_fair.py::test_question_group_counts_once_not_per_blank` |
| US3-AS6 | `tests/unit/core/ranking_review/test_rank_fair.py::test_only_first_place_count_increases` |
| US4-AS1 | `tests/integration/test_us4_judgement.py::test_question_group_judgement_keeps_answers`<br>`tests/unit/core/ranking_review/test_review_rules_mark.py::test_mark_non_winner_keeps_original_candidate_data` |
| US4-AS2 | `tests/integration/test_us4_judgement.py::test_question_group_judgement_keeps_answers`<br>`tests/unit/core/ranking_review/test_review_rules_mark.py::test_mark_non_winner_keeps_original_candidate_data` |
| US4-AS3 | `tests/integration/test_us4_judgement.py::test_undo_steps_back_and_actions_follow`<br>`tests/unit/core/ranking_review/test_review_rules_mark.py::test_unmark_restores_original_rank` |
| US4-AS4 | `tests/unit/app/ranking_review/test_mark_permissions.py::test_student_and_anonymous_cannot_mark_or_unmark` |
| US4-AS5 | `tests/unit/app/ranking_review/test_mark_stages.py::test_round_still_open_has_clear_message` |
| US4-AS6 | `tests/unit/core/ranking_review/test_review_rules_mark.py::test_missing_submission_is_rejected` |
| US4-AS7 | `tests/integration/test_us4_judgement.py::test_speed_sequence_marks_and_replacement` |
| US4-AS8 | `tests/contract/test_http_ranking_review.py::test_mark_wrong_returns_changed_version_and_affected` |
| US4-AS9 | `tests/contract/test_http_ranking_review.py::test_non_winner_can_be_judged_through_api`<br>`tests/integration/test_us4_judgement.py::test_api_allows_judging_a_non_winner` |
| US4-AS10 | `tests/integration/test_ranking_visibility.py::test_replacement_chain_data_for_student_screen`<br>`tests/integration/test_us4_judgement.py::test_undo_steps_back_and_actions_follow`<br>`tests/unit/core/ranking_review/test_review_rules_mark.py::test_undo_steps_back_one_at_a_time` |
| US5-AS1 | `tests/unit/core/ranking_review/test_recompute.py::test_marking_first_winner_flips_both_questions` |
| US5-AS2 | `tests/unit/core/ranking_review/test_recompute.py::test_undo_returns_to_identical_result` |
| US5-AS3 | `tests/unit/core/ranking_review/test_recompute.py::test_all_candidates_wrong_means_no_success_and_no_count` |
| US5-AS4 | `tests/unit/core/ranking_review/test_recompute.py::test_mark_and_undo_sequence_returns_to_start` |
| US5-AS5 | `tests/integration/test_us5_recalc.py::test_affected_marks_follow_latest_change_and_versions_increase`<br>`tests/unit/core/ranking_review/test_diff.py::test_only_changed_questions_are_listed` |
| US5-AS6 | `tests/integration/test_us5_recalc.py::test_affected_marks_follow_latest_change_and_versions_increase` |
| US5-AS7 | `tests/unit/app/ranking_review/test_marks_concurrency.py::test_two_concurrent_marks_apply_serially_and_order_independent` |
| US5-AS8 | `tests/integration/test_us5_recalc.py::test_winner_marked_wrong_is_replaced_by_next` |
| US6-AS1 | `tests/integration/test_us6_two_rounds.py::test_success_counts_feed_next_round_baseline`<br>`tests/unit/app/ranking_review/test_finalize.py::test_finalize_updates_001_and_marks_correct`<br>`tests/unit/core/ranking_review/test_finalize_plan.py::test_plan_lists_solved_questions_increments_and_counts` |
| US6-AS2 | `tests/unit/app/ranking_review/test_finalize.py::test_finalize_updates_001_and_marks_correct`<br>`tests/unit/app/ranking_review/test_finalize.py::test_repeat_same_version_is_idempotent_and_calls_001_once` |
| US6-AS3 | `tests/unit/app/ranking_review/test_finalize.py::test_finalize_updates_001_and_marks_correct`<br>`tests/unit/app/ranking_review/test_finalize.py::test_stale_version_is_rejected_without_changes` |
| US6-AS4 | `tests/unit/app/ranking_review/test_post_final_lock.py::test_marking_after_final_is_rejected` |
| US6-AS5 | `tests/unit/app/ranking_review/test_post_final_lock.py::test_old_round_stays_locked_after_next_round_opens` |
| US6-AS6 | `tests/unit/app/ranking_review/test_finalize.py::test_finalize_without_any_mark` |
| US6-AS7 | `tests/integration/test_us6_two_rounds.py::test_round_without_submissions_finalizes_with_unchanged_counts`<br>`tests/unit/core/ranking_review/test_finalize_plan.py::test_no_submissions_means_empty_plan` |
| US7-AS1 | `tests/integration/test_ranking_visibility.py::test_no_ranking_while_round_is_open_for_every_role`<br>`tests/integration/test_us2_ranking_snapshot.py::test_no_ranking_while_round_is_open` |
| US7-AS2 | 無（前端畫面行為，專案沒有前端單元測試設施，由 `verification.md` 的 T094 人工驗證；資料面由 US7-AS5、AS6 對應的測試涵蓋） |
| US7-AS3 | `tests/integration/test_ranking_visibility.py::test_replacement_chain_data_for_student_screen`<br>`tests/unit/core/ranking_review/test_review_rules_mark.py::test_undo_steps_back_one_at_a_time` |
| US7-AS4 | `tests/integration/test_ranking_visibility.py::test_replacement_chain_data_for_student_screen` |
| US7-AS5 | `tests/integration/test_ranking_visibility.py::test_student_json_hides_teacher_only_keys_but_teacher_has_them`<br>`tests/unit/core/ranking_review/test_view_student.py::test_student_output_does_not_depend_on_group` |
| US7-AS6 | `tests/integration/test_ranking_visibility.py::test_student_json_hides_teacher_only_keys_but_teacher_has_them` |
| US7-AS7 | `tests/integration/test_us7_safe_display.py::test_answers_survive_judgement_verbatim_and_004_holds_no_answers` |
| US7-AS8 | `tests/integration/test_ranking_snapshot_monotonic.py::test_versions_never_decrease_across_marks_and_reads` |
| US7-AS9 | `tests/integration/test_ranking_visibility.py::test_all_wrong_hides_replaced_from_students_but_not_teacher`<br>`tests/integration/test_ranking_visibility.py::test_no_success_question_and_old_rounds_stay_public` |
| US7-AS10 | `tests/integration/test_ranking_visibility.py::test_no_success_question_and_old_rounds_stay_public` |
| US7-AS11 | `tests/integration/test_ranking_visibility.py::test_replacement_chain_data_for_student_screen` |
| US7-AS12 | `tests/integration/test_us7_safe_display.py::test_answers_survive_judgement_verbatim_and_004_holds_no_answers` |
| US7-AS13 | `tests/integration/test_ranking_visibility.py::test_no_success_question_and_old_rounds_stay_public` |
| US7-AS14 | `tests/integration/test_ranking_visibility.py::test_final_shows_correct_and_clears_replaced` |

共 56 個 Scenario，未對應：US7-AS2（1 個）。

## 004 對應的 OpenSpec Scenario（ranking-review）

| OpenSpec Requirement | OpenSpec Scenario | 對應的 Acceptance Scenario | 有測試 |
|---|---|---|---|
| 歷史成功次數基準 | 題組與不同模式的累計 | US1-AS1、US1-AS2 | 是 |
| 固定題目處理順序 | 最早提交被判錯 | US2-AS1、US2-AS2、US2-AS3 | 是 |
| 速度模式順位 | 同組最快回答兩題 | US2-AS4、US2-AS5、US2-AS6 | 是 |
| 公平模式順位 | 公平分配兩題 | US3-AS1、US3-AS2 | 是 |
| 公平模式順位 | 完全同次數與同時間 | US3-AS3 | 是 |
| 判錯及撤銷判錯 | 非勝者與題組判錯 | US4-AS1、US4-AS2、US4-AS7、US4-AS8 | 是 |
| 判錯及撤銷判錯 | 撤銷誤判 | US4-AS3 | 是 |
| 整輪重算與受影響題目 | 判錯造成跨題勝者改變 | US5-AS1、US5-AS2 | 是 |
| 整輪重算與受影響題目 | 全部被判錯 | US5-AS3 | 是 |
| 老師確認定案與歷史鎖定 | 定案及重複確認 | US6-AS1、US6-AS2 | 是 |
| 老師確認定案與歷史鎖定 | 定案前結果被更新 | US6-AS3 | 是 |
| 老師確認定案與歷史鎖定 | 定案後改判 | US6-AS4、US6-AS5 | 是 |
| （跨能力：round-submission「搶答中依角色限制資料」「關輪公開結果與版本一致」） | 老師即時看板（搶答中不顯示暫估順位）、結果公布與後續輪次 | US7-AS1、US7-AS5 | 是 |

共 13 列（ranking-review 的 12 個 Scenario 加 1 列跨能力的 round-submission Scenario），每列至少對應一個測試：是。

## 005-result-export

依 spec 的 35 個 Acceptance Scenario（US1～US6）掃描 `tests/` 產生（2026-11-25，005 T078）；OpenSpec result-export 的 12 個 Scenario 對應見 spec 的 OpenSpec Traceability 表。

| Scenario | 測試 |
|---|---|
| US1-AS1 | `tests/contract/result_export/test_http_preview_write.py::test_write_returns_attempt`<br>`tests/integration/test_export_us1_two_rounds.py::test_history_written_without_the_running_round`<br>`tests/unit/app/result_export/test_confirm_gate.py::test_confirm_with_current_snapshot_writes_winners_only`<br>`tests/unit/app/result_export/test_preview.py::test_round_in_progress_preview_has_only_finalized_history`<br>`tests/unit/core/result_export/test_snapshot.py::test_only_finalized_winners_are_written` |
| US1-AS2 | `tests/contract/result_export/test_http_preview_write.py::test_preview_shape_and_a1_targets`<br>`tests/unit/app/result_export/test_preview.py::test_preview_fields_and_plain_text_answers`<br>`tests/unit/core/result_export/test_snapshot.py::test_items_have_required_fields`<br>`tests/unit/core/result_export/test_snapshot.py::test_unwritten_questions_listed_sorted`<br>`tests/unit/core/result_export/test_snapshot.py::test_overwrite_impact_kinds_and_truncation`<br>`tests/unit/core/result_export/test_snapshot.py::test_number_with_same_digits_is_not_same` |
| US1-AS3 | `tests/unit/app/result_export/test_confirm_gate.py::test_stale_snapshot_is_rejected_and_nothing_written`<br>`tests/unit/core/result_export/test_snapshot_id.py::test_id_is_sorted_dot_joined`<br>`tests/unit/core/result_export/test_snapshot_id.py::test_new_round_changes_id_and_repeat_is_stable` |
| US1-AS4 | `tests/unit/app/result_export/test_confirm_gate.py::test_no_results_cannot_confirm`<br>`tests/unit/app/result_export/test_preview.py::test_no_winners_means_no_results_and_no_write`<br>`tests/unit/app/result_export/test_preview.py::test_all_unsolved_finalized_round_is_no_results` |
| US1-AS5 | `tests/unit/app/result_export/test_confirm_gate.py::test_non_teacher_cannot_confirm`<br>`tests/unit/app/result_export/test_preview.py::test_non_teacher_is_rejected_without_teacher_data` |
| US1-AS6 | `tests/unit/app/result_export/test_confirm_gate.py::test_ended_activity_still_works_and_nothing_is_written_automatically` |
| US1-AS7 | `tests/unit/app/result_export/test_confirm_gate.py::test_cancelled_activity_cannot_confirm`<br>`tests/unit/app/result_export/test_preview.py::test_cancelled_activity_is_rejected_without_external_calls` |
| US2-AS1 | `tests/unit/app/result_export/test_structure_gate.py::test_inserted_row_stops_the_whole_write`<br>`tests/unit/core/result_export/test_structure.py::test_inserted_row_moves_answer_cells` |
| US2-AS2 | `tests/unit/app/result_export/test_structure_gate.py::test_sheet_replaced_or_deleted_is_identity_difference`<br>`tests/unit/app/result_export/test_structure_gate.py::test_deleted_header_is_unrecognized`<br>`tests/unit/core/result_export/test_structure.py::test_row_inserted_above_header_moves_headers`<br>`tests/unit/core/result_export/test_structure.py::test_deleted_header_is_unrecognized`<br>`tests/unit/core/result_export/test_structure.py::test_each_difference_kind_is_reported_with_position` |
| US2-AS3 | `tests/unit/app/result_export/test_structure_gate.py::test_answer_text_and_rename_do_not_block_writing`<br>`tests/unit/core/result_export/test_structure.py::test_identical_snapshot_is_ok`<br>`tests/unit/core/result_export/test_structure.py::test_answer_text_change_is_not_a_structure_change`<br>`tests/unit/core/result_export/test_structure.py::test_rename_is_not_a_structure_change` |
| US2-AS4 | `tests/unit/app/result_export/test_structure_gate.py::test_whole_check_completes_before_any_write` |
| US2-AS5 | `tests/architecture/test_export_static.py::test_auth_param_is_read_synchronously_at_module_top`<br>`tests/contract/result_export/test_http_authorization.py::test_returns_auth_url`<br>`tests/unit/app/result_export/test_auth_failures.py::test_preview_and_confirm_stop_before_any_write`<br>`tests/unit/app/result_export/test_auth_failures.py::test_guidance_mentions_reauthorization_or_permission`<br>`tests/unit/app/result_export/test_reauthorization.py::test_available_in_every_non_cancelled_stage` |
| US3-AS1 | `tests/integration/test_export_us3_two_layouts.py::test_exact_write_and_everything_else_preserved`<br>`tests/unit/adapters/google/test_sheets_writer_request.py::test_single_batch_update_one_update_cells_per_cell`<br>`tests/unit/adapters/google/test_sheets_writer_request.py::test_fields_only_user_entered_value_and_no_value_input_option`<br>`tests/unit/app/result_export/test_exact_write.py::test_cells_are_blank_targets_with_verbatim_answers`<br>`tests/unit/app/result_export/test_exact_write.py::test_targets_come_from_import_record_only_and_losers_have_none` |
| US3-AS2 | `tests/integration/test_export_us3_two_layouts.py::test_exact_write_and_everything_else_preserved` |
| US3-AS3 | `tests/unit/adapters/google/test_sheets_writer_request.py::test_answers_are_sent_verbatim_as_string_values` |
| US3-AS4 | `tests/unit/adapters/google/test_sheets_writer_request.py::test_answers_are_sent_verbatim_as_string_values`<br>`tests/unit/app/result_export/test_exact_write.py::test_cells_are_blank_targets_with_verbatim_answers` |
| US3-AS5 | `tests/integration/test_export_us3_two_layouts.py::test_placeholder_replaced_for_winners_kept_for_unsolved`<br>`tests/unit/app/result_export/test_exact_write.py::test_targets_come_from_import_record_only_and_losers_have_none` |
| US3-AS6 | `tests/unit/adapters/google/test_sheets_writer_request.py::test_fields_only_user_entered_value_and_no_value_input_option`<br>`tests/unit/adapters/google/test_sheets_writer_request.py::test_merged_cell_writes_top_left_only` |
| US4-AS1 | `tests/unit/adapters/google/test_sheets_writer_outcomes.py::test_http_status_classification`<br>`tests/unit/adapters/google/test_sheets_writer_outcomes.py::test_timeouts_and_network_errors_are_pending`<br>`tests/unit/app/result_export/test_pending_and_recheck.py::test_lost_response_is_pending_not_success_nor_unwritten` |
| US4-AS2 | `tests/contract/result_export/test_http_attempts.py::test_recheck_has_cell_checks_other_responses_do_not`<br>`tests/unit/app/result_export/test_pending_and_recheck.py::test_recheck_actually_written_becomes_success_without_reading_structure`<br>`tests/unit/app/result_export/test_pending_and_recheck.py::test_recheck_nothing_written_becomes_failed_not_written`<br>`tests/unit/app/result_export/test_pending_and_recheck.py::test_recheck_partial_stays_pending_and_lists_mismatches`<br>`tests/unit/core/result_export/test_reconcile.py::test_all_match_is_success`<br>`tests/unit/core/result_export/test_reconcile.py::test_none_match_is_failed`<br>`tests/unit/core/result_export/test_reconcile.py::test_partial_is_pending_and_lists_mismatches` |
| US4-AS3 | `tests/unit/app/result_export/test_retry_idempotent.py::test_five_retries_are_identical_and_idempotent` |
| US4-AS4 | `tests/unit/app/result_export/test_read_only_for_activity.py::test_activity_results_unchanged_for_every_outcome`<br>`tests/unit/app/result_export/test_read_only_for_activity.py::test_no_mutating_calls_on_activity_or_other_features` |
| US4-AS5 | `tests/unit/app/result_export/test_retry_idempotent.py::test_retry_rechecks_structure_every_time` |
| US4-AS6 | `tests/unit/app/result_export/test_in_progress.py::test_concurrent_confirm_writes_once_and_lock_is_free_during_io` |
| US5-AS1 | `tests/contract/result_export/test_http_csv.py::test_download_headers_and_bom`<br>`tests/integration/test_export_us5_csv.py::test_group_questions_wrong_marks_and_unfinalized_round`<br>`tests/unit/app/result_export/test_download_csv.py::test_rows_follow_004_results_not_recomputed`<br>`tests/unit/core/result_export/test_build_rows.py::test_group_question_with_wrong_group_gives_four_rows` |
| US5-AS2 | `tests/unit/app/result_export/test_download_csv.py::test_only_finalized_rounds_are_included`<br>`tests/unit/core/result_export/test_build_rows.py::test_no_invented_rows_and_unfinalized_input_is_not_expanded` |
| US5-AS3 | `tests/contract/result_export/test_http_csv.py::test_header_only_when_no_data`<br>`tests/integration/test_export_us5_csv.py::test_header_only_before_any_finalized_round`<br>`tests/unit/app/result_export/test_download_csv.py::test_header_only_without_finalized_rounds` |
| US5-AS4 | `tests/unit/app/result_export/test_download_csv.py::test_rows_follow_004_results_not_recomputed`<br>`tests/unit/core/result_export/test_build_rows.py::test_three_candidates_failed_are_not_wrong`<br>`tests/unit/core/result_export/test_build_rows.py::test_order_wrong_after_ranked_and_by_receive_time` |
| US5-AS5 | `tests/unit/app/result_export/test_download_csv.py::test_independent_of_google_and_write_state`<br>`tests/unit/app/result_export/test_download_csv.py::test_download_does_not_touch_google_ports` |
| US5-AS6 | `tests/unit/core/result_export/test_build_rows.py::test_multi_round_distinguished_by_round`<br>`tests/unit/core/result_export/test_snapshot.py::test_multi_round_question_written_once` |
| US6-AS1 | `tests/unit/core/result_export/test_render_csv.py::test_header_is_fixed_nine_columns`<br>`tests/unit/core/result_export/test_render_csv.py::test_special_text_roundtrips_with_nine_columns` |
| US6-AS2 | `tests/unit/core/result_export/test_protect_text.py::test_formula_leading_characters_get_prefix`<br>`tests/unit/core/result_export/test_protect_text.py::test_other_text_is_unchanged`<br>`tests/unit/core/result_export/test_protect_text.py::test_only_group_and_answer_columns_are_protected` |
| US6-AS3 | `tests/architecture/test_export_static.py::test_no_html_parsing_apis`<br>`tests/architecture/test_export_static.py::test_protection_prefix_note_is_fixed_text`<br>`tests/integration/test_export_us6_safety.py::test_csv_protects_but_nothing_else_is_modified` |
| US6-AS4 | `tests/unit/core/result_export/test_render_csv.py::test_time_has_timezone_and_millisecond_precision` |
| US6-AS5 | `tests/integration/test_export_us6_safety.py::test_chinese_header_and_yes_no_columns`<br>`tests/unit/core/result_export/test_render_csv.py::test_none_values_empty_and_booleans_are_yes_no` |
