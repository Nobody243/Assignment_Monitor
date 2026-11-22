import React, { useMemo } from "react";
import qrcode from "qrcode-generator";

/* A QR code drawn as one SVG path, made in the browser (nothing is sent anywhere). Dark on white with a quiet zone,
   so every scanner reads it in both themes. */
export function Qr({ value, size = 168, label }) {
  const { path, n } = useMemo(() => {
    const q = qrcode(0, "M");
    q.addData(value); q.make();
    const count = q.getModuleCount();
    let d = "";
    for (let r = 0; r < count; r += 1) for (let c = 0; c < count; c += 1) if (q.isDark(r, c)) d += `M${c + 4} ${r + 4}h1v1h-1z`;
    return { path: d, n: count + 8 };
  }, [value]);
  return (
    <svg className="qr" viewBox={`0 0 ${n} ${n}`} width={size} height={size} role="img" aria-label={label || `QR code for ${value}`} shapeRendering="crispEdges">
      <rect width={n} height={n} fill="#fff" />
      <path d={path} fill="#0b0b0d" />
    </svg>
  );
}
