import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'Iconsai',
  description: 'Iconsai - Inteligencia Artificial',
  // Favicon e icones sao detectados automaticamente pelo Next.js
  // via arquivos icon.png e apple-icon.png na pasta app/
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="pt-BR">
      <body className={inter.className}>{children}</body>
    </html>
  )
}
