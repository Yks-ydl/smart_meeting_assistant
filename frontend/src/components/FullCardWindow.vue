<template>
  <div
    ref="containerRef"
    class="full-card-window"
  >
    <div
      v-if="items.length > 0"
      class="full-card-window__shell"
    >
      <div class="full-card-window__viewport" :style="{ height: `${totalSize}px` }">
        <div
          v-for="entry in virtualRows"
          :key="entry.key"
          :data-index="entry.virtualRow.index"
          :ref="measureElement"
          class="full-card-window__item"
          :style="{
            transform: `translateY(${entry.virtualRow.start}px)`,
            paddingBottom: entry.virtualRow.index === items.length - 1 ? '0px' : `${itemGap}px`,
          }"
        >
          <slot :item="entry.item" :index="entry.virtualRow.index"></slot>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch, type ComponentPublicInstance } from 'vue'
import { useVirtualizer, type VirtualItem } from '@tanstack/vue-virtual'

type FullCardWindowItem = any
type VirtualWindowRow = {
  key: string
  item: FullCardWindowItem
  virtualRow: VirtualItem
}

const props = withDefaults(defineProps<{
  items: FullCardWindowItem[]
  getItemKey: (item: FullCardWindowItem, index: number) => string | number
  estimateItemHeight?: number
  itemGap?: number
  overscan?: number
}>(), {
  estimateItemHeight: 144,
  itemGap: 12,
  overscan: 4,
})

defineSlots<{
  default(props: { item: FullCardWindowItem; index: number }): unknown
}>()

const containerRef = ref<HTMLDivElement | null>(null)
let viewportObserver: ResizeObserver | null = null
let measureFrame = 0

// Centralize the stable virtual-list behavior here so long result lists reuse one measurement path.
const rowVirtualizer = useVirtualizer<HTMLDivElement, HTMLDivElement>(
  computed(() => ({
    count: props.items.length,
    getScrollElement: () => containerRef.value,
    estimateSize: () => props.estimateItemHeight + props.itemGap,
    overscan: props.overscan,
    getItemKey: (index: number) =>
      String(props.getItemKey(props.items[index], index)),
  })),
)

const totalSize = computed(() => rowVirtualizer.value.getTotalSize())
const virtualRows = computed<VirtualWindowRow[]>(() =>
  rowVirtualizer.value.getVirtualItems().reduce<VirtualWindowRow[]>((rows, virtualRow) => {
    const item = props.items[virtualRow.index]
    if (item !== undefined) {
      rows.push({
        key: String(props.getItemKey(item, virtualRow.index)),
        item,
        virtualRow,
      })
    }

    return rows
  }, []),
)

function scheduleMeasure(): void {
  if (measureFrame) {
    cancelAnimationFrame(measureFrame)
  }

  measureFrame = requestAnimationFrame(() => {
    measureFrame = 0
    rowVirtualizer.value.measure()
  })
}

function observeViewport(): void {
  viewportObserver?.disconnect()

  const container = containerRef.value
  if (!container) {
    return
  }

  viewportObserver = new ResizeObserver(() => {
    scheduleMeasure()
  })
  viewportObserver.observe(container)
}

function measureElement(
  element: Element | ComponentPublicInstance | null,
): void {
  if (element instanceof Element) {
    rowVirtualizer.value.measureElement(element as HTMLDivElement)
  }
}

watch(
  () => props.items,
  async () => {
    await nextTick()
    scheduleMeasure()
  },
  { deep: true },
)

watch(
  () => [props.estimateItemHeight, props.itemGap, props.overscan],
  async () => {
    await nextTick()
    scheduleMeasure()
  },
)

onMounted(() => {
  observeViewport()
  scheduleMeasure()
})

onBeforeUnmount(() => {
  viewportObserver?.disconnect()
  if (measureFrame) {
    cancelAnimationFrame(measureFrame)
    measureFrame = 0
  }
})
</script>

<style scoped>
.full-card-window {
  min-height: 0;
  overflow-y: auto;
  overscroll-behavior: contain;
  scrollbar-gutter: stable;
}

.full-card-window__shell {
  min-height: 100%;
}

.full-card-window__viewport {
  min-height: 100%;
  position: relative;
  width: 100%;
}

.full-card-window__item {
  left: 0;
  position: absolute;
  top: 0;
  width: 100%;
}
</style>