/**
 * 日志区：chenglou/pretext 无 DOM 折行 + TanStack Virtual 可视区渲染。
 * @see https://github.com/chenglou/pretext
 */
import { layoutWithLines, prepareWithSegments } from "@chenglou/pretext";
import { useVirtualizer } from "@tanstack/react-virtual";
import {
  useEffect,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
  type RefObject,
} from "react";

/* 与 index.css 中 IBM Plex Mono + 中文回退一致，供 Pretext canvas 测量 */
const LOG_FONT =
  '400 13.6px "IBM Plex Mono", "Noto Sans SC", "PingFang SC", monospace';
const LINE_HEIGHT_PX = 22;
const PAD_X = 16;

function useContentWidth(scrollRef: RefObject<HTMLDivElement | null>) {
  const [w, setW] = useState(600);

  useLayoutEffect(() => {
    const el = scrollRef.current;
    if (!el) return;
    const measure = () => {
      const inner = Math.max(64, el.clientWidth - PAD_X * 2);
      setW(inner);
    };
    measure();
    const ro = new ResizeObserver(measure);
    ro.observe(el);
    return () => ro.disconnect();
  }, [scrollRef]);

  return w;
}

type LogViewProps = {
  text: string;
};

export function LogView({ text }: LogViewProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const followBottomRef = useRef(true);
  const contentWidth = useContentWidth(scrollRef);

  const lines = useMemo(() => {
    const maxW = Math.max(64, contentWidth);
    if (!text) return [] as string[];
    const prepared = prepareWithSegments(text, LOG_FONT, {
      whiteSpace: "pre-wrap",
    });
    const { lines: ls } = layoutWithLines(prepared, maxW, LINE_HEIGHT_PX);
    return ls.map((l) => l.text);
  }, [text, contentWidth]);

  const virtualizer = useVirtualizer({
    count: lines.length,
    getScrollElement: () => scrollRef.current,
    estimateSize: () => LINE_HEIGHT_PX,
    overscan: 16,
  });

  useEffect(() => {
    if (!followBottomRef.current || lines.length === 0) return;
    virtualizer.scrollToIndex(lines.length - 1, { align: "end" });
  }, [lines.length, text, virtualizer]);

  const onScroll = () => {
    const el = scrollRef.current;
    if (!el) return;
    const nearBottom =
      el.scrollHeight - el.scrollTop - el.clientHeight < 56;
    followBottomRef.current = nearBottom;
  };

  const vItems = virtualizer.getVirtualItems();
  const total = virtualizer.getTotalSize();

  return (
    <div
      ref={scrollRef}
      onScroll={onScroll}
      className="panel-shoji log-scroll max-h-[min(58vh,26rem)] overflow-y-auto overflow-x-hidden rounded-sm [scrollbar-gutter:stable]"
    >
      {lines.length === 0 ? (
        <div className="font-[family-name:var(--font-ui)] min-h-20 px-4 py-6 text-sm italic text-[var(--color-gofun-muted)]/80">
          运行任务后，流式日志将显示于此…
        </div>
      ) : (
        <div
          className="relative w-full"
          style={{
            height: total + PAD_X * 2,
            font: LOG_FONT,
          }}
        >
          {vItems.map((vi) => (
            <div
              key={vi.key}
              className="absolute left-0 box-border whitespace-pre-wrap break-words px-4 font-[family-name:var(--font-mono)] text-[0.85rem] leading-[22px] text-[var(--color-gofun)]/92"
              style={{
                top: 0,
                width: "100%",
                transform: `translateY(${vi.start + PAD_X}px)`,
              }}
            >
              {lines[vi.index]}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
