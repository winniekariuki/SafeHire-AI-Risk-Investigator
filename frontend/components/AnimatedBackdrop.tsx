"use client";

/**
 * Full-viewport decorative layer: soft gradient orbs + slow drift.
 * Keep ``pointer-events-none`` so it never blocks clicks.
 */
export function AnimatedBackdrop() {
  return (
    <div
      className="pointer-events-none fixed inset-0 -z-10 overflow-hidden"
      aria-hidden
    >
      <div className="safehire-blob safehire-blob-1 absolute -left-24 -top-24 h-[28rem] w-[28rem] rounded-full bg-fuchsia-400/35 blur-3xl dark:bg-fuchsia-500/25" />
      <div className="safehire-blob safehire-blob-2 absolute -right-20 top-1/3 h-[26rem] w-[26rem] rounded-full bg-cyan-400/30 blur-3xl dark:bg-cyan-500/20" />
      <div className="safehire-blob safehire-blob-3 absolute bottom-0 left-1/3 h-[24rem] w-[24rem] rounded-full bg-amber-300/25 blur-3xl dark:bg-amber-400/15" />
      <div className="safehire-mesh absolute inset-0 opacity-40 dark:opacity-25" />
    </div>
  );
}
