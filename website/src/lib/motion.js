/* Shared Framer Motion vocabulary so every reveal on the site moves the same way. */
export const EASE = [0.16, 1, 0.3, 1];          // "expo-ish" out: quick start, long settle
export const EASE_INOUT = [0.65, 0, 0.35, 1];

export const fadeUp = {
  hidden: { opacity: 0, y: 26 },
  show: { opacity: 1, y: 0, transition: { duration: 0.9, ease: EASE } },
};
export const stagger = (delay = 0, step = 0.08) => ({
  hidden: {},
  show: { transition: { delayChildren: delay, staggerChildren: step } },
});
export const viewport = { once: true, amount: 0.18, margin: "0px 0px -8% 0px" };

export const pageVariants = {
  initial: { opacity: 0, y: 14 },
  enter: { opacity: 1, y: 0, transition: { duration: 0.55, ease: EASE } },
  exit: { opacity: 0, y: -10, transition: { duration: 0.3, ease: EASE_INOUT } },
};
