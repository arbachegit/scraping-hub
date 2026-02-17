# Skill: DTO Validation (NestJS class-validator)

Revisor NestJS/TS para avaliar DTOs e pipeline de validacao usando class-validator + class-transformer.

## Camada

**Camada 2** - Servicos de Dominio (Node/NestJS)

## Quando Usar

- DTOs em projetos NestJS
- Classes de transferencia de dados
- Validacao de entrada em controllers

## Regras Inviolaveis

1. **Decorators Obrigatorios**: DTOs usam decorators de validacao:
   - `@IsString()`, `@IsInt()`, `@IsEmail()`
   - `@Length()`, `@Min()`, `@Max()`
   - `@Matches()` para patterns
   - `@IsOptional()` para campos opcionais

2. **Transformacao Antes de Validacao**: Transformacoes (`class-transformer`) sao aplicadas ANTES da validacao:
   - `@Transform()` para normalizacao
   - `@Type()` para conversao de tipos

3. **Whitelist Habilitado**: `whitelist` + `forbidNonWhitelisted` habilitados no ValidationPipe para endpoints criticos.

4. **Erros Seguros**: Erros 400 com mensagens seguras, sem expor internals.

5. **Separacao de Responsabilidade**: DTOs nao devem conter logica de negocio.

## Exemplo de Implementacao Correta

```typescript
// dto/search-company.dto.ts
import { IsString, IsOptional, Length, Matches, IsEnum } from 'class-validator';
import { Transform, Type } from 'class-transformer';

export class SearchCompanyDto {
  @IsString()
  @Length(2, 200)
  @Transform(({ value }) => value?.trim())
  nome: string;

  @IsOptional()
  @IsString()
  @Length(2, 100)
  @Transform(({ value }) => value?.trim().toLowerCase())
  cidade?: string;

  @IsOptional()
  @IsString()
  @Matches(/^\d{14}$/, { message: 'CNPJ deve ter 14 digitos' })
  @Transform(({ value }) => value?.replace(/[^\d]/g, ''))
  cnpj?: string;

  @IsOptional()
  @IsEnum(['SIMPLES_NACIONAL', 'LUCRO_PRESUMIDO', 'LUCRO_REAL'])
  regime?: string;
}

// main.ts - Configuracao global
app.useGlobalPipes(new ValidationPipe({
  whitelist: true,
  forbidNonWhitelisted: true,
  transform: true,
  transformOptions: {
    enableImplicitConversion: true
  },
  exceptionFactory: (errors) => {
    const messages = errors.map(err => ({
      field: err.property,
      constraints: Object.values(err.constraints || {})
    }));
    return new BadRequestException({
      success: false,
      error: 'Validacao falhou',
      details: messages
    });
  }
}));

// controller.ts
@Controller('companies')
export class CompaniesController {
  @Post('search')
  async search(@Body() dto: SearchCompanyDto) {
    // dto ja validado e transformado
    return this.service.search(dto);
  }
}
```

## Checklist de Auditoria

- [ ] Todos os campos tem decorators de validacao
- [ ] `@Transform()` usado para normalizacao
- [ ] `@Type()` usado para conversao de tipos complexos
- [ ] `@IsOptional()` em campos nao obrigatorios
- [ ] `whitelist: true` no ValidationPipe
- [ ] `forbidNonWhitelisted: true` em endpoints criticos
- [ ] Erros 400 com mensagens seguras
- [ ] DTOs sem logica de negocio

## Saida da Auditoria

```
RESULTADO: PASS | FAIL

VIOLACOES:
- [Regra X]: Descricao do problema

CORRECOES:
- Arquivo:linha - O que mudar
```
