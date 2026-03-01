export function register() {
  const ALLOWED_PORTS = [3002, 3000]; // dev=3002, prod=3000
  const port = Number(process.env.PORT || 3002);

  if (!ALLOWED_PORTS.includes(port)) {
    console.error(
      `PORTA BLOQUEADA: Next.js tentou iniciar na porta ${port}. Portas permitidas: ${ALLOWED_PORTS.join(", ")}`
    );
    process.exit(1);
  }
}
