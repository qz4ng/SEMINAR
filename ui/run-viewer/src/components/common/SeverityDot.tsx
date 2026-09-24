import { Severity } from '../../data/types';
import clsx from 'clsx';

export function SeverityDot({ severity, className }: { severity: Severity, className?: string }) {
  const colorMap = {
    blocking: "bg-blocked",
    error: "bg-failed",
    warning: "bg-warn",
    info: "bg-info",
  };
  
  return (
    <div className={clsx("w-2 h-2 rounded-full shrink-0", colorMap[severity], className)} />
  );
}
