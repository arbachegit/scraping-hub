import { NextRequest, NextResponse } from 'next/server'

const API_URL = process.env.BACKEND_URL || 'http://localhost:8000'

export async function GET(request: NextRequest) {
  try {
    const authHeader = request.headers.get('authorization')

    if (!authHeader) {
      return NextResponse.json(
        { message: 'Token nao fornecido' },
        { status: 401 }
      )
    }

    // Chamar API do backend Python
    const res = await fetch(`${API_URL}/api/v1/auth/me`, {
      headers: { Authorization: authHeader },
    })

    const data = await res.json()

    if (!res.ok) {
      return NextResponse.json(
        { message: data.detail || 'Nao autorizado' },
        { status: res.status }
      )
    }

    return NextResponse.json(data)
  } catch (error) {
    console.error('Auth check error:', error)
    return NextResponse.json(
      { message: 'Erro interno do servidor' },
      { status: 500 }
    )
  }
}
