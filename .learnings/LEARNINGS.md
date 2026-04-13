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