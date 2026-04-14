## [ERR-20260413-001] npm_run_build

**Logged**: 2026-04-13T20:36:00
**Priority**: medium
**Status**: resolved
**Area**: frontend

### Summary

Vue template typechecking rejected the virtualized row ref callback because its parameter type was narrower than `VNodeRef`.

### Error
```
src/components/SubtitlePanel.vue:17:14 - error TS2322: Type '(element: Element | null) => void' is not assignable to type 'VNodeRef | undefined'.
```

### Context
- Command attempted: `npm run build`
- Trigger: adding `:ref="measureSubtitleElement"` for `@tanstack/vue-virtual`
- Environment: Vue 3.5 + vue-tsc

### Suggested Fix

Accept `Element | ComponentPublicInstance | null` in the callback and guard with `instanceof Element` before passing the node to `measureElement`.

### Metadata
- Reproducible: yes
- Related Files: frontend/src/components/SubtitlePanel.vue

### Resolution

- **Resolved**: 2026-04-13T20:38:00
- **Commit/PR**: not committed
- **Notes**: Broadened the callback signature and re-ran `npm run build` successfully.

---

## [ERR-20260414-002] run_in_terminal_cwd_simplification

**Logged**: 2026-04-14T20:02:00
**Priority**: medium
**Status**: pending
**Area**: infra

### Summary

Launching `npm run dev` with `run_in_terminal` from a nested folder lost the intended working-directory context and executed the command from the repository root.

### Error
```
npm error Missing script: "dev"
```

### Context
- Command attempted: `Set-Location frontend; npm run dev`
- Trigger: validating the frontend manually after lifecycle changes
- Environment: PowerShell terminal created by `run_in_terminal`

### Suggested Fix

Prefer sending a follow-up command to an existing terminal with an explicit `Set-Location frontend; npm run dev` chain, or use commands whose cwd does not depend on tool-side simplification.

### Metadata
- Reproducible: yes
- Related Files: frontend/package.json

---