# Proteção recomendada para `main` e `dev`

O repositório tem duas branches permanentes: `dev` (integração) e `main`
(produção). Aplicar uma ruleset para cada uma.

## Regras comuns a `main` e `dev`

- Pull Request obrigatório, com pelo menos uma aprovação;
- conversas resolvidas antes do merge;
- aprovação anterior descartada quando novos commits alterarem o PR;
- checks obrigatórios `checks / Python lint`, `checks / Python tests and imports`
  e `checks / Python build`;
- branch atualizada com a base antes do merge (`strict status checks`);
- bloqueio de force push e de deleção da branch;
- nenhuma exceção permanente para push direto;
- revisão obrigatória pelos owners reais definidos em `.github/CODEOWNERS`.

## Regra adicional para `main`

- check obrigatório `Source branch policy`: o PR para `main` deve vir de `dev`.

Os nomes dos checks levam o prefixo `checks /` porque os jobs vêm do workflow
reutilizável `.github/workflows/_checks.yml`.

As rulesets dependem de permissão administrativa no GitHub e devem ser
conferidas em **Settings → Rules → Rulesets** após sua aplicação.
