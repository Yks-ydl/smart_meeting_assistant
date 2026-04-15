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