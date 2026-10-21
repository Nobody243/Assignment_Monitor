import React from "react";
import { motion } from "framer-motion";
import { pageVariants } from "../lib/motion.js";

/* Route container: pages fade and drift between each other; the planet behind them simply keeps turning. */
export default function Page({ children, className = "" }) {
  return (
    <motion.main className={`page ${className}`} variants={pageVariants} initial="initial" animate="enter" exit="exit">
      {children}
    </motion.main>
  );
}
