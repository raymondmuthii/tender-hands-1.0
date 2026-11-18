import type { AnchorHTMLAttributes, ReactNode } from 'react';

type LinkStubProps = Omit<AnchorHTMLAttributes<HTMLAnchorElement>, 'href'> & {
  to?: unknown;
  children?: ReactNode;
};

/** Plain anchor standing in for TanStack's <Link> in component tests. */
export function LinkStub({ to, children, ...rest }: LinkStubProps) {
  return (
    <a href={typeof to === 'string' ? to : '#'} {...rest}>
      {children}
    </a>
  );
}
