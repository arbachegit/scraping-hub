export function register() {
  const ALLOWED_PORT = 3002;
  const port = Number(process.env.PORT || 3002);

  if (port !== ALLOWED_PORT) {
    console.error(
      `PORTA BLOQUEADA: Next.js tentou iniciar na porta ${port}. Porta permitida: ${ALLOWED_PORT}`
    );
    process.exit(1);
  }
}
