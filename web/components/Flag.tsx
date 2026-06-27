import { flagUrl } from "@/lib/flags";

export function Flag({ name, size = "md" }: { name: string; size?: "sm" | "md" | "lg" }) {
  const url = flagUrl(name);
  const cls =
    size === "lg" ? "w-[62px] h-[46px] rounded-lg" :
    size === "sm" ? "w-[22px] h-[16px] rounded-[3px]" :
    "w-[30px] h-[22px] rounded";
  if (!url) {
    return (
      <span className={`${cls} inline-flex items-center justify-center bg-bg2 border border-line text-muted text-[11px] font-extrabold shrink-0`}>
        {(name || "?").slice(0, 2).toUpperCase()}
      </span>
    );
  }
  // eslint-disable-next-line @next/next/no-img-element
  return <img src={url} alt="" loading="lazy" className={`${cls} object-cover shadow-md shrink-0`} />;
}
