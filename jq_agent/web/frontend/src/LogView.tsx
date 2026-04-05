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

const LOG_FONT =
  '400 13.6px Inter, "Noto Sans SC", "PingFang SC", "Hiragino Sans GB", sans-serif';
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
      className="max-h-[min(60vh,28rem)] overflow-y-auto overflow-x-hidden rounded-lg border border-slate-700 bg-slate-900 contain-content [scrollbar-gutter:stable]"
    >
      {lines.length === 0 ? (
        <div className="min-h-16 px-4 py-4 font-mono text-[0.85rem] text-slate-500" />
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
              className="absolute left-0 box-border whitespace-pre-wrap break-words px-4 font-mono text-[0.85rem] leading-[22px] text-slate-200"
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
