import Image from 'next/image'

export default function Home() {
  return (
    <main className="min-h-screen bg-bg-dark flex flex-col items-center justify-center">
      {/* Logo Iconsai - Seguindo as especificacoes do logo-guide */}
      <div className="flex justify-center">
        <Image
          src="/images/iconsai-logo.png"
          alt="Iconsai"
          width={280}
          height={80}
          priority
          className="h-16 w-auto"
        />
      </div>

      <h1 className="mt-8 text-2xl font-bold text-logo-gray">
        Bem-vindo ao <span className="text-logo-red">Iconsai</span>
      </h1>

      <p className="mt-4 text-logo-gray/70">
        Plataforma de Inteligencia Artificial
      </p>
    </main>
  )
}
