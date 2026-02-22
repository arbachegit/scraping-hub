import * as React from 'react';
import { cn } from '@/lib/utils';

export type InputProps = React.InputHTMLAttributes<HTMLInputElement>;

const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, type, ...props }, ref) => {
    return (
      <input
        type={type}
        className={cn(
          'flex h-12 w-full rounded-xl border-2 border-cyan-500/30 bg-[#1a2332] px-4 py-2 text-base text-foreground transition-all duration-200',
          'placeholder:text-muted-foreground',
          'focus:border-cyan-400 focus:outline-none focus:ring-2 focus:ring-cyan-500/20',
          'disabled:cursor-not-allowed disabled:opacity-50',
          className
        )}
        ref={ref}
        {...props}
      />
    );
  }
);
Input.displayName = 'Input';

export { Input };
