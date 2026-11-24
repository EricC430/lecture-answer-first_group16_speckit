# Scenario 對應表（001-activity-session、003-round-submission）

依憲章原則 VI，spec 的每個 Acceptance Scenario 至少對應一個自動化測試；測試函式的 docstring 寫 `Scenario: USn-ASm`。本表由 `tests/` 掃描產生（2026-11-24，003 T059）。001 與 003 的編號各自獨立：003 新增的測試檔歸 003，其餘歸 001。

## 001-activity-session

| Scenario | 測試 |
|---|---|
| US1-AS1 | `tests/integration/test_us1_teacher.py::test_second_activity_gets_distinct_valid_code`<br>`tests/unit/core/test_input_rules_max_groups.py::test_create_records_max_groups`<br>`tests/unit/core/test_state_machine_create_and_permissions.py::test_create_activity_starts_preparing` |
| US1-AS2 | `tests/integration/test_us1_teacher.py::test_same_token_in_new_client_keeps_teacher_identity` |
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
| US2-AS10 | `tests/unit/core/test_state_machine_open_joining.py::test_group_without_devices_can_be_joined_without_credential`<br>`tests/unit/core/test_state_machine_open_joining.py::test_group_without_devices_ignores_a_wrong_credential` |
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
