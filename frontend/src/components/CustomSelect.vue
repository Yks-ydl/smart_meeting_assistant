<template>
  <div class="custom-select" ref="selectRef">
    <div
      class="select-trigger"
      :class="{ active: isOpen, focused: isFocused, disabled: props.disabled }"
      @click="toggleDropdown"
      @keydown="handleKeydown"
      :tabindex="props.disabled ? -1 : 0"
      :aria-disabled="props.disabled ? 'true' : 'false'"
      @focus="handleFocus"
      @blur="handleBlur"
    >
      <span class="selected-value">{{ selectedLabel }}</span>
      <span class="arrow" :class="{ rotated: isOpen }">
        <svg width="12" height="12" viewBox="0 0 12 12" fill="currentColor">
          <path d="M6 8L1 3h10z" />
        </svg>
      </span>
    </div>

    <Transition name="dropdown">
      <div v-if="isOpen" class="dropdown-menu">
        <div v-for="(option, index) in options" :key="option.value" class="dropdown-item" :class="{
          selected: option.value === modelValue,
          highlighted: index === highlightedIndex
        }" @click.stop="selectOption(option)" @mouseenter="highlightedIndex = index">
          {{ option.label }}
        </div>
      </div>
    </Transition>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'

interface SelectOption {
  value: string
  label: string
}

const props = withDefaults(
  defineProps<{
    modelValue: string
    options: SelectOption[]
    disabled?: boolean
  }>(),
  {
    disabled: false,
  }
)

const emit = defineEmits<{
  (e: 'update:modelValue', value: string): void
}>()

const selectRef = ref<HTMLElement | null>(null)
const isOpen = ref(false)
const isFocused = ref(false)
const highlightedIndex = ref(0)

const selectedLabel = computed(() => {
  const option = props.options.find((opt) => opt.value === props.modelValue)
  return option ? option.label : ''
})

function toggleDropdown() {
  if (props.disabled) {
    return
  }

  isOpen.value = !isOpen.value
  if (isOpen.value) {
    highlightedIndex.value = props.options.findIndex(
      (opt) => opt.value === props.modelValue
    )
    if (highlightedIndex.value < 0) highlightedIndex.value = 0
  }
}

function selectOption(option: SelectOption) {
  if (props.disabled) {
    return
  }

  emit('update:modelValue', option.value)
  isOpen.value = false
}

function handleFocus() {
  if (props.disabled) {
    return
  }
  isFocused.value = true
}

function handleBlur() {
  isFocused.value = false
  setTimeout(() => {
    isOpen.value = false
  }, 150)
}

function handleKeydown(e: KeyboardEvent) {
  if (props.disabled) {
    return
  }

  if (!isOpen.value) {
    if (e.key === 'Enter' || e.key === ' ' || e.key === 'ArrowDown') {
      e.preventDefault()
      isOpen.value = true
      highlightedIndex.value = props.options.findIndex(
        (opt) => opt.value === props.modelValue
      )
      if (highlightedIndex.value < 0) highlightedIndex.value = 0
    }
    return
  }

  switch (e.key) {
    case 'ArrowDown':
      e.preventDefault()
      highlightedIndex.value = (highlightedIndex.value + 1) % props.options.length
      break
    case 'ArrowUp':
      e.preventDefault()
      highlightedIndex.value =
        (highlightedIndex.value - 1 + props.options.length) % props.options.length
      break
    case 'Enter':
    case ' ':
      e.preventDefault()
      if (props.options[highlightedIndex.value]) {
        selectOption(props.options[highlightedIndex.value])
      }
      break
    case 'Escape':
      e.preventDefault()
      isOpen.value = false
      break
  }
}

function handleClickOutside(e: MouseEvent) {
  if (selectRef.value && !selectRef.value.contains(e.target as Node)) {
    isOpen.value = false
  }
}

onMounted(() => {
  document.addEventListener('click', handleClickOutside)
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
})

watch(
  () => props.disabled,
  (disabled) => {
    if (disabled) {
      isOpen.value = false
      isFocused.value = false
    }
  }
)

watch(isOpen, (open) => {
  if (!open) {
    highlightedIndex.value = 0
  }
})
</script>

<style scoped>
.custom-select {
  position: relative;
  width: 100%;
}

.select-trigger {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 13px;
  padding-right: 36px;
  border: 1px solid var(--border-color);
  border-radius: 8px;
  background-color: var(--bg-card);
  color: var(--text-primary);
  font-size: 0.95rem;
  cursor: pointer;
  transition: border-color 0.2s, background-color 0.2s, box-shadow 0.2s;
  user-select: none;
}

.select-trigger:not(.disabled):hover {
  background-color: var(--bg-card-alt);
}

.select-trigger:not(.disabled).focused,
.select-trigger:not(.disabled).active {
  border-color: var(--primary);
  box-shadow: 0 0 0 2px rgba(14, 165, 233, 0.15);
}

.select-trigger.disabled {
  cursor: not-allowed;
  opacity: 0.6;
  background-color: var(--bg-card-alt);
}

.selected-value {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.arrow {
  position: absolute;
  right: 12px;
  display: flex;
  align-items: center;
  color: var(--text-muted);
  transition: transform 0.2s ease;
}

.arrow.rotated {
  transform: rotate(180deg);
}

.dropdown-menu {
  position: absolute;
  top: calc(100% + 4px);
  left: 0;
  right: 0;
  background-color: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.12);
  z-index: 100;
  overflow: hidden;
}

.dropdown-item {
  padding: 11px 12px;
  color: var(--text-secondary);
  cursor: pointer;
  transition: background-color 0.15s, color 0.15s;
}

.dropdown-item:hover,
.dropdown-item.highlighted {
  background-color: var(--bg-card-alt);
  color: var(--text-primary);
}

.dropdown-item.selected {
  background-color: rgba(14, 165, 233, 0.14);
  color: var(--primary);
}

.dropdown-item.selected:hover,
.dropdown-item.selected.highlighted {
  background-color: rgba(14, 165, 233, 0.22);
}

.dropdown-enter-active,
.dropdown-leave-active {
  transition: opacity 0.15s ease, transform 0.15s ease;
}

.dropdown-enter-from,
.dropdown-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}

.dropdown-enter-to,
.dropdown-leave-from {
  opacity: 1;
  transform: translateY(0);
}
</style>
