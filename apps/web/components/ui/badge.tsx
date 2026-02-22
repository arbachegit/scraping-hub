import * as React from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '@/lib/utils';

const badgeVariants = cva(
  'inline-flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-xs font-medium transition-all cursor-pointer',
  {
    variants: {
      variant: {
        default:
          'border-cyan-500/30 bg-cyan-500/10 text-cyan-400 hover:bg-cyan-500/20',
        secondary:
          'border-blue-500/30 bg-blue-500/10 text-blue-400 hover:bg-blue-500/20',
        success:
          'border-green-500/30 bg-green-500/10 text-green-400 hover:bg-green-500/20',
        warning:
          'border-amber-500/30 bg-amber-500/10 text-amber-400 hover:bg-amber-500/20',
        destructive:
          'border-red-500/30 bg-red-500/10 text-red-400 hover:bg-red-500/20',
        outline: 'border-border text-foreground hover:bg-accent',
      },
    },
    defaultVariants: {
      variant: 'default',
    },
  }
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return (
    <div className={cn(badgeVariants({ variant }), className)} {...props} />
  );
}

export { Badge, badgeVariants };
