## [LRN-20260415-001] correction

**Logged**: 2026-04-15T00:00:00Z
**Priority**: high
**Status**: pending
**Area**: backend

### Summary

Do not treat `/ws/meeting/{session_id}` as the current gateway contract in this worktree; the user-confirmed latest contract is `/ws/pipeline/dir`.

### Details

During live verification, the gateway/frontend mismatch was initially analyzed as a missing `type: start_meeting` wrapper. The user clarified that this premise was wrong: `/ws/pipeline/dir` is the latest interface from the target fullGateway API documentation, while `/ws/meeting/{session_id}` is the old interface and should be removed entirely.

### Suggested Action

When restoring gateway compatibility, use the existing frontend client and `tests/test_gateway_pipeline_dir_contract.py` as the local source of truth, restore `/ws/pipeline/dir`, and delete `/ws/meeting/{session_id}` instead of adding compatibility shims.

### Metadata

- Source: user_feedback
- Related Files: gateway/main_server.py, frontend/src/services/api.ts, tests/test_gateway_pipeline_dir_contract.py, API_DOC.md
- Tags: websocket, contract, correction

---
## [LRN-20260413-001] correction

**Logged**: 2026-04-13T20:35:00
**Priority**: high
**Status**: pending
**Area**: frontend

### Summary

Audio-first subtitle bugs should be fixed in the frontend by adapting timestamp rendering and virtualizing the full list instead of truncating or reshaping backend output.

### Details

The earlier approach tried to normalize audio timestamps in the gateway and limit subtitle delivery to 50 items. That would have hidden the real UI scalability issue and still left the frontend coupled to the wrong timestamp assumption. The corrected approach keeps backend payloads intact, formats floating-point second strings in the UI, renders all subtitles through virtualization, and preserves translation matching by subtitle ID.

### Suggested Action

When demo sources emit different timestamp formats, normalize them at the presentation boundary and keep subtitle identity stable end-to-end.

### Metadata

- Source: conversation
- Related Files: frontend/src/components/SubtitlePanel.vue, frontend/src/stores/meeting.ts
- Tags: frontend, timestamps, virtualization, translation-mapping

---
## [LRN-20260415-002] correction

**Logged**: 2026-04-15T00:00:00Z
**Priority**: high
**Status**: pending
**Area**: frontend

### Summary

Do not decide whether a list needs virtualization based on whether it is realtime; post-meeting result panes can still be long lists and need a correct virtualized viewport.

### Details

The initial response assumed that action items and significant moments should revert to plain rendering because they are not streaming data. The user corrected that premise: these lists are not realtime, but they can still be long enough to require virtualization. The actual bug was the missing and flawed shared virtual list implementation, not the decision to virtualize the panels.

### Suggested Action

When evaluating list rendering in this frontend, separate data freshness from list size. Keep virtualization for any potentially long list, and verify the viewport implementation itself before replacing it with a plain list.

### Metadata

- Source: user_feedback
- Related Files: frontend/src/components/FullCardWindow.vue, frontend/src/components/SummaryPanel.vue, frontend/src/components/SentimentPanel.vue
- Tags: frontend, virtualization, correction, ui

---