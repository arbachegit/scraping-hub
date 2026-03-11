import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

/**
 * Next.js Middleware for route protection.
 *
 * Since tokens are stored in localStorage (client-side only),
 * we cannot validate them server-side. Instead, we set a cookie
 * flag on login that the middleware can check. The real auth
 * validation happens client-side via fetchWithAuth.
 *
 * This middleware provides a fast redirect for unauthenticated
 * users, avoiding a flash of protected content.
 */

const PROTECTED_ROUTES = ['/dashboard', '/admin', '/profile', '/emendas', '/noticias', '/inteligencia'];

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Check if this is a protected route
  const isProtected = PROTECTED_ROUTES.some(
    (route) => pathname === route || pathname.startsWith(route + '/')
  );

  if (!isProtected) {
    return NextResponse.next();
  }

  // Check for auth cookie (set by client on login)
  const hasAuthCookie = request.cookies.has('has_session');

  if (!hasAuthCookie) {
    const loginUrl = new URL('/', request.url);
    return NextResponse.redirect(loginUrl);
  }

  return NextResponse.next();
}

export const config = {
  matcher: ['/dashboard/:path*', '/admin/:path*', '/profile/:path*', '/emendas/:path*', '/noticias/:path*', '/inteligencia/:path*'],
};
